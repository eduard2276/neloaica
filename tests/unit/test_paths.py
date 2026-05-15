"""Tests for `src/paths.py` — path resolution for dev vs frozen mode.

The module exposes:
  * _is_frozen()         — bool from sys.frozen
  * get_app_dir()        — folder containing exe / project root in dev
  * get_bundle_dir()     — sys._MEIPASS in frozen mode, project root in dev

These tests run in dev mode only.
"""

import sys
from pathlib import Path
from unittest.mock import patch

from src import paths

# ===========================================================================
# TestIsFrozen
# ===========================================================================


class TestIsFrozen:
    def test_dev_mode_is_false(self):
        # Pytest runs the source tree, so sys.frozen should not be set.
        assert paths._is_frozen() is False

    def test_returns_true_when_attribute_set(self):
        with patch.object(sys, "frozen", True, create=True):
            assert paths._is_frozen() is True


# ===========================================================================
# TestGetAppDir
# ===========================================================================


class TestGetAppDir:
    def test_returns_path(self):
        assert isinstance(paths.get_app_dir(), Path)

    def test_dev_mode_resolves_to_project_root(self):
        p = paths.get_app_dir()
        # Project root must exist and contain the src/ folder
        assert p.exists()
        assert (p / "src").is_dir()

    def test_frozen_mode_uses_executable_parent(self):
        fake_exe = Path("C:/some/where/app.exe")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", str(fake_exe)),
        ):
            assert paths.get_app_dir() == fake_exe.parent


# ===========================================================================
# TestGetBundleDir
# ===========================================================================


class TestGetBundleDir:
    def test_dev_returns_project_root(self):
        # In dev mode bundle dir == app dir
        assert paths.get_bundle_dir() == paths.get_app_dir()

    def test_returns_path(self):
        assert isinstance(paths.get_bundle_dir(), Path)

    def test_frozen_uses_meipass(self):
        fake_dir = "C:/tmp/_MEI12345"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", fake_dir, create=True),
        ):
            assert paths.get_bundle_dir() == Path(fake_dir)


# ===========================================================================
# TestProjectStructure
# ===========================================================================


class TestProjectStructure:
    """Verify the dev paths point at what we actually expect."""

    def test_templates_dir_resolvable(self):
        templates = paths.get_bundle_dir() / "templates"
        assert templates.is_dir()

    def test_template_file_exists(self):
        # The Excel export uses this file
        tpl = paths.get_bundle_dir() / "templates" / "Template-deviz.xlsx"
        assert tpl.is_file()
