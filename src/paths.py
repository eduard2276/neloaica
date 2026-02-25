"""Centralized path resolution for dev and frozen (PyInstaller) modes."""

import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """Directory where the .exe (or project root in dev) lives.

    Used for files that must persist across runs and live next to
    the application: database, backups, exports.
    """
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_bundle_dir() -> Path:
    """Directory where bundled read-only assets are extracted.

    In frozen mode this is the PyInstaller temp folder (sys._MEIPASS).
    In dev mode it is the project root — same as get_app_dir().
    """
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent
