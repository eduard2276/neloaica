"""Tests for the centralized application version.

The package version lives in ``src/__init__.py`` as ``__version__`` and is the
single source of truth for the running app, the packaging metadata and the
auto-update flow. These tests guard against:

  * the constant being removed or renamed;
  * the format drifting away from semantic versioning ``X.Y.Z`` (which the
    auto-update comparator expects);
  * the value falling out of sync with what ``pyproject.toml`` exposes.
"""

import re
import sys
from pathlib import Path

import pytest

import src

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.9/3.10
    import tomli as tomllib


SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$"
)


# ===========================================================================
# TestVersionConstant
# ===========================================================================


class TestVersionConstant:
    def test_version_is_defined(self):
        assert hasattr(src, "__version__"), "src.__version__ must be defined"

    def test_version_is_string(self):
        assert isinstance(src.__version__, str)

    def test_version_is_not_empty(self):
        assert src.__version__.strip() != ""

    def test_version_matches_semver(self):
        # The auto-update flow compares versions with packaging.version which
        # accepts PEP 440. We tighten to plain semver to keep release tags
        # predictable (``v1.2.3`` / ``v1.2.3-beta.1``).
        assert SEMVER_RE.match(src.__version__), (
            f"src.__version__ = {src.__version__!r} is not in X.Y.Z form"
        )


# ===========================================================================
# TestVersionPyprojectSync
# ===========================================================================


class TestVersionPyprojectSync:
    """Verify ``pyproject.toml`` reads the version from ``src/__init__.py``.

    We do not check that a literal version string in ``pyproject.toml`` matches
    the constant, because the project is configured with
    ``dynamic = ["version"]`` precisely so there is only one source of truth.
    """

    @pytest.fixture(scope="class")
    def pyproject(self):
        root = Path(__file__).resolve().parents[2]
        with (root / "pyproject.toml").open("rb") as f:
            return tomllib.load(f)

    def test_version_is_dynamic(self, pyproject):
        dynamic = pyproject.get("project", {}).get("dynamic", [])
        assert "version" in dynamic, (
            "pyproject.toml must declare version as dynamic so that "
            "src.__version__ remains the single source of truth"
        )

    def test_static_version_field_absent(self, pyproject):
        # If a static ``version = "x.y.z"`` field reappears, the dynamic block
        # is silently shadowed and the two values can drift. Fail loudly.
        assert "version" not in pyproject.get("project", {}), (
            "pyproject.toml [project] must not define a static `version` "
            "field; remove it and rely on dynamic resolution from src/__init__.py"
        )

    def test_dynamic_version_points_to_src(self, pyproject):
        dyn = (
            pyproject.get("tool", {})
            .get("setuptools", {})
            .get("dynamic", {})
            .get("version", {})
        )
        assert dyn.get("attr") == "src.__version__", (
            "[tool.setuptools.dynamic].version must read from "
            "`src.__version__` (got {!r})".format(dyn)
        )
