"""Download the release archive advertised by the manifest.

PR #5 of the auto-update roadmap. Responsibilities:

* download the ZIP referenced by :class:`UpdateInfo.download_url`
  into a writable temp location (under
  :func:`~src.paths.get_user_data_dir`) so the running ``.exe`` is
  never touched,
* stream the response in chunks and report progress through an
  injectable callback so the UI can show a progress bar,
* support cancellation through a callable predicate without leaving
  partial files on disk,
* verify the SHA-256 digest from the manifest before declaring
  success (a missing manifest hash is allowed but logged).

The HTTP layer is once again injected so unit tests never touch the
network. The default opener is :func:`urllib.request.urlopen`,
matching the convention from :mod:`~src.services.updater.check`.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ContextManager, Iterator, Optional, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.paths import get_user_data_dir

from .schema import UpdateDownloadError, UpdateInfo

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KiB
DEFAULT_USER_AGENT = "Neloaica-Updater"

ProgressCallback = Callable[[int, Optional[int]], None]
"""``progress(bytes_so_far, total_bytes_or_None)``.

``total_bytes`` is ``None`` when the server does not advertise a
``Content-Length`` header (rare for GitHub releases but still
possible behind certain proxies).
"""

CancelPredicate = Callable[[], bool]
"""Called between chunks; return ``True`` to abort the download."""


# ---------------------------------------------------------------
# HTTP opener abstraction (injected for tests)
# ---------------------------------------------------------------


class _ResponseLike(Protocol):
    def read(self, size: int) -> bytes: ...
    def getheader(self, name: str, default: Optional[str] = None) -> Optional[str]: ...


HttpOpener = Callable[[str, float], ContextManager[_ResponseLike]]


@contextmanager
def _urllib_opener(url: str, timeout: float) -> Iterator[_ResponseLike]:
    """Default opener wrapping :func:`urllib.request.urlopen`.

    Yields the raw response object so the caller can call
    ``read(chunk)`` and ``getheader("Content-Length")`` on it.
    """
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 (trusted)
        yield response


# ---------------------------------------------------------------
# Result type
# ---------------------------------------------------------------


@dataclass(frozen=True)
class DownloadResult:
    """Outcome of a successful download.

    Returned from :meth:`UpdateDownloader.download` so the apply
    stage knows where to find the archive and what hash was actually
    observed (handy for diagnostics if the manifest hash was
    missing).
    """

    path: Path
    bytes_downloaded: int
    sha256: str
    info: UpdateInfo


# ---------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------


class UpdateDownloader:
    """Stream-download a release archive to disk and verify it.

    The downloader is single-use per :class:`UpdateInfo`: call
    :meth:`download`, get a :class:`DownloadResult`, hand it to the
    apply stage. If anything fails (network, hash mismatch,
    cancellation) the partial file is deleted before re-raising.
    """

    def __init__(
        self,
        *,
        target_dir: Optional[Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        opener: Optional[HttpOpener] = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        self._target_dir = target_dir
        self._timeout = timeout
        self._chunk_size = chunk_size
        self._opener = opener or _urllib_opener

    # ---------------------------------------------------------------
    # Public surface
    # ---------------------------------------------------------------

    @property
    def target_dir(self) -> Path:
        """Resolve lazily so tests can monkeypatch ``get_user_data_dir``."""
        if self._target_dir is not None:
            return self._target_dir
        return get_user_data_dir() / "updates"

    def target_path_for(self, info: UpdateInfo) -> Path:
        """Stable on-disk filename derived from version + URL.

        Versioning the filename lets us keep the old archive around
        until the apply stage finishes (and lets the user re-run an
        interrupted apply without re-downloading).
        """
        suffix = Path(info.download_url).suffix or ".zip"
        return self.target_dir / f"Neloaica-v{info.version}{suffix}"

    def download(
        self,
        info: UpdateInfo,
        *,
        on_progress: Optional[ProgressCallback] = None,
        cancel: Optional[CancelPredicate] = None,
    ) -> DownloadResult:
        """Fetch ``info.download_url`` into :attr:`target_dir`.

        Returns a :class:`DownloadResult` on success. Raises
        :class:`UpdateDownloadError` for any IO / hash / cancellation
        failure. The partial file is deleted before re-raising so
        the caller can simply retry.
        """
        destination = self.target_path_for(info)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise UpdateDownloadError(
                f"Cannot create download directory {destination.parent}: {exc}"
            ) from exc

        temp_path = self._stream_to_temp(info, destination.parent, on_progress, cancel)
        try:
            digest = _hash_file(temp_path)
            if info.sha256 is not None and digest != info.sha256:
                raise UpdateDownloadError(
                    f"SHA-256 mismatch for {info.download_url}: "
                    f"expected {info.sha256}, got {digest}."
                )
            if info.sha256 is None:
                logger.warning(
                    "Manifest does not advertise sha256 for %s; " "skipping integrity check.",
                    info.download_url,
                )
            size = temp_path.stat().st_size
            _atomic_replace(temp_path, destination)
            logger.info(
                "Downloaded %s (%d bytes, sha256=%s) to %s",
                info.download_url,
                size,
                digest,
                destination,
            )
            return DownloadResult(
                path=destination,
                bytes_downloaded=size,
                sha256=digest,
                info=info,
            )
        except Exception:
            _silent_unlink(temp_path)
            raise

    # ---------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------

    def _stream_to_temp(
        self,
        info: UpdateInfo,
        target_dir: Path,
        on_progress: Optional[ProgressCallback],
        cancel: Optional[CancelPredicate],
    ) -> Path:
        fd, temp_name = tempfile.mkstemp(
            prefix=".neloaica-update-",
            suffix=".part",
            dir=str(target_dir),
        )
        temp_path = Path(temp_name)
        # Close the bare fd and re-open via Path so we can use a
        # context manager that always flushes / closes cleanly.
        os.close(fd)

        try:
            with self._opener(info.download_url, self._timeout) as response:
                total = _parse_content_length(response)
                downloaded = 0
                if on_progress is not None:
                    on_progress(0, total)
                with open(temp_path, "wb") as out:
                    while True:
                        if cancel is not None and cancel():
                            raise UpdateDownloadError(
                                f"Download cancelled by user at {downloaded} bytes."
                            )
                        chunk = response.read(self._chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if on_progress is not None:
                            on_progress(downloaded, total)
        except URLError as exc:
            _silent_unlink(temp_path)
            raise UpdateDownloadError(f"Cannot download {info.download_url}: {exc}") from exc
        except OSError as exc:
            _silent_unlink(temp_path)
            raise UpdateDownloadError(
                f"IO error while downloading {info.download_url}: {exc}"
            ) from exc
        except BaseException:
            # Cancellation and any other failure path must not leave
            # the partial ``.part`` file behind. We re-raise so the
            # caller still sees the original exception unchanged.
            _silent_unlink(temp_path)
            raise

        return temp_path


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _parse_content_length(response: _ResponseLike) -> Optional[int]:
    raw = response.getheader("Content-Length", None)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _hash_file(path: Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_replace(src: Path, dst: Path) -> None:
    # ``Path.replace`` is atomic on the same filesystem (which it
    # always is here because we put the temp file in the same
    # directory as the destination). ``shutil.move`` falls back to
    # copy+delete across drives so we prefer ``replace``.
    try:
        src.replace(dst)
    except OSError:
        shutil.move(str(src), str(dst))


def _silent_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.debug("Could not remove partial download %s: %s", path, exc)


__all__ = [
    "CancelPredicate",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "DownloadResult",
    "HttpOpener",
    "ProgressCallback",
    "UpdateDownloader",
]
