"""Tests for ``scripts/verify_tag_matches_version.py``.

The script is the gate that prevents a Release workflow from publishing
a build whose embedded version does not match the tag. Coverage:

  * `normalize_tag` strips whitespace and a leading ``v``.
  * `check` accepts only SemVer-shaped tags and only when they match
    the package version exactly.
  * `_read_package_version` reads ``__version__`` from
    ``src/__init__.py`` without importing the runtime package.
  * `main` returns the documented exit codes (0 / 1 / 2).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import verify_tag_matches_version as v

# ===========================================================================
# TestNormalizeTag
# ===========================================================================


class TestNormalizeTag:
    def test_strips_leading_v(self):
        assert v.normalize_tag("v1.2.3") == "1.2.3"

    def test_keeps_non_v_input(self):
        assert v.normalize_tag("1.2.3") == "1.2.3"

    def test_strips_whitespace(self):
        assert v.normalize_tag("  v1.2.3  ") == "1.2.3"

    def test_handles_empty_input(self):
        assert v.normalize_tag("") == ""
        assert v.normalize_tag(None) == ""  # type: ignore[arg-type]


# ===========================================================================
# TestCheck
# ===========================================================================


class TestCheck:
    def test_match_returns_true(self):
        ok, msg = v.check("v1.2.3", "1.2.3")
        assert ok is True
        assert "matches" in msg

    def test_match_without_v_prefix(self):
        ok, msg = v.check("1.2.3", "1.2.3")
        assert ok is True

    def test_mismatch_returns_false(self):
        ok, msg = v.check("v1.2.3", "1.2.4")
        assert ok is False
        assert "1.2.3" in msg and "1.2.4" in msg

    def test_invalid_tag_format(self):
        ok, msg = v.check("not-a-version", "1.0.0")
        assert ok is False
        assert "SemVer" in msg

    def test_missing_patch_component_rejected(self):
        ok, _ = v.check("v1.2", "1.2.0")
        assert ok is False

    def test_extra_component_rejected(self):
        ok, _ = v.check("v1.2.3.4", "1.2.3")
        assert ok is False

    def test_empty_tag_rejected(self):
        ok, _ = v.check("", "1.0.0")
        assert ok is False


# ===========================================================================
# TestReadPackageVersion
# ===========================================================================


class TestReadPackageVersion:
    def test_returns_real_version(self):
        from src import __version__

        assert v._read_package_version() == __version__

    def test_raises_when_file_missing(self, tmp_path, monkeypatch):
        # Point the resolver at a fake repo where src/__init__.py is missing.
        fake_repo = tmp_path / "fake"
        (fake_repo / "src").mkdir(parents=True)
        # Don't create __init__.py
        monkeypatch.setattr(
            v, "__file__", str(fake_repo / "scripts" / "verify_tag_matches_version.py")
        )
        with pytest.raises(FileNotFoundError):
            v._read_package_version()

    def test_raises_when_version_literal_missing(self, tmp_path, monkeypatch):
        fake_repo = tmp_path / "fake"
        (fake_repo / "src").mkdir(parents=True)
        (fake_repo / "src" / "__init__.py").write_text(
            "# no version literal here\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            v, "__file__", str(fake_repo / "scripts" / "verify_tag_matches_version.py")
        )
        with pytest.raises(ValueError):
            v._read_package_version()


# ===========================================================================
# TestMain
# ===========================================================================


class TestMain:
    def test_zero_when_tag_matches(self, capsys):
        from src import __version__

        rc = v.main(["script", f"v{__version__}"])
        assert rc == 0

    def test_one_when_tag_mismatches(self, capsys):
        from src import __version__

        # Build a version guaranteed to differ.
        major, minor, patch = (int(p) for p in __version__.split("."))
        bad = f"v{major}.{minor}.{patch + 99}"

        rc = v.main(["script", bad])
        assert rc == 1
        # Mismatch goes to stderr per the docstring contract.
        err = capsys.readouterr().err
        assert __version__ in err
        assert bad in err

    def test_two_when_no_tag_argument(self, capsys):
        rc = v.main(["script"])
        assert rc == 2

    def test_two_when_too_many_arguments(self, capsys):
        rc = v.main(["script", "v1.0.0", "extra"])
        assert rc == 2

    def test_two_when_package_version_unreadable(self, monkeypatch, capsys):
        def boom():
            raise OSError("cannot read")

        monkeypatch.setattr(v, "_read_package_version", boom)
        rc = v.main(["script", "v1.0.0"])
        assert rc == 2

    def test_one_when_tag_is_garbage(self, capsys):
        rc = v.main(["script", "release-candidate"])
        assert rc == 1


# ===========================================================================
# TestProjectStructure
# ===========================================================================


class TestProjectStructure:
    """Smoke checks that the helper script is wired up correctly."""

    def test_script_file_exists(self):
        repo_root = Path(__file__).resolve().parent.parent.parent
        assert (repo_root / "scripts" / "verify_tag_matches_version.py").is_file()

    def test_scripts_package_init_exists(self):
        repo_root = Path(__file__).resolve().parent.parent.parent
        assert (repo_root / "scripts" / "__init__.py").is_file()
