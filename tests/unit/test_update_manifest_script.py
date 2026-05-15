"""Tests for ``scripts/update_manifest.py``.

The script is what GitHub Actions runs after every release to keep
``update-manifest.json`` in sync. We exercise it end-to-end against a
temporary manifest copy: validation, entry rendering, idempotency,
preservation of other channels and unknown top-level keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make ``scripts/`` importable without installing the project.
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import update_manifest  # noqa: E402

# ===========================================================================
# Helpers
# ===========================================================================


def _write_manifest(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "update-manifest.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _common_argv(version="1.2.3", sha="a" * 64, channel="stable", **overrides):
    argv = [
        "--version",
        version,
        "--channel",
        channel,
        "--sha256",
        sha,
        "--owner",
        "eduard2276",
        "--repo",
        "neloaica",
        "--asset",
        f"Neloaica-v{version}-windows.zip",
    ]
    for key, value in overrides.items():
        argv += [f"--{key.replace('_', '-')}", value]
    return argv


# ===========================================================================
# TestNormalisers
# ===========================================================================


class TestNormalizeVersion:
    def test_strips_v_prefix(self):
        assert update_manifest.normalize_version("v1.2.3") == "1.2.3"

    def test_strips_whitespace(self):
        assert update_manifest.normalize_version(" 1.2.3 ") == "1.2.3"

    @pytest.mark.parametrize("bad", ["1.2", "abc", "1.2.x", "", "1.2.3-rc1"])
    def test_rejects_non_semver(self, bad):
        with pytest.raises(ValueError):
            update_manifest.normalize_version(bad)


class TestNormalizeSha256:
    def test_lowercases(self):
        assert update_manifest.normalize_sha256("A" * 64) == "a" * 64

    @pytest.mark.parametrize("bad", ["short", "g" * 64, "z" * 64, "", "  abc  ", "a" * 63])
    def test_rejects_bad_hex(self, bad):
        with pytest.raises(ValueError):
            update_manifest.normalize_sha256(bad)


# ===========================================================================
# TestBuildEntry
# ===========================================================================


class TestBuildEntry:
    def test_renders_minimal_entry(self):
        args = update_manifest.parse_args(_common_argv())
        entry = update_manifest.build_entry(args)
        assert entry["version"] == "1.2.3"
        assert entry["download_url"].endswith("v1.2.3/Neloaica-v1.2.3-windows.zip")
        assert "github.com/eduard2276/neloaica/releases/download/v1.2.3/" in entry["download_url"]
        assert entry["sha256"] == "a" * 64
        assert entry["mandatory"] is False
        assert entry["min_required_version"] == "0.0.0"
        assert entry["release_url"].endswith("/releases/tag/v1.2.3")
        assert entry["release_notes_url"] == entry["release_url"]

    def test_mandatory_flag_propagated(self):
        argv = _common_argv() + ["--mandatory"]
        entry = update_manifest.build_entry(update_manifest.parse_args(argv))
        assert entry["mandatory"] is True

    def test_min_required_version_propagated(self):
        argv = _common_argv() + ["--min-required-version", "v1.0.0"]
        entry = update_manifest.build_entry(update_manifest.parse_args(argv))
        assert entry["min_required_version"] == "1.0.0"

    def test_version_with_v_prefix_accepted(self):
        argv = _common_argv(version="v1.2.3")
        entry = update_manifest.build_entry(update_manifest.parse_args(argv))
        assert entry["version"] == "1.2.3"


# ===========================================================================
# TestUpdateManifest (the function)
# ===========================================================================


class TestUpdateManifestFunction:
    def test_writes_new_stable_entry(self, tmp_path):
        path = _write_manifest(tmp_path, {"stable": {"version": "1.0.0"}})
        entry = {"version": "1.2.3", "download_url": "https://x.example/y.zip"}
        changed = update_manifest.update_manifest(path, "stable", entry)
        assert changed is True
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["stable"] == entry

    def test_idempotent_when_no_changes(self, tmp_path):
        entry = {
            "version": "1.0.0",
            "download_url": "https://x.example/y.zip",
            "sha256": "a" * 64,
            "mandatory": False,
            "min_required_version": "0.0.0",
            "release_url": "r",
            "release_notes_url": "r",
        }
        path = _write_manifest(tmp_path, {"stable": entry})
        # Pre-write the same content the function would emit so a
        # second update is a true no-op.
        canonical = json.dumps({"stable": entry}, indent=2, sort_keys=False) + "\n"
        path.write_text(canonical, encoding="utf-8")
        changed = update_manifest.update_manifest(path, "stable", entry)
        assert changed is False
        assert path.read_text(encoding="utf-8") == canonical

    def test_preserves_other_channels(self, tmp_path):
        existing = {
            "stable": {"version": "1.0.0"},
            "beta": {"version": "2.0.0-keep", "download_url": "https://x/y.zip"},
        }
        path = _write_manifest(tmp_path, existing)
        new_entry = {"version": "1.5.0", "download_url": "https://x/y.zip"}
        update_manifest.update_manifest(path, "stable", new_entry)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["beta"] == existing["beta"]
        assert data["stable"] == new_entry

    def test_preserves_unknown_top_level_keys(self, tmp_path):
        existing = {
            "$schema": "./schema.json",
            "stable": {"version": "1.0.0"},
        }
        path = _write_manifest(tmp_path, existing)
        update_manifest.update_manifest(
            path,
            "stable",
            {"version": "1.5.0", "download_url": "https://x/y.zip"},
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["$schema"] == "./schema.json"

    def test_missing_file_raises(self, tmp_path):
        path = tmp_path / "nope.json"
        with pytest.raises(FileNotFoundError):
            update_manifest.update_manifest(path, "stable", {})

    def test_malformed_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError):
            update_manifest.update_manifest(path, "stable", {})

    def test_non_object_root_rejected(self, tmp_path):
        path = tmp_path / "arr.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError):
            update_manifest.update_manifest(path, "stable", {})

    def test_creates_channel_when_missing(self, tmp_path):
        path = _write_manifest(tmp_path, {"stable": {"version": "1.0.0"}})
        update_manifest.update_manifest(
            path,
            "beta",
            {"version": "1.1.0", "download_url": "https://x/y.zip"},
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "beta" in data
        assert data["beta"]["version"] == "1.1.0"

    def test_trailing_newline_preserved(self, tmp_path):
        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        update_manifest.update_manifest(
            path,
            "stable",
            {"version": "1.0.0", "download_url": "https://x/y.zip"},
        )
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")


# ===========================================================================
# TestMainEntryPoint
# ===========================================================================


class TestMainEntryPoint:
    def test_happy_path_returns_zero(self, tmp_path, capsys):
        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        argv = _common_argv() + ["--manifest", str(path)]
        exit_code = update_manifest.main(argv)
        assert exit_code == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["stable"]["version"] == "1.2.3"
        captured = capsys.readouterr()
        assert "Updated" in captured.out

    def test_idempotent_run_returns_zero_and_prints_no_changes(self, tmp_path, capsys):
        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        argv = _common_argv() + ["--manifest", str(path)]
        update_manifest.main(argv)  # first run -> updates
        capsys.readouterr()
        exit_code = update_manifest.main(argv)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No changes" in captured.out

    def test_invalid_version_returns_one(self, tmp_path, capsys):
        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        argv = _common_argv(version="not-a-version") + ["--manifest", str(path)]
        exit_code = update_manifest.main(argv)
        assert exit_code == 1
        assert "error" in capsys.readouterr().err.lower()

    def test_invalid_sha_returns_one(self, tmp_path, capsys):
        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        argv = _common_argv(sha="not-hex") + ["--manifest", str(path)]
        exit_code = update_manifest.main(argv)
        assert exit_code == 1

    def test_missing_manifest_returns_two(self, tmp_path, capsys):
        argv = _common_argv() + ["--manifest", str(tmp_path / "missing.json")]
        exit_code = update_manifest.main(argv)
        assert exit_code == 2
        assert "error" in capsys.readouterr().err.lower()

    def test_invalid_channel_rejected_by_argparse(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            update_manifest.parse_args(_common_argv(channel="nightly"))


# ===========================================================================
# TestEndToEndAgainstUpdater
# ===========================================================================


class TestEndToEndAgainstUpdater:
    """Confirm what the script writes is consumable by the updater."""

    def test_written_manifest_parses_into_update_info(self, tmp_path):
        from src.services.updater import UpdateChannel, UpdateInfo

        path = _write_manifest(tmp_path, {"stable": {"version": "0.0.0"}})
        argv = _common_argv(version="1.2.3") + ["--manifest", str(path)]
        update_manifest.main(argv)

        data = json.loads(path.read_text(encoding="utf-8"))
        info = UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, data["stable"])
        assert str(info.version) == "1.2.3"
        assert info.sha256 == "a" * 64
        assert info.download_url.endswith("Neloaica-v1.2.3-windows.zip")
