"""Apply a downloaded update on top of the running install.

Third and final stage of the auto-update flow at runtime. The
challenge on Windows is that a running ``.exe`` cannot overwrite
itself, and we ship as a PyInstaller ``onedir`` bundle — many files
in the install directory may be locked while the process is alive.

The strategy here mirrors what most desktop updaters do:

1. Extract the freshly downloaded archive into a *staging* folder
   under :func:`~src.paths.get_user_data_dir` (always writable, even
   if the install lives in ``Program Files``).
2. Confirm the staged tree looks like a Neloaica build (the
   executable is present at the expected relative path).
3. Write a self-contained PowerShell *helper* script to the same
   user data directory. The helper waits for the current PID to
   exit, then performs the swap (current install -> ``.old.<ts>``
   backup, staged folder -> install location) and relaunches the
   freshly installed executable.
4. Launch the helper in a detached PowerShell process and return.
   The caller is expected to immediately shut the Qt app down
   ("application is exiting to finish the update..." in the UI).

Every step is structured so it can be unit tested without actually
running the swap: directory layout, archive shape, helper script
contents and the final ``subprocess.Popen`` arguments are all
exposed through small, individually testable methods. The actual
``Popen`` call is the only side effect and lives in a tiny method
(``_spawn_helper``) that tests monkeypatch.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from src.paths import get_user_data_dir

from .schema import UpdateApplyError, UpdateInfo

logger = logging.getLogger(__name__)

DEFAULT_EXECUTABLE_NAME = "Neloaica.exe"
HELPER_SCRIPT_NAME = "apply_update.ps1"


@dataclass(frozen=True)
class ApplyPlan:
    """Everything needed to perform the swap, computed up front.

    Building the plan eagerly lets us validate inputs and surface
    errors to the user *before* writing any helper script — once the
    plan is good, applying it is a single :func:`subprocess.Popen`
    call.
    """

    archive_path: Path
    staging_dir: Path
    install_dir: Path
    executable_path: Path
    backup_dir: Path
    helper_script_path: Path
    info: UpdateInfo
    current_pid: int


class UpdateApplier:
    """Stage, validate and launch an update.

    The applier is stateless between calls: each :meth:`apply` builds
    its own :class:`ApplyPlan`, leaves the helper script + staging
    folder on disk and hands control to PowerShell.
    """

    def __init__(
        self,
        *,
        install_dir: Optional[Path] = None,
        staging_root: Optional[Path] = None,
        executable_name: str = DEFAULT_EXECUTABLE_NAME,
    ) -> None:
        if not executable_name:
            raise ValueError("executable_name must not be empty.")
        self._install_dir = install_dir
        self._staging_root = staging_root
        self._executable_name = executable_name

    # ---------------------------------------------------------------
    # Inspection helpers (exposed for tests / UI)
    # ---------------------------------------------------------------

    @property
    def executable_name(self) -> str:
        return self._executable_name

    def resolve_install_dir(self) -> Path:
        """Where the currently running build lives.

        In a frozen PyInstaller build this is the folder containing
        ``sys.executable``; in development it falls back to the
        project root. Tests inject a value via the constructor so
        they never depend on the real layout.
        """
        if self._install_dir is not None:
            return self._install_dir
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[3]

    def resolve_staging_root(self) -> Path:
        """Where staged update folders are written.

        Lazy by design: tests can swap ``get_user_data_dir`` at the
        module level and the change is honoured on the next call.
        """
        if self._staging_root is not None:
            return self._staging_root
        return get_user_data_dir() / "updates" / "staging"

    def staging_dir_for(self, info: UpdateInfo) -> Path:
        return self.resolve_staging_root() / f"Neloaica-v{info.version}"

    # ---------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------

    def apply(self, archive_path: Path, info: UpdateInfo) -> ApplyPlan:
        """Stage the archive and launch the helper.

        Returns the resolved :class:`ApplyPlan` so the caller can log
        / show it in the UI. The caller MUST shut down the Qt
        application immediately after this returns; otherwise the
        helper will time out waiting for the process to exit.
        """
        plan = self._build_plan(archive_path, info)
        self._stage_archive(plan)
        self._validate_staged_tree(plan)
        self._write_helper_script(plan)
        self._spawn_helper(plan)
        logger.info(
            "Update apply launched: install=%s staging=%s backup=%s helper=%s",
            plan.install_dir,
            plan.staging_dir,
            plan.backup_dir,
            plan.helper_script_path,
        )
        return plan

    # ---------------------------------------------------------------
    # Plan / staging
    # ---------------------------------------------------------------

    def _build_plan(self, archive_path: Path, info: UpdateInfo) -> ApplyPlan:
        archive_path = Path(archive_path)
        if not archive_path.exists() or not archive_path.is_file():
            raise UpdateApplyError(f"Update archive not found: {archive_path}")

        install_dir = self.resolve_install_dir()
        staging_dir = self.staging_dir_for(info)
        executable_path = install_dir / self._executable_name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = install_dir.with_name(f"{install_dir.name}.old.{timestamp}")
        helper_script_path = self.resolve_staging_root() / f"{HELPER_SCRIPT_NAME}"
        return ApplyPlan(
            archive_path=archive_path,
            staging_dir=staging_dir,
            install_dir=install_dir,
            executable_path=executable_path,
            backup_dir=backup_dir,
            helper_script_path=helper_script_path,
            info=info,
            current_pid=os.getpid(),
        )

    def _stage_archive(self, plan: ApplyPlan) -> None:
        """Extract ``archive_path`` into ``staging_dir`` (clean)."""
        try:
            if plan.staging_dir.exists():
                _force_rmtree(plan.staging_dir)
            plan.staging_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise UpdateApplyError(
                f"Cannot prepare staging directory {plan.staging_dir}: {exc}"
            ) from exc

        try:
            with zipfile.ZipFile(plan.archive_path) as zf:
                _safe_extract_zip(zf, plan.staging_dir)
        except zipfile.BadZipFile as exc:
            raise UpdateApplyError(
                f"Update archive is corrupt: {plan.archive_path} ({exc})."
            ) from exc
        except OSError as exc:
            raise UpdateApplyError(
                f"Cannot extract {plan.archive_path} into " f"{plan.staging_dir}: {exc}"
            ) from exc

    def _validate_staged_tree(self, plan: ApplyPlan) -> None:
        """Confirm the staged tree contains the executable.

        We don't try to be too clever — many archives wrap their
        contents in an extra ``Neloaica/`` folder; we accept either
        layout by promoting the inner folder if needed.
        """
        executable = plan.staging_dir / self._executable_name
        if executable.exists():
            return

        # Single-child wrapper folder (the common PyInstaller layout
        # when zipping the ``dist/Neloaica`` directory).
        entries = [p for p in plan.staging_dir.iterdir()]
        if len(entries) == 1 and entries[0].is_dir():
            inner = entries[0]
            inner_exe = inner / self._executable_name
            if inner_exe.exists():
                # Flatten: move inner/* up one level, then remove inner.
                for child in list(inner.iterdir()):
                    target = plan.staging_dir / child.name
                    shutil.move(str(child), str(target))
                inner.rmdir()
                return

        raise UpdateApplyError(
            f"Staged archive does not contain {self._executable_name} "
            f"at the expected location {executable}."
        )

    # ---------------------------------------------------------------
    # Helper script (PowerShell)
    # ---------------------------------------------------------------

    def _write_helper_script(self, plan: ApplyPlan) -> None:
        try:
            plan.helper_script_path.parent.mkdir(parents=True, exist_ok=True)
            plan.helper_script_path.write_text(self.build_helper_script(plan), encoding="utf-8")
        except OSError as exc:
            raise UpdateApplyError(
                f"Cannot write helper script {plan.helper_script_path}: {exc}"
            ) from exc

    @staticmethod
    def build_helper_script(plan: ApplyPlan) -> str:
        """Render the PowerShell helper for the given plan.

        Public + ``@staticmethod`` so tests can render the script
        without running the apply pipeline. The helper:

        * waits up to 60 s for the current PID to exit,
        * renames the current install to ``.old.<timestamp>``,
        * moves the staged folder into the install location,
        * relaunches the executable,
        * leaves a structured log next to itself.
        """
        log_path = plan.helper_script_path.with_suffix(".log")
        return _POWERSHELL_HELPER_TEMPLATE.format(
            pid=plan.current_pid,
            install_dir=_ps_quote(plan.install_dir),
            staging_dir=_ps_quote(plan.staging_dir),
            backup_dir=_ps_quote(plan.backup_dir),
            executable=_ps_quote(plan.executable_path),
            log_path=_ps_quote(log_path),
            version=plan.info.version,
        )

    # ---------------------------------------------------------------
    # Spawn (only side effect)
    # ---------------------------------------------------------------

    def _spawn_helper(self, plan: ApplyPlan) -> None:
        argv = self.build_spawn_argv(plan)
        try:
            self._popen(argv)
        except OSError as exc:
            raise UpdateApplyError(
                f"Cannot launch helper {plan.helper_script_path}: {exc}"
            ) from exc

    @staticmethod
    def build_spawn_argv(plan: ApplyPlan) -> Sequence[str]:
        """Argv for the detached PowerShell process.

        Public so tests assert on the exact command line. The flags
        are chosen so the helper survives the parent exiting:

        * ``-NoProfile`` - skip user profile (faster, predictable),
        * ``-WindowStyle Hidden`` - no flashing console for the user,
        * ``-ExecutionPolicy Bypass`` - the script is local and
          generated by us; signing is unnecessary.
        """
        return (
            "powershell.exe",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(plan.helper_script_path),
        )

    def _popen(self, argv: Sequence[str]) -> None:
        """Tiny seam tests monkeypatch instead of running PowerShell."""
        # ``DETACHED_PROCESS`` + ``CREATE_NEW_PROCESS_GROUP`` are the
        # canonical Windows flags for "fire and forget" children.
        # ``CREATE_BREAKAWAY_FROM_JOB`` (0x01000000) is critical for
        # PyInstaller-built apps: PyInstaller's ``runw.exe`` bootloader
        # runs inside a Windows Job Object that, by default, closes all
        # children when the parent exits. Without breakaway, our helper
        # PowerShell process is killed the instant we call ``app.quit()``
        # — even if it was launched detached. We fall back to plain
        # ``Popen`` on non-Windows platforms (CI / dev) where these
        # flags are unavailable.
        creation_flags = 0
        if sys.platform == "win32":
            DETACHED_PROCESS = subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            CREATE_NEW_PROCESS_GROUP = (
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            )
            CREATE_BREAKAWAY_FROM_JOB = 0x01000000
            creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
        subprocess.Popen(
            list(argv),
            close_fds=True,
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------


def _ps_quote(path) -> str:
    """Quote a path / value for PowerShell single-quoted string.

    PowerShell escapes a literal single quote inside a single-quoted
    string by doubling it. Everything else passes through unchanged.
    """
    text = str(path)
    return "'" + text.replace("'", "''") + "'"


def _safe_extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    """Zip extraction with path traversal protection.

    A malicious archive could include entries like ``..\\evil`` which
    would land outside ``dest`` under ``ZipFile.extractall``. We
    refuse anything whose resolved destination escapes ``dest``.
    """
    dest_resolved = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        try:
            target.relative_to(dest_resolved)
        except ValueError as exc:
            raise UpdateApplyError(
                f"Archive contains entry escaping staging dir: " f"{member.filename!r}"
            ) from exc
    zf.extractall(dest)


def _force_rmtree(path: Path) -> None:
    """Like :func:`shutil.rmtree` but recovers from read-only files."""

    def _onerror(func, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            raise

    shutil.rmtree(path, onerror=_onerror)


# ---------------------------------------------------------------
# PowerShell helper template
# ---------------------------------------------------------------
#
# Notes:
# * The script is generated, not committed, so we keep it inline.
# * We use ``Wait-Process -Id`` with ``-Timeout`` then ``Stop-Process``
#   as a safety net; the parent app should already be exiting.
# * All paths are interpolated as PowerShell single-quoted strings via
#   :func:`_ps_quote` so spaces in ``Program Files\\Neloaica`` are safe.
# * We tee output to a log file next to the helper script so failures
#   are diagnosable after the fact even when the helper is detached.

_POWERSHELL_HELPER_TEMPLATE = r"""# Neloaica auto-update helper (generated)
# Target version: {version}

$ErrorActionPreference = 'Stop'

$LogPath     = {log_path}
$InstallDir  = {install_dir}
$StagingDir  = {staging_dir}
$BackupDir   = {backup_dir}
$Executable  = {executable}
$ParentPid   = {pid}

function Write-Log($msg) {{
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line  = "[{{0}}] {{1}}" -f $stamp, $msg
    Add-Content -Path $LogPath -Value $line -ErrorAction SilentlyContinue
}}

try {{
    Write-Log "Starting update helper for version {version}."
    Write-Log "Parent PID: $ParentPid"
    Write-Log "Install dir: $InstallDir"

    try {{
        Wait-Process -Id $ParentPid -Timeout 60 -ErrorAction SilentlyContinue
    }} catch {{
        Write-Log "Wait-Process produced: $($_.Exception.Message)"
    }}
    Start-Sleep -Seconds 1

    if (Test-Path -LiteralPath $InstallDir) {{
        Write-Log "Renaming $InstallDir -> $BackupDir"
        Move-Item -LiteralPath $InstallDir -Destination $BackupDir
    }} else {{
        Write-Log "Install directory missing, nothing to back up."
    }}

    Write-Log "Promoting staged build $StagingDir -> $InstallDir"
    Move-Item -LiteralPath $StagingDir -Destination $InstallDir

    Write-Log "Launching new build: $Executable"
    Start-Process -FilePath $Executable
    Write-Log "Update complete."
}} catch {{
    Write-Log "Update FAILED: $($_.Exception.Message)"
    Write-Log $_.ScriptStackTrace
    exit 1
}}
"""


__all__ = [
    "ApplyPlan",
    "DEFAULT_EXECUTABLE_NAME",
    "HELPER_SCRIPT_NAME",
    "UpdateApplier",
]
