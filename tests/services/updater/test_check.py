"""Tests for ``src/services/updater/check.py``.

The HTTP layer is replaced by an in-memory ``fetcher`` callable so no
test ever touches the network. The default ``_urllib_fetcher`` is
exercised at module-import smoke level only.
"""

from __future__ import annotations

import json
import logging
from urllib.error import URLError

import pytest

from src.services.updater import (
    UpdateChannel,
    UpdateChecker,
    UpdateCheckError,
    UpdateInfo,
    Version,
)
from src.services.updater.check import DEFAULT_MANIFEST_URL, DEFAULT_TIMEOUT

# ===========================================================================
# Helpers
# ===========================================================================


def _manifest(stable_version: str = "1.0.0", **overrides):
    """Build a minimal valid manifest with a ``stable`` channel."""
    entry = {
        "version": stable_version,
        "download_url": (f"https://example.com/Neloaica-v{stable_version}-windows.zip"),
        **overrides,
    }
    return {"stable": entry}


def _fetcher_returning(payload):
    """Build a fake fetcher closed over the given payload (bytes or str)."""
    if isinstance(payload, dict):
        payload = json.dumps(payload).encode("utf-8")
    elif isinstance(payload, str):
        payload = payload.encode("utf-8")

    captured = {"url": None, "timeout": None, "calls": 0}

    def fake(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["calls"] += 1
        return payload

    fake.captured = captured  # type: ignore[attr-defined]
    return fake


# ===========================================================================
# TestDefaults
# ===========================================================================


class TestDefaults:
    def test_manifest_url_points_at_main_branch(self):
        assert DEFAULT_MANIFEST_URL.startswith(
            "https://raw.githubusercontent.com/eduard2276/neloaica/"
        )
        assert "main/update-manifest.json" in DEFAULT_MANIFEST_URL

    def test_default_timeout_is_reasonable(self):
        assert 1 <= DEFAULT_TIMEOUT <= 60

    def test_constructor_defaults(self):
        checker = UpdateChecker(Version(1, 0, 0))
        assert checker.current_version == Version(1, 0, 0)
        assert checker.channel is UpdateChannel.STABLE
        assert checker.manifest_url == DEFAULT_MANIFEST_URL


# ===========================================================================
# TestCheck
# ===========================================================================


class TestCheck:
    def test_returns_info_when_newer(self):
        fetcher = _fetcher_returning(_manifest("1.2.3"))
        checker = UpdateChecker(Version(1, 0, 0), fetcher=fetcher)
        info = checker.check()
        assert isinstance(info, UpdateInfo)
        assert info.version == Version(1, 2, 3)
        assert info.channel is UpdateChannel.STABLE

    def test_returns_none_when_same_version(self):
        fetcher = _fetcher_returning(_manifest("1.2.3"))
        checker = UpdateChecker(Version(1, 2, 3), fetcher=fetcher)
        assert checker.check() is None

    def test_returns_none_when_older_published(self):
        # Defensive: the manifest somehow advertises an older build than
        # what is running. We never want to "downgrade" the user.
        fetcher = _fetcher_returning(_manifest("1.0.0"))
        checker = UpdateChecker(Version(1, 5, 0), fetcher=fetcher)
        assert checker.check() is None

    def test_passes_manifest_url_to_fetcher(self):
        fetcher = _fetcher_returning(_manifest("1.0.0"))
        UpdateChecker(
            Version(1, 0, 0),
            manifest_url="https://example.com/manifest.json",
            fetcher=fetcher,
        ).check()
        assert fetcher.captured["url"] == "https://example.com/manifest.json"

    def test_passes_timeout_to_fetcher(self):
        fetcher = _fetcher_returning(_manifest("1.0.0"))
        UpdateChecker(Version(1, 0, 0), timeout=7.5, fetcher=fetcher).check()
        assert fetcher.captured["timeout"] == 7.5

    def test_logs_when_update_available(self, caplog):
        fetcher = _fetcher_returning(_manifest("2.0.0"))
        checker = UpdateChecker(Version(1, 0, 0), fetcher=fetcher)
        with caplog.at_level(logging.INFO, logger="src.services.updater.check"):
            checker.check()
        assert any("Update available" in r.message for r in caplog.records)


# ===========================================================================
# TestChannelSelection
# ===========================================================================


class TestChannelSelection:
    def test_beta_channel_picks_beta_entry(self):
        manifest = {
            "stable": {
                "version": "1.0.0",
                "download_url": "https://example.com/s.zip",
            },
            "beta": {
                "version": "2.0.0",
                "download_url": "https://example.com/b.zip",
            },
        }
        fetcher = _fetcher_returning(manifest)
        info = UpdateChecker(Version(1, 0, 0), channel=UpdateChannel.BETA, fetcher=fetcher).check()
        assert info is not None
        assert info.version == Version(2, 0, 0)
        assert info.channel is UpdateChannel.BETA

    def test_missing_channel_raises_check_error(self):
        # Manifest only has stable, but client asks for beta.
        fetcher = _fetcher_returning(_manifest("1.0.0"))
        checker = UpdateChecker(Version(1, 0, 0), channel=UpdateChannel.BETA, fetcher=fetcher)
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "beta" in str(ei.value)


# ===========================================================================
# TestErrorPaths
# ===========================================================================


class TestErrorPaths:
    def test_network_error_wrapped(self):
        def boom(url, timeout):
            raise URLError("Temporary failure in name resolution")

        checker = UpdateChecker(Version(1, 0, 0), fetcher=boom)
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "Cannot reach manifest" in str(ei.value)

    def test_os_error_wrapped(self):
        def boom(url, timeout):
            raise OSError("connection reset")

        checker = UpdateChecker(Version(1, 0, 0), fetcher=boom)
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "Network error" in str(ei.value)

    def test_empty_payload(self):
        checker = UpdateChecker(Version(1, 0, 0), fetcher=_fetcher_returning(b""))
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "empty" in str(ei.value).lower()

    def test_invalid_json(self):
        checker = UpdateChecker(Version(1, 0, 0), fetcher=_fetcher_returning("not-json"))
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "valid JSON" in str(ei.value)

    def test_root_must_be_object(self):
        checker = UpdateChecker(Version(1, 0, 0), fetcher=_fetcher_returning("[1, 2]"))
        with pytest.raises(UpdateCheckError) as ei:
            checker.check()
        assert "JSON object" in str(ei.value)

    def test_malformed_channel_propagates(self):
        manifest = {"stable": {"version": "abc", "download_url": "x"}}
        checker = UpdateChecker(Version(1, 0, 0), fetcher=_fetcher_returning(manifest))
        with pytest.raises(UpdateCheckError):
            checker.check()


# ===========================================================================
# TestFetchManifest
# ===========================================================================


class TestFetchManifest:
    def test_returns_parsed_dict_for_all_channels(self):
        manifest = {
            "stable": {"version": "1.0.0", "download_url": "https://example.com/s.zip"},
            "beta": {"version": "1.1.0", "download_url": "https://example.com/b.zip"},
        }
        checker = UpdateChecker(Version(1, 0, 0), fetcher=_fetcher_returning(manifest))
        data = checker.fetch_manifest()
        assert set(data.keys()) == {"stable", "beta"}

    def test_propagates_network_error(self):
        def boom(url, timeout):
            raise URLError("dns")

        with pytest.raises(UpdateCheckError):
            UpdateChecker(Version(1, 0, 0), fetcher=boom).fetch_manifest()


# ===========================================================================
# TestRealUrllibFetcherImportable
# ===========================================================================


class TestRealUrllibFetcherImportable:
    """Smoke check that the default fetcher exists and is callable.

    Does NOT hit the network — just confirms the symbol so the
    constructor default does not silently break in some future
    refactor.
    """

    def test_default_fetcher_is_callable(self):
        from src.services.updater.check import _urllib_fetcher

        assert callable(_urllib_fetcher)
