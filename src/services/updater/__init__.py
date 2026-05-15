"""Auto-update service.

PR #4 of the auto-update roadmap. This package will grow over the
next PRs to cover the full check / download / apply flow, but for
now it exposes only what is needed to query "is a newer release
available?" so the Settings page (or a future tray icon) can hook
in immediately.

Typical use::

    from src import __version__
    from src.services.updater import UpdateChecker, UpdateChannel, Version

    checker = UpdateChecker(Version.coerce(__version__))
    try:
        info = checker.check()
    except UpdateCheckError as exc:
        logger.warning("Update check failed: %s", exc)
        info = None

    if info is not None:
        # surface in UI: f"Versiunea {info.version} este disponibilă."
        ...
"""

from .check import (
    DEFAULT_MANIFEST_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    ManifestFetcher,
    UpdateChecker,
)
from .schema import (
    UpdateApplyError,
    UpdateChannel,
    UpdateCheckError,
    UpdateDownloadError,
    UpdateError,
    UpdateInfo,
)
from .version import Version

__all__ = [
    "DEFAULT_MANIFEST_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "ManifestFetcher",
    "UpdateApplyError",
    "UpdateChannel",
    "UpdateCheckError",
    "UpdateChecker",
    "UpdateDownloadError",
    "UpdateError",
    "UpdateInfo",
    "Version",
]
