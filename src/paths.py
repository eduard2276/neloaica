"""Centralized path resolution for dev and frozen (PyInstaller) modes.

Three roles are kept distinct so a frozen install can put the executable
under ``C:\\Program Files\\Neloaica`` (read-only) while still writing the
database, backups and logs to a per-user location:

    * :func:`get_app_dir`        — folder containing the executable / project
                                   root in dev. Used for read-only resources
                                   that ship next to the binary.
    * :func:`get_bundle_dir`     — bundled assets (PyInstaller ``_MEIPASS``
                                   in frozen mode, project root in dev).
    * :func:`get_user_data_dir`  — writable, per-user folder for runtime data
                                   (DB, backups, logs). Falls back to the
                                   project root in dev mode so the workspace
                                   layout does not change for contributors.

The ``APP_NAME`` constant is the directory name used inside the OS-specific
data directory (``%LOCALAPPDATA%\\Neloaica`` on Windows, etc.).
"""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "Neloaica"


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """Directory where the executable lives (or project root in dev).

    In frozen mode this is read-only when installed under Program Files,
    so do not write into it. Use :func:`get_user_data_dir` for runtime
    data instead.
    """
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_bundle_dir() -> Path:
    """Directory where bundled read-only assets are extracted.

    In frozen mode this is the PyInstaller temp folder (``sys._MEIPASS``).
    In dev mode it is the project root — same as :func:`get_app_dir`.
    """
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_user_data_dir() -> Path:
    """Per-user, writable directory for runtime data (DB, backups, logs).

    Resolution rules:

    * Dev mode (not frozen): the project root. Keeps the workspace layout
      stable for contributors — no surprise ``%LOCALAPPDATA%`` writes during
      ``python -m src.main``.
    * Frozen Windows: ``%LOCALAPPDATA%\\Neloaica`` (falls back to
      ``~\\AppData\\Local\\Neloaica`` if the env var is missing).
    * Frozen macOS: ``~/Library/Application Support/Neloaica``.
    * Frozen Linux / other Unix: ``$XDG_DATA_HOME/Neloaica`` (falls back to
      ``~/.local/share/Neloaica`` per XDG basedir spec).

    The directory is **not** created here — call :meth:`pathlib.Path.mkdir`
    on it from the consumer when the directory is actually needed.
    """
    if not _is_frozen():
        return Path(__file__).parent.parent

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_NAME


def get_logs_dir() -> Path:
    """Directory for log files. Lives under :func:`get_user_data_dir`."""
    return get_user_data_dir() / "logs"


def get_logo_png_path() -> Path:
    """Path to the application logo bitmap.

    The PNG ships under ``templates/images/`` and is mirrored into the
    PyInstaller bundle by :data:`Neloaica.spec`. The same path resolves
    against the project root in dev mode and against ``_MEIPASS`` in
    frozen mode, so callers can use it for both.

    Used for the in-app sidebar header where Qt's smooth pixmap
    scaling gives a better result than the multi-resolution ICO.
    """
    return get_bundle_dir() / "templates" / "images" / "Neloaica_logo.png"


def get_logo_ico_path() -> Path:
    """Path to the multi-resolution application icon.

    Preferred for :meth:`QApplication.setWindowIcon` (and the
    PyInstaller ``EXE(icon=...)`` build hint) because Windows pulls
    the correct size for the taskbar, alt-tab, title bar and tray
    out of a single ``.ico``.
    """
    return get_bundle_dir() / "templates" / "images" / "Neloaica_logo.ico"


def get_database_path() -> Path:
    """Absolute path of the SQLite database file."""
    return get_user_data_dir() / "neloaica.db"


def get_backups_dir() -> Path:
    """Directory holding rolling database backups."""
    return get_user_data_dir() / "backups"


def migrate_legacy_db(legacy_path: Path, new_path: Path) -> bool:
    """Move a legacy DB sitting next to the executable into the user data dir.

    Older builds wrote ``neloaica.db`` next to the ``.exe``. After moving the
    runtime data under ``%LOCALAPPDATA%\\Neloaica`` we run this on every
    startup so existing installs migrate transparently.

    Behaviour:
        * No ``legacy_path`` on disk → return ``False`` (nothing to migrate).
        * ``new_path`` already exists → return ``False`` and leave the legacy
          file alone (the user data dir is the source of truth).
        * Otherwise → create the parent of ``new_path`` if missing, move the
          file, return ``True``.

    The function never raises; on I/O errors it returns ``False`` so the app
    can boot with whatever DB it can still reach.
    """
    try:
        if not legacy_path.exists():
            return False
        if new_path.exists():
            return False
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_path), str(new_path))
        return True
    except OSError:
        return False


def migrate_legacy_dir(legacy_dir: Path, new_dir: Path) -> int:
    """Move files from a legacy directory next to the exe into the user data dir.

    Used for the ``backups/`` folder that older builds wrote next to the
    executable. Behaviour mirrors :func:`migrate_legacy_db` but at the
    directory level:

        * No ``legacy_dir`` on disk → return 0 (nothing to do).
        * ``legacy_dir == new_dir`` → return 0 (dev-mode no-op).
        * For each regular file inside ``legacy_dir``:
            - if the same name does not exist in ``new_dir`` → move it.
            - if it already exists in ``new_dir`` → leave the legacy file
              in place. Backup filenames carry a timestamp so the only
              way to hit a conflict is for the user to have re-run the
              migration with the same files, in which case the user data
              dir is already authoritative.
        * If ``legacy_dir`` ends up empty (or only contains empty
          subdirectories) → remove it.
        * Subdirectories under ``legacy_dir`` are walked recursively;
          ``new_dir`` mirrors the relative structure.

    Returns:
        The number of files actually moved. ``0`` is a valid success value
        when there was nothing to migrate.

    Like :func:`migrate_legacy_db`, this function swallows ``OSError`` and
    returns whatever progress it made — the application must still be
    able to boot if the migration partially fails.
    """
    if not legacy_dir.exists() or not legacy_dir.is_dir():
        return 0
    if legacy_dir == new_dir:
        return 0

    moved = 0
    try:
        new_dir.mkdir(parents=True, exist_ok=True)
        for entry in sorted(legacy_dir.rglob("*")):
            if not entry.is_file():
                continue
            rel = entry.relative_to(legacy_dir)
            target = new_dir / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(entry), str(target))
                moved += 1
            except OSError:
                # One file failed; keep going so the rest still get out.
                continue

        # Best-effort cleanup of now-empty directories. ``rmdir`` only
        # succeeds on empty dirs so any leftover files (skipped on conflict
        # or failed to move) keep the legacy folder around for the user.
        for entry in sorted(legacy_dir.rglob("*"), reverse=True):
            if entry.is_dir():
                try:
                    entry.rmdir()
                except OSError:
                    pass
        try:
            legacy_dir.rmdir()
        except OSError:
            pass
    except OSError:
        pass

    return moved
