"""High-level facade around check / download / apply.

PR #8 of the auto-update roadmap. The three stages from PR #4-6 work
fine independently, but every UI integration (the Settings page
button, a future tray icon, a CLI tool) needs the same boilerplate:

* build the checker with the current ``__version__``,
* keep the resulting ``UpdateInfo`` around so the download stage can
  reuse it,
* keep the resulting ``DownloadResult`` around so the apply stage
  can reuse it,
* funnel everything through the same logger.

:class:`UpdateOrchestrator` encapsulates exactly that — a small,
stateful object that exposes ``check`` / ``download`` / ``apply`` and
caches the intermediate results. Each method can also be called in
isolation by passing the relevant ``UpdateInfo`` / ``DownloadResult``
explicitly, which is how the worker threads in :mod:`src.ui.update`
re-enter the orchestrator from background threads.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .apply import ApplyPlan, UpdateApplier
from .check import UpdateChecker, default_manifest_url
from .download import (
    CancelPredicate,
    DownloadResult,
    ProgressCallback,
    UpdateDownloader,
)
from .schema import UpdateChannel, UpdateInfo
from .version import Version

logger = logging.getLogger(__name__)


class UpdateOrchestrator:
    """Stateful glue around the three updater stages.

    Calling :meth:`check`, :meth:`download` and :meth:`apply` in order
    is the typical flow:

    >>> orch = UpdateOrchestrator(Version.coerce("1.0.0"))
    >>> info = orch.check()
    >>> if info is not None:
    ...     result = orch.download()
    ...     plan = orch.apply()

    Each method can be called in isolation by passing the relevant
    intermediate result, which is essential for background threads
    that hand work off without sharing mutable state across threads.
    """

    def __init__(
        self,
        current_version: Version,
        *,
        channel: UpdateChannel = UpdateChannel.STABLE,
        manifest_url: Optional[str] = None,
        download_dir: Optional[Path] = None,
        install_dir: Optional[Path] = None,
        staging_root: Optional[Path] = None,
        checker: Optional[UpdateChecker] = None,
        downloader: Optional[UpdateDownloader] = None,
        applier: Optional[UpdateApplier] = None,
    ) -> None:
        if not isinstance(current_version, Version):
            raise TypeError(
                "current_version must be a Version instance; "
                "use Version.coerce(...) for strings."
            )
        self._current = current_version
        self._channel = channel
        self._manifest_url = manifest_url or default_manifest_url()

        self._checker = checker or UpdateChecker(
            current_version,
            manifest_url=self._manifest_url,
            channel=channel,
        )
        self._downloader = downloader or UpdateDownloader(target_dir=download_dir)
        self._applier = applier or UpdateApplier(install_dir=install_dir, staging_root=staging_root)

        self._last_info: Optional[UpdateInfo] = None
        self._last_download: Optional[DownloadResult] = None
        self._last_plan: Optional[ApplyPlan] = None

    # ---------------------------------------------------------------
    # Read-only state
    # ---------------------------------------------------------------

    @property
    def current_version(self) -> Version:
        return self._current

    @property
    def channel(self) -> UpdateChannel:
        return self._channel

    @property
    def manifest_url(self) -> str:
        return self._manifest_url

    @property
    def last_info(self) -> Optional[UpdateInfo]:
        return self._last_info

    @property
    def last_download(self) -> Optional[DownloadResult]:
        return self._last_download

    @property
    def last_plan(self) -> Optional[ApplyPlan]:
        return self._last_plan

    @property
    def checker(self) -> UpdateChecker:
        return self._checker

    @property
    def downloader(self) -> UpdateDownloader:
        return self._downloader

    @property
    def applier(self) -> UpdateApplier:
        return self._applier

    # ---------------------------------------------------------------
    # Stage methods
    # ---------------------------------------------------------------

    def check(self) -> Optional[UpdateInfo]:
        """Query the manifest. Caches the result in :attr:`last_info`."""
        logger.info(
            "Checking for updates: current=%s channel=%s manifest=%s",
            self._current,
            self._channel.value,
            self._manifest_url,
        )
        info = self._checker.check()
        self._last_info = info
        if info is None:
            logger.info("No update available.")
        else:
            logger.info("Update available: %s -> %s", self._current, info.version)
        return info

    def download(
        self,
        info: Optional[UpdateInfo] = None,
        *,
        on_progress: Optional[ProgressCallback] = None,
        cancel: Optional[CancelPredicate] = None,
    ) -> DownloadResult:
        """Download the archive for ``info`` (or :attr:`last_info`).

        Caches the resulting :class:`DownloadResult` in
        :attr:`last_download` so a subsequent :meth:`apply` call can
        omit its argument.
        """
        target = info or self._last_info
        if target is None:
            raise RuntimeError("No UpdateInfo to download. Call check() first or pass info=...")
        result = self._downloader.download(target, on_progress=on_progress, cancel=cancel)
        self._last_download = result
        return result

    def apply(self, download: Optional[DownloadResult] = None) -> ApplyPlan:
        """Apply the archive (default: :attr:`last_download`).

        After this returns the caller MUST shut the Qt app down so the
        helper script can take over.
        """
        result = download or self._last_download
        if result is None:
            raise RuntimeError(
                "No DownloadResult to apply. Call download() first or pass it explicitly."
            )
        plan = self._applier.apply(result.path, result.info)
        self._last_plan = plan
        return plan

    # ---------------------------------------------------------------
    # Convenience predicates for the UI
    # ---------------------------------------------------------------

    def is_update_available(self) -> bool:
        """``True`` if :meth:`check` returned a newer version."""
        return self._last_info is not None and self._last_info.is_newer_than(self._current)

    def is_download_ready(self) -> bool:
        """``True`` once :meth:`download` finished successfully."""
        return self._last_download is not None


__all__ = ["UpdateOrchestrator"]
