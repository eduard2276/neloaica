"""Tests for ``src/services/updater/download.py``.

The HTTP layer is replaced by a fake opener (a ``contextmanager``)
so no test ever touches the network. Filesystem effects are scoped
to per-test ``tmp_path``.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import pytest

from src.services.updater import (
    DownloadResult,
    UpdateChannel,
    UpdateDownloader,
    UpdateDownloadError,
    UpdateInfo,
)

# ===========================================================================
# Helpers
# ===========================================================================


class _FakeResponse:
    """Minimal stand-in for the object returned by ``urlopen``.

    Reads from an in-memory buffer in arbitrary-sized chunks and
    exposes ``getheader`` so the downloader can detect
    ``Content-Length``.
    """

    def __init__(self, payload: bytes, *, content_length: object = "auto"):
        self._buffer = BytesIO(payload)
        if content_length == "auto":
            self._headers = {"Content-Length": str(len(payload))}
        elif content_length is None:
            self._headers = {}
        else:
            self._headers = {"Content-Length": str(content_length)}

    def read(self, size: int) -> bytes:
        return self._buffer.read(size)

    def getheader(self, name: str, default=None):
        return self._headers.get(name, default)


def _make_opener(payload: bytes, *, content_length: object = "auto"):
    captured = {"url": None, "timeout": None, "calls": 0}

    @contextmanager
    def opener(url: str, timeout: float):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["calls"] += 1
        yield _FakeResponse(payload, content_length=content_length)

    opener.captured = captured  # type: ignore[attr-defined]
    return opener


def _opener_raising(exc: Exception):
    @contextmanager
    def opener(url: str, timeout: float):
        raise exc
        yield  # pragma: no cover - unreachable

    return opener


def _info(
    version: str, *, sha256: object = "auto", url: str = "https://example.com/Neloaica-vX.zip"
):
    """Build an ``UpdateInfo`` for tests.

    ``sha256='auto'`` means the caller will fill it after computing
    the expected payload digest; pass ``None`` to skip the integrity
    check, or any 64-char hex string to inject a value.
    """
    entry = {"version": version, "download_url": url}
    if sha256 != "auto":
        if sha256 is not None:
            entry["sha256"] = sha256
    else:
        # placeholder; tests override via dataclasses.replace
        pass
    return UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, entry)


def _sha256_of(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ===========================================================================
# TestConstruction
# ===========================================================================


class TestConstruction:
    def test_rejects_non_positive_chunk_size(self):
        with pytest.raises(ValueError):
            UpdateDownloader(chunk_size=0)
        with pytest.raises(ValueError):
            UpdateDownloader(chunk_size=-1)

    def test_target_dir_defaults_to_user_data_updates(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.services.updater.download.get_user_data_dir", lambda: tmp_path)
        downloader = UpdateDownloader()
        assert downloader.target_dir == tmp_path / "updates"

    def test_target_dir_override_wins(self, tmp_path):
        custom = tmp_path / "custom"
        downloader = UpdateDownloader(target_dir=custom)
        assert downloader.target_dir == custom


# ===========================================================================
# TestTargetPathFor
# ===========================================================================


class TestTargetPathFor:
    def test_uses_version_in_filename(self, tmp_path):
        info = _info("1.2.3", sha256=None)
        downloader = UpdateDownloader(target_dir=tmp_path)
        assert downloader.target_path_for(info).name == "Neloaica-v1.2.3.zip"

    def test_preserves_url_extension(self, tmp_path):
        info = _info(
            "1.2.3",
            sha256=None,
            url="https://example.com/Neloaica-v1.2.3-windows.7z",
        )
        downloader = UpdateDownloader(target_dir=tmp_path)
        assert downloader.target_path_for(info).suffix == ".7z"

    def test_defaults_to_zip_when_url_has_no_extension(self, tmp_path):
        info = _info("1.2.3", sha256=None, url="https://example.com/release-without-ext")
        downloader = UpdateDownloader(target_dir=tmp_path)
        assert downloader.target_path_for(info).suffix == ".zip"


# ===========================================================================
# TestDownloadHappyPath
# ===========================================================================


class TestDownloadHappyPath:
    def test_writes_payload_to_disk(self, tmp_path):
        payload = b"hello-world" * 1000
        digest = _sha256_of(payload)
        info = _info("1.2.3", sha256=digest)
        downloader = UpdateDownloader(
            target_dir=tmp_path, opener=_make_opener(payload), chunk_size=128
        )

        result = downloader.download(info)

        assert isinstance(result, DownloadResult)
        assert result.path.exists()
        assert result.path.read_bytes() == payload
        assert result.bytes_downloaded == len(payload)
        assert result.sha256 == digest
        assert result.info is info

    def test_creates_target_directory_if_missing(self, tmp_path):
        payload = b"abc"
        info = _info("1.0.0", sha256=_sha256_of(payload))
        nested = tmp_path / "deep" / "nested" / "updates"
        downloader = UpdateDownloader(target_dir=nested, opener=_make_opener(payload))
        result = downloader.download(info)
        assert result.path.parent == nested
        assert nested.is_dir()

    def test_passes_url_and_timeout_to_opener(self, tmp_path):
        payload = b"abc"
        info = _info(
            "1.0.0",
            sha256=_sha256_of(payload),
            url="https://example.com/special.zip",
        )
        opener = _make_opener(payload)
        UpdateDownloader(target_dir=tmp_path, timeout=42.0, opener=opener).download(info)
        assert opener.captured["url"] == "https://example.com/special.zip"
        assert opener.captured["timeout"] == 42.0


# ===========================================================================
# TestProgressCallback
# ===========================================================================


class TestProgressCallback:
    def test_reports_total_when_known(self, tmp_path):
        payload = b"x" * 1000
        info = _info("1.0.0", sha256=_sha256_of(payload))
        events: list[tuple[int, object]] = []

        UpdateDownloader(
            target_dir=tmp_path, opener=_make_opener(payload), chunk_size=128
        ).download(info, on_progress=lambda done, total: events.append((done, total)))

        # First event must be (0, total).
        assert events[0] == (0, 1000)
        # Last event must reach the full payload.
        assert events[-1][0] == 1000
        # Total is reported on every event.
        assert all(total == 1000 for _, total in events)
        # Progress is monotonically non-decreasing.
        for prev, curr in zip(events, events[1:]):
            assert curr[0] >= prev[0]

    def test_reports_none_when_total_missing(self, tmp_path):
        payload = b"y" * 256
        info = _info("1.0.0", sha256=_sha256_of(payload))
        events: list[tuple[int, object]] = []

        UpdateDownloader(
            target_dir=tmp_path,
            opener=_make_opener(payload, content_length=None),
            chunk_size=64,
        ).download(info, on_progress=lambda d, t: events.append((d, t)))

        assert events[0] == (0, None)
        assert events[-1][0] == 256
        assert all(total is None for _, total in events)

    def test_no_callback_is_ok(self, tmp_path):
        payload = b"abc"
        info = _info("1.0.0", sha256=_sha256_of(payload))
        UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload)).download(
            info
        )  # no on_progress; must not raise


# ===========================================================================
# TestCancellation
# ===========================================================================


class TestCancellation:
    def test_cancel_predicate_aborts_and_cleans_up(self, tmp_path):
        payload = b"x" * 10_000
        info = _info("1.0.0", sha256=_sha256_of(payload))
        downloader = UpdateDownloader(
            target_dir=tmp_path,
            opener=_make_opener(payload),
            chunk_size=128,
        )

        with pytest.raises(UpdateDownloadError) as ei:
            downloader.download(info, cancel=lambda: True)
        assert "cancelled" in str(ei.value).lower()

        # No partial files left behind.
        leftovers = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert leftovers == []

    def test_cancel_after_some_progress(self, tmp_path):
        payload = b"x" * 10_000
        info = _info("1.0.0", sha256=_sha256_of(payload))

        state = {"chunks": 0}

        def cancel():
            state["chunks"] += 1
            return state["chunks"] > 3

        downloader = UpdateDownloader(
            target_dir=tmp_path,
            opener=_make_opener(payload),
            chunk_size=128,
        )
        with pytest.raises(UpdateDownloadError):
            downloader.download(info, cancel=cancel)

        # Even mid-stream cancel must not leave a final file.
        target = downloader.target_path_for(info)
        assert not target.exists()


# ===========================================================================
# TestSha256Verification
# ===========================================================================


class TestSha256Verification:
    def test_mismatch_raises_and_cleans_up(self, tmp_path):
        payload = b"hello"
        info = _info("1.0.0", sha256="a" * 64)  # wrong on purpose

        downloader = UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload))
        with pytest.raises(UpdateDownloadError) as ei:
            downloader.download(info)
        assert "SHA-256 mismatch" in str(ei.value)

        target = downloader.target_path_for(info)
        assert not target.exists()

    def test_match_succeeds(self, tmp_path):
        payload = b"hello-binary"
        info = _info("1.0.0", sha256=_sha256_of(payload))
        result = UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload)).download(info)
        assert result.sha256 == _sha256_of(payload)

    def test_missing_hash_is_allowed_but_warned(self, tmp_path, caplog):
        payload = b"trustme"
        # Build an UpdateInfo without sha256.
        info = UpdateInfo.from_manifest_entry(
            UpdateChannel.STABLE,
            {"version": "1.0.0", "download_url": "https://example.com/x.zip"},
        )
        assert info.sha256 is None

        with caplog.at_level("WARNING", logger="src.services.updater.download"):
            result = UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload)).download(
                info
            )

        assert result.sha256 == _sha256_of(payload)
        assert any("skipping integrity check" in r.message for r in caplog.records)


# ===========================================================================
# TestNetworkErrors
# ===========================================================================


class TestNetworkErrors:
    def test_url_error_wrapped(self, tmp_path):
        info = _info("1.0.0", sha256=_sha256_of(b""))
        downloader = UpdateDownloader(target_dir=tmp_path, opener=_opener_raising(URLError("dns")))
        with pytest.raises(UpdateDownloadError) as ei:
            downloader.download(info)
        assert "Cannot download" in str(ei.value)

    def test_oserror_wrapped(self, tmp_path):
        info = _info("1.0.0", sha256=_sha256_of(b""))
        downloader = UpdateDownloader(
            target_dir=tmp_path,
            opener=_opener_raising(OSError("connection reset")),
        )
        with pytest.raises(UpdateDownloadError) as ei:
            downloader.download(info)
        assert "IO error" in str(ei.value) or "Cannot download" in str(ei.value)

    def test_no_partial_files_on_network_error(self, tmp_path):
        info = _info("1.0.0", sha256=_sha256_of(b""))
        downloader = UpdateDownloader(target_dir=tmp_path, opener=_opener_raising(URLError("nope")))
        with pytest.raises(UpdateDownloadError):
            downloader.download(info)
        leftovers = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert leftovers == []


# ===========================================================================
# TestDirectoryCreationError
# ===========================================================================


class TestDirectoryCreationError:
    def test_mkdir_failure_wrapped(self, tmp_path, monkeypatch):
        info = _info("1.0.0", sha256=_sha256_of(b""))

        def boom(self, parents=False, exist_ok=False):
            raise OSError("read-only filesystem")

        monkeypatch.setattr(Path, "mkdir", boom)

        downloader = UpdateDownloader(target_dir=tmp_path / "child", opener=_make_opener(b""))
        with pytest.raises(UpdateDownloadError) as ei:
            downloader.download(info)
        assert "Cannot create download directory" in str(ei.value)


# ===========================================================================
# TestAtomicReplace
# ===========================================================================


class TestAtomicReplace:
    def test_overwrites_existing_file_atomically(self, tmp_path):
        payload = b"new-version-bits"
        info = _info("1.0.0", sha256=_sha256_of(payload))
        downloader = UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload))
        target = downloader.target_path_for(info)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"OLD")
        assert target.read_bytes() == b"OLD"

        result = downloader.download(info)
        assert result.path.read_bytes() == payload

    def test_temp_files_cleaned_up_on_success(self, tmp_path):
        payload = b"abc"
        info = _info("1.0.0", sha256=_sha256_of(payload))
        UpdateDownloader(target_dir=tmp_path, opener=_make_opener(payload)).download(info)
        leftovers = [p for p in tmp_path.rglob("*") if p.is_file() and p.suffix == ".part"]
        assert leftovers == []
