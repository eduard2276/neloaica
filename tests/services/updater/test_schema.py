"""Tests for ``src/services/updater/schema.py``."""

from __future__ import annotations

import pytest

from src.services.updater import (
    UpdateChannel,
    UpdateCheckError,
    UpdateError,
    UpdateInfo,
    Version,
)

# ===========================================================================
# TestUpdateChannel
# ===========================================================================


class TestUpdateChannel:
    def test_stable_value(self):
        assert UpdateChannel.STABLE.value == "stable"

    def test_beta_value(self):
        assert UpdateChannel.BETA.value == "beta"

    def test_from_value_canonical(self):
        assert UpdateChannel.from_value("stable") is UpdateChannel.STABLE
        assert UpdateChannel.from_value("beta") is UpdateChannel.BETA

    def test_from_value_case_insensitive(self):
        assert UpdateChannel.from_value("STABLE") is UpdateChannel.STABLE
        assert UpdateChannel.from_value(" Beta ") is UpdateChannel.BETA

    def test_from_value_rejects_unknown(self):
        with pytest.raises(ValueError):
            UpdateChannel.from_value("nightly")

    def test_from_value_rejects_non_string(self):
        with pytest.raises(ValueError):
            UpdateChannel.from_value(None)  # type: ignore[arg-type]


# ===========================================================================
# TestExceptionHierarchy
# ===========================================================================


class TestExceptionHierarchy:
    def test_check_error_is_update_error(self):
        assert issubclass(UpdateCheckError, UpdateError)

    def test_can_catch_via_base(self):
        try:
            raise UpdateCheckError("boom")
        except UpdateError as exc:
            assert "boom" in str(exc)


# ===========================================================================
# TestFromManifestEntry
# ===========================================================================


@pytest.fixture
def minimal_entry():
    return {
        "version": "1.2.3",
        "download_url": "https://example.com/Neloaica-v1.2.3-windows.zip",
    }


@pytest.fixture
def full_entry():
    return {
        "version": "v1.2.3",
        "download_url": "https://example.com/Neloaica-v1.2.3-windows.zip",
        "sha256": "a" * 64,
        "mandatory": True,
        "min_required_version": "1.0.0",
        "release_url": "https://github.com/x/y/releases/tag/v1.2.3",
        "release_notes_url": "https://github.com/x/y/releases/tag/v1.2.3",
        "future_field": "ignored-but-kept-in-raw",
    }


class TestFromManifestEntry:
    def test_minimal_entry(self, minimal_entry):
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert info.version == Version(1, 2, 3)
        assert info.channel is UpdateChannel.STABLE
        assert info.download_url == minimal_entry["download_url"]
        assert info.sha256 is None
        assert info.mandatory is False
        assert info.min_required_version is None
        assert info.release_url is None

    def test_full_entry(self, full_entry):
        info = UpdateInfo.from_manifest_entry(UpdateChannel.BETA, full_entry)
        assert info.version == Version(1, 2, 3)
        assert info.channel is UpdateChannel.BETA
        assert info.sha256 == "a" * 64
        assert info.mandatory is True
        assert info.min_required_version == Version(1, 0, 0)
        assert info.release_url == full_entry["release_url"]

    def test_unknown_fields_are_kept_in_raw(self, full_entry):
        info = UpdateInfo.from_manifest_entry(UpdateChannel.BETA, full_entry)
        assert info.raw["future_field"] == "ignored-but-kept-in-raw"

    def test_missing_version_raises(self, minimal_entry):
        del minimal_entry["version"]
        with pytest.raises(UpdateCheckError) as ei:
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert "version" in str(ei.value)

    def test_missing_download_url_raises(self, minimal_entry):
        del minimal_entry["download_url"]
        with pytest.raises(UpdateCheckError) as ei:
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert "download_url" in str(ei.value)

    def test_empty_download_url_raises(self, minimal_entry):
        minimal_entry["download_url"] = "   "
        with pytest.raises(UpdateCheckError) as ei:
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert "download_url" in str(ei.value)

    def test_invalid_version_raises(self, minimal_entry):
        minimal_entry["version"] = "not-a-version"
        with pytest.raises(UpdateCheckError):
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)

    def test_invalid_min_required_version_raises(self, minimal_entry):
        minimal_entry["min_required_version"] = "abc"
        with pytest.raises(UpdateCheckError):
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)

    def test_non_object_entry_rejected(self):
        with pytest.raises(UpdateCheckError):
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, [1, 2, 3])  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [123, ["a"], {"x": 1}])
    def test_invalid_sha256_type_rejected(self, minimal_entry, bad):
        minimal_entry["sha256"] = bad
        with pytest.raises(UpdateCheckError):
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)

    @pytest.mark.parametrize("bad", ["short", "g" * 64, "A" * 64 + "z", "abc"])
    def test_invalid_sha256_format_rejected(self, minimal_entry, bad):
        minimal_entry["sha256"] = bad
        with pytest.raises(UpdateCheckError):
            UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)

    def test_empty_sha256_is_treated_as_none(self, minimal_entry):
        minimal_entry["sha256"] = ""
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert info.sha256 is None

    def test_sha256_is_lowercased(self, minimal_entry):
        minimal_entry["sha256"] = "AB" * 32
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert info.sha256 == "ab" * 32

    def test_mandatory_coerced_to_bool(self, minimal_entry):
        minimal_entry["mandatory"] = 1
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, minimal_entry)
        assert info.mandatory is True


# ===========================================================================
# TestPredicates
# ===========================================================================


def _info(version: str, **overrides):
    entry = {
        "version": version,
        "download_url": "https://example.com/x.zip",
        **overrides,
    }
    return UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, entry)


class TestPredicates:
    def test_is_newer_than_current(self):
        info = _info("1.2.3")
        assert info.is_newer_than(Version(1, 2, 2)) is True
        assert info.is_newer_than(Version(1, 2, 3)) is False
        assert info.is_newer_than(Version(2, 0, 0)) is False

    def test_requires_upgrade_from_when_below_min(self):
        info = _info("2.0.0", min_required_version="1.5.0")
        assert info.requires_upgrade_from(Version(1, 4, 9)) is True
        assert info.requires_upgrade_from(Version(1, 5, 0)) is False

    def test_requires_upgrade_returns_false_when_no_min(self):
        info = _info("2.0.0")
        assert info.requires_upgrade_from(Version(1, 0, 0)) is False
