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
4. Launch the helper *outside our own process tree* so it survives
   ``QApplication.quit()``. On Windows this is done by registering
   a one-shot Scheduled Task and immediately invoking ``schtasks
   /Run``. Task Scheduler executes the task in its own service
   context, isolated from any Windows Job Object the PyInstaller
   bootloader may have placed us in (``DETACHED_PROCESS`` and
   ``CREATE_BREAKAWAY_FROM_JOB`` alone are not sufficient — the
   parent job can ignore breakaway and silently kill the child).
   If the Scheduled Task strategy fails (e.g. ``schtasks`` is
   unavailable), we fall back to ``subprocess.Popen`` with the
   detach flags. The helper deletes its own task on completion.

Every step is structured so it can be unit tested without actually
running the swap: directory layout, archive shape, helper script
contents, scheduled-task command line and the final ``Popen``
arguments are all exposed through small, individually testable
methods. The only true side effects live in ``_run_schtasks`` and
``_popen``, both of which tests monkeypatch.
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
SCHEDULED_TASK_PREFIX = "Neloaica-Apply-Update"


@dataclass(frozen=True)
class ApplyPlan:
    """Everything needed to perform the swap, computed up front.

    Building the plan eagerly lets us validate inputs and surface
    errors to the user *before* writing any helper script — once the
    plan is good, applying it is a single ``schtasks`` invocation
    (or, on POSIX / when ``schtasks`` is unavailable, a single
    :func:`subprocess.Popen` call).
    """

    archive_path: Path
    staging_dir: Path
    install_dir: Path
    executable_path: Path
    backup_dir: Path
    helper_script_path: Path
    info: UpdateInfo
    current_pid: int
    task_name: str


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
        use_schtasks: Optional[bool] = None,
    ) -> None:
        if not executable_name:
            raise ValueError("executable_name must not be empty.")
        self._install_dir = install_dir
        self._staging_root = staging_root
        self._executable_name = executable_name
        # Scheduled Task spawn is Windows-only and is the default
        # there; tests / non-Windows fall back to plain ``Popen``.
        self._use_schtasks = use_schtasks if use_schtasks is not None else sys.platform == "win32"

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
        current_pid = os.getpid()
        task_name = f"{SCHEDULED_TASK_PREFIX}-{info.version}-{timestamp}-{current_pid}"
        return ApplyPlan(
            archive_path=archive_path,
            staging_dir=staging_dir,
            install_dir=install_dir,
            executable_path=executable_path,
            backup_dir=backup_dir,
            helper_script_path=helper_script_path,
            info=info,
            current_pid=current_pid,
            task_name=task_name,
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
        * unregisters its own Scheduled Task on success,
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
            task_name=_ps_quote(plan.task_name),
        )

    # ---------------------------------------------------------------
    # Spawn (only side effect)
    # ---------------------------------------------------------------

    def _spawn_helper(self, plan: ApplyPlan) -> None:
        """Launch the helper outside our own process tree.

        Order of preference on Windows:

        1. **Scheduled Task** (``schtasks /Create`` + ``/Run``). Runs
           in the Task Scheduler service context, completely
           independent of any Job Object we may be in.
        2. **Detached ``Popen``** (``DETACHED_PROCESS | ...``).
           Historical fallback if ``schtasks`` fails for any reason
           (uncommon, e.g. corporate machines that hard-disable it).
        """
        if self._use_schtasks:
            try:
                self._spawn_via_schtasks(plan)
                return
            except (OSError, ValueError) as exc:
                logger.warning(
                    "Scheduled Task spawn failed (%s); "
                    "falling back to detached Popen for helper %s",
                    exc,
                    plan.helper_script_path,
                )
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

    @staticmethod
    def build_schtasks_tr_value(plan: ApplyPlan) -> str:
        """Render the ``/TR`` value passed to ``schtasks /Create``.

        Public so tests can assert on the exact command-line string.
        The value is a single Windows command line — ``schtasks``
        parses it by quoting rules, so any argument with whitespace
        is wrapped in double quotes and embedded quotes are escaped
        per the standard MSVCRT convention.
        """
        argv = UpdateApplier.build_spawn_argv(plan)
        return " ".join(_win_quote_arg(a) for a in argv)

    @staticmethod
    def build_schtasks_create_argv(plan: ApplyPlan) -> Sequence[str]:
        """Argv for ``schtasks /Create`` (returned for tests/UI logs)."""
        return (
            "schtasks",
            "/Create",
            "/TN",
            plan.task_name,
            "/TR",
            UpdateApplier.build_schtasks_tr_value(plan),
            "/SC",
            "ONCE",
            "/ST",
            "00:00",
            "/F",
        )

    @staticmethod
    def build_schtasks_run_argv(plan: ApplyPlan) -> Sequence[str]:
        """Argv for ``schtasks /Run`` (returned for tests/UI logs)."""
        return ("schtasks", "/Run", "/TN", plan.task_name)

    @staticmethod
    def build_schtasks_delete_argv(plan: ApplyPlan) -> Sequence[str]:
        """Argv for ``schtasks /Delete`` (best-effort cleanup)."""
        return ("schtasks", "/Delete", "/TN", plan.task_name, "/F")

    def _spawn_via_schtasks(self, plan: ApplyPlan) -> None:
        """Register a one-shot Scheduled Task and run it immediately.

        Why this works where ``DETACHED_PROCESS`` does not:
        ``schtasks`` hands the work off to the Task Scheduler
        service, which then ``CreateProcessW``-es the helper from a
        completely independent process tree. The PyInstaller
        bootloader's Job Object cannot reach across that boundary,
        so ``app.quit()`` no longer takes the helper down with it.
        """
        create_argv = self.build_schtasks_create_argv(plan)
        create_result = self._run_schtasks(create_argv)
        if create_result.returncode != 0:
            raise OSError(
                f"schtasks /Create failed (rc={create_result.returncode}): "
                f"{(create_result.stderr or create_result.stdout).strip()}"
            )

        run_argv = self.build_schtasks_run_argv(plan)
        run_result = self._run_schtasks(run_argv)
        if run_result.returncode != 0:
            # Best-effort cleanup so we don't leave an orphan task
            # behind when /Run fails.
            self._run_schtasks(self.build_schtasks_delete_argv(plan))
            raise OSError(
                f"schtasks /Run failed (rc={run_result.returncode}): "
                f"{(run_result.stderr or run_result.stdout).strip()}"
            )

    def _run_schtasks(self, argv: Sequence[str]) -> "subprocess.CompletedProcess[str]":
        """Tiny seam tests monkeypatch instead of running schtasks."""
        return subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
        )

    def _popen(self, argv: Sequence[str]) -> None:
        """Tiny seam tests monkeypatch instead of running PowerShell.

        This is only used as a fallback when the Scheduled Task
        strategy fails. The detach flags below are kept as a
        best-effort safety net even though, on PyInstaller windowed
        builds, they are routinely overridden by the parent Job
        Object — which is exactly why ``schtasks`` is the primary
        path on Windows.
        """
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


def _win_quote_arg(arg: str) -> str:
    """Quote a single argument for a Windows command line.

    Follows the standard MSVCRT parsing rules (the same convention
    used by :func:`subprocess.list2cmdline`): wrap the argument in
    double quotes if it contains whitespace or quotes, and escape
    embedded ``"`` / trailing ``\\`` runs appropriately. Plain
    arguments are returned untouched so the rendered command line
    stays human-readable.
    """
    text = str(arg)
    if not text:
        return '""'
    needs_quoting = any(c in text for c in (" ", "\t", '"'))
    if not needs_quoting:
        return text
    out: list = []
    backslashes = 0
    for ch in text:
        if ch == "\\":
            backslashes += 1
            continue
        if ch == '"':
            out.append("\\" * (backslashes * 2 + 1))
            out.append('"')
        else:
            out.append("\\" * backslashes)
            out.append(ch)
        backslashes = 0
    out.append("\\" * (backslashes * 2))
    return '"' + "".join(out) + '"'


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
$TaskName    = {task_name}

function Write-Log($msg) {{
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line  = "[{{0}}] {{1}}" -f $stamp, $msg
    Add-Content -Path $LogPath -Value $line -ErrorAction SilentlyContinue
}}

function Remove-SelfTask {{
    if (-not $TaskName) {{ return }}
    try {{
        & schtasks.exe /Delete /TN $TaskName /F 2>$null | Out-Null
    }} catch {{
        Write-Log "Task cleanup produced: $($_.Exception.Message)"
    }}
}}

try {{
    Write-Log "Starting update helper for version {version}."
    Write-Log "Parent PID: $ParentPid"
    Write-Log "Install dir: $InstallDir"
    Write-Log "Scheduled task: $TaskName"

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
    Remove-SelfTask
}} catch {{
    Write-Log "Update FAILED: $($_.Exception.Message)"
    Write-Log $_.ScriptStackTrace
    Remove-SelfTask
    exit 1
}}
"""


__all__ = [
    "ApplyPlan",
    "DEFAULT_EXECUTABLE_NAME",
    "HELPER_SCRIPT_NAME",
    "UpdateApplier",
]
