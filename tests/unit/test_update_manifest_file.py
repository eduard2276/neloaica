"""Tests for ``update-manifest.json`` (the committed file).

These guard the file we ship at the URL the in-app updater polls
(``raw.githubusercontent.com/.../main/update-manifest.json``). The
schema must always parse via :class:`UpdateInfo.from_manifest_entry`
so a malformed manifest never reaches production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.updater import UpdateChannel, UpdateInfo

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "update-manifest.json"


@pytest.fixture(scope="module")
def manifest():
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    return json.loads(text)


class TestManifestFile:
    def test_exists(self):
        assert MANIFEST_PATH.is_file(), MANIFEST_PATH

    def test_is_valid_json(self):
        # Re-read independently of the fixture so this test stays
        # isolated; a malformed file would skip the fixture loading.
        text = MANIFEST_PATH.read_text(encoding="utf-8")
        json.loads(text)

    def test_root_is_object(self, manifest):
        assert isinstance(manifest, dict)

    def test_has_stable_channel(self, manifest):
        assert "stable" in manifest

    def test_stable_parses_as_update_info(self, manifest):
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, manifest["stable"])
        assert info.version is not None
        assert info.download_url.startswith("https://")

    def test_stable_download_url_points_at_github_releases(self, manifest):
        url = manifest["stable"]["download_url"]
        assert "github.com/eduard2276/neloaica/releases/download/" in url

    def test_optional_beta_entry_is_valid(self, manifest):
        # Skip when the file does not yet expose a beta channel.
        if "beta" not in manifest:
            pytest.skip("No beta channel published yet.")
        info = UpdateInfo.from_manifest_entry(UpdateChannel.BETA, manifest["beta"])
        assert info.channel is UpdateChannel.BETA
