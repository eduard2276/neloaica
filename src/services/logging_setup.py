"""Application-wide logging configuration.

A single :func:`setup_logging` call wires the root logger to a rotating file
handler under :func:`src.paths.get_logs_dir`. Once configured, every module
that imports :mod:`logging` (``logging.getLogger(__name__)``) writes into the
same rolled log file.

Why a rotating file handler?
    The application runs as a desktop binary on a user's machine, so we cannot
    rely on the OS journal or a remote log sink. ``RotatingFileHandler`` keeps
    disk usage bounded (5 files × ~2 MB by default) without external services.

Why ``setup_logging`` and not ``logging.basicConfig`` at module import?
    ``basicConfig`` is a no-op once any handler is attached (e.g. by pytest or
    Qt). An explicit setup function lets the entry point opt in, lets tests
    point the logs at a tmp path, and is idempotent so it can be called again
    safely (e.g. from a unit test).
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.paths import get_logs_dir

DEFAULT_LOG_FILENAME = "neloaica.log"
DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB per file
DEFAULT_BACKUP_COUNT = 5  # keep 5 rolled files (~10 MB total)
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Tag attached to handlers we install, so :func:`setup_logging` is idempotent
# and so tests can identify and remove them without touching foreign handlers.
_HANDLER_TAG = "neloaica.logging_setup"


def _is_managed(handler: logging.Handler) -> bool:
    return getattr(handler, "_neloaica_tag", None) == _HANDLER_TAG


def setup_logging(
    logs_dir: Optional[Path] = None,
    *,
    level: int = logging.INFO,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    filename: str = DEFAULT_LOG_FILENAME,
) -> Path:
    """Configure the root logger with a rotating file handler.

    Args:
        logs_dir: Directory to write the log file into. Defaults to
            :func:`src.paths.get_logs_dir`. The directory is created if
            missing.
        level: Root logger level (default ``logging.INFO``).
        max_bytes: Per-file size cap before rotation. Default 2 MB.
        backup_count: Number of rolled files to keep alongside the active one.
            Default 5.
        filename: Active log file name. Default ``neloaica.log``.

    Returns:
        Absolute path of the log file. Useful for tests and for surfacing the
        location in the Settings page.

    The function is **idempotent**: calling it twice in the same process
    replaces any previously installed handler tagged by this module rather
    than stacking up duplicates. Foreign handlers (e.g. pytest's caplog) are
    left untouched.
    """
    target_dir = Path(logs_dir) if logs_dir is not None else get_logs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_dir / filename

    root = logging.getLogger()
    for existing in list(root.handlers):
        if _is_managed(existing):
            root.removeHandler(existing)
            try:
                existing.close()
            except OSError:
                pass

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
    handler._neloaica_tag = _HANDLER_TAG  # type: ignore[attr-defined]

    root.addHandler(handler)
    if root.level == logging.WARNING or root.level == logging.NOTSET:
        # Don't lower a more permissive level chosen by the user / tests, but
        # do raise the default WARNING/NOTSET so INFO messages are emitted.
        root.setLevel(level)

    return log_file


def reset_logging() -> None:
    """Remove handlers installed by :func:`setup_logging`.

    Used by tests to leave the root logger clean between cases.
    """
    root = logging.getLogger()
    for existing in list(root.handlers):
        if _is_managed(existing):
            root.removeHandler(existing)
            try:
                existing.close()
            except OSError:
                pass
