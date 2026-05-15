"""Tests for ``src/services/updater/version.py``."""

from __future__ import annotations

import pytest

from src.services.updater import Version

# ===========================================================================
# TestParse
# ===========================================================================


class TestParse:
    def test_canonical(self):
        assert Version.parse("1.2.3") == Version(1, 2, 3)

    def test_with_v_prefix(self):
        assert Version.parse("v1.2.3") == Version(1, 2, 3)

    def test_strips_whitespace(self):
        assert Version.parse("  v1.2.3  ") == Version(1, 2, 3)

    def test_large_numbers(self):
        assert Version.parse("v123.456.789") == Version(123, 456, 789)

    def test_zero_components_allowed(self):
        assert Version.parse("0.0.0") == Version(0, 0, 0)

    @pytest.mark.parametrize(
        "bad",
        ["1.2", "1.2.3.4", "1.2.x", "", "v", "1..2.3", "1.2.3-beta", "1.2.3+build"],
    )
    def test_rejects_non_strict_semver(self, bad):
        with pytest.raises(ValueError):
            Version.parse(bad)

    def test_rejects_non_string(self):
        with pytest.raises(TypeError):
            Version.parse(123)  # type: ignore[arg-type]


# ===========================================================================
# TestCoerce
# ===========================================================================


class TestCoerce:
    def test_returns_self_when_already_version(self):
        v = Version(1, 2, 3)
        assert Version.coerce(v) is v

    def test_parses_string(self):
        assert Version.coerce("1.2.3") == Version(1, 2, 3)

    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            Version.coerce("nope")


# ===========================================================================
# TestOrdering
# ===========================================================================


class TestOrdering:
    def test_major_dominates(self):
        assert Version(2, 0, 0) > Version(1, 99, 99)

    def test_minor_dominates_when_major_equal(self):
        assert Version(1, 1, 0) > Version(1, 0, 99)

    def test_patch_breaks_tie(self):
        assert Version(1, 1, 2) > Version(1, 1, 1)

    def test_equal(self):
        assert Version(1, 2, 3) == Version(1, 2, 3)

    def test_lt_chain(self):
        v = sorted([Version(1, 2, 3), Version(0, 9, 9), Version(2, 0, 0)])
        assert v == [Version(0, 9, 9), Version(1, 2, 3), Version(2, 0, 0)]

    def test_hashable(self):
        s = {Version(1, 0, 0), Version(1, 0, 0), Version(2, 0, 0)}
        assert s == {Version(1, 0, 0), Version(2, 0, 0)}


# ===========================================================================
# TestRendering
# ===========================================================================


class TestRendering:
    def test_str(self):
        assert str(Version(1, 2, 3)) == "1.2.3"

    def test_with_v_prefix(self):
        assert Version(1, 2, 3).with_v_prefix() == "v1.2.3"

    def test_repr_round_trip_with_dataclass_default(self):
        # Defensive: dataclass-generated repr should mention all fields.
        rendered = repr(Version(1, 2, 3))
        assert "major=1" in rendered and "minor=2" in rendered and "patch=3" in rendered


# ===========================================================================
# TestIsNewerThan
# ===========================================================================


class TestIsNewerThan:
    def test_against_string(self):
        assert Version(1, 2, 3).is_newer_than("1.2.2") is True
        assert Version(1, 2, 3).is_newer_than("1.2.3") is False
        assert Version(1, 2, 3).is_newer_than("2.0.0") is False

    def test_against_version(self):
        assert Version(2, 0, 0).is_newer_than(Version(1, 99, 99)) is True

    def test_rejects_garbage_input(self):
        with pytest.raises(ValueError):
            Version(1, 2, 3).is_newer_than("nope")
