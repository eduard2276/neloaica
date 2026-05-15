"""Tests for ``src/paths.py`` — path resolution for dev vs frozen mode.

The module exposes:
  * ``_is_frozen()``         — bool from ``sys.frozen``
  * ``get_app_dir()``        — folder containing exe / project root in dev
  * ``get_bundle_dir()``     — ``sys._MEIPASS`` in frozen mode, project root in dev
  * ``get_user_data_dir()``  — writable per-user directory; project root in dev
  * ``get_logs_dir()``       — ``user_data_dir/logs``
  * ``get_database_path()``  — ``user_data_dir/neloaica.db``
  * ``get_backups_dir()``    — ``user_data_dir/backups``
  * ``migrate_legacy_db()``  — best-effort move from legacy location

The cross-platform tests fake ``sys.platform`` and ``sys.frozen`` rather than
actually freezing the app — this keeps the suite portable.
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
# TestGetUserDataDir
# ===========================================================================


class TestGetUserDataDir:
    def test_dev_returns_project_root(self):
        # In dev mode user data lives in the workspace so contributors do not
        # accidentally pollute their real %LOCALAPPDATA% when running tests.
        assert paths.get_user_data_dir() == paths.get_app_dir()

    def test_frozen_windows_uses_localappdata(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", "D:/users/ecoras/AppData/Local")
        with patch.object(sys, "frozen", True, create=True):
            assert (
                paths.get_user_data_dir() == Path("D:/users/ecoras/AppData/Local") / paths.APP_NAME
            )

    def test_frozen_windows_falls_back_to_home(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        fake_home = Path("D:/users/fake")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(Path, "home", classmethod(lambda cls: fake_home)),
        ):
            expected = fake_home / "AppData" / "Local" / paths.APP_NAME
            assert paths.get_user_data_dir() == expected

    def test_frozen_macos(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        fake_home = Path("/Users/fake")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(Path, "home", classmethod(lambda cls: fake_home)),
        ):
            expected = fake_home / "Library" / "Application Support" / paths.APP_NAME
            assert paths.get_user_data_dir() == expected

    def test_frozen_linux_uses_xdg_data_home(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("XDG_DATA_HOME", "/data/xdg")
        with patch.object(sys, "frozen", True, create=True):
            assert paths.get_user_data_dir() == Path("/data/xdg") / paths.APP_NAME

    def test_frozen_linux_falls_back_to_local_share(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        fake_home = Path("/home/fake")
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(Path, "home", classmethod(lambda cls: fake_home)),
        ):
            expected = fake_home / ".local" / "share" / paths.APP_NAME
            assert paths.get_user_data_dir() == expected


# ===========================================================================
# TestDerivedPaths
# ===========================================================================


class TestDerivedPaths:
    def test_logs_dir_is_under_user_data(self):
        assert paths.get_logs_dir() == paths.get_user_data_dir() / "logs"

    def test_database_path_is_under_user_data(self):
        assert paths.get_database_path() == paths.get_user_data_dir() / "neloaica.db"

    def test_backups_dir_is_under_user_data(self):
        assert paths.get_backups_dir() == paths.get_user_data_dir() / "backups"

    def test_get_user_data_dir_is_not_created_implicitly(self, monkeypatch, tmp_path):
        # Pretending to be frozen with LOCALAPPDATA pointing into a tmp dir.
        # Querying the path must not create it on disk; consumers do that.
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        with patch.object(sys, "frozen", True, create=True):
            target = paths.get_user_data_dir()
        assert target == tmp_path / paths.APP_NAME
        assert not target.exists()


# ===========================================================================
# TestMigrateLegacyDb
# ===========================================================================


class TestMigrateLegacyDb:
    def test_returns_false_when_legacy_missing(self, tmp_path):
        legacy = tmp_path / "missing.db"
        new = tmp_path / "new" / "neloaica.db"
        assert paths.migrate_legacy_db(legacy, new) is False
        assert not new.exists()

    def test_moves_legacy_into_new_location(self, tmp_path):
        legacy = tmp_path / "legacy" / "neloaica.db"
        legacy.parent.mkdir()
        legacy.write_bytes(b"SQLite format 3\x00")
        new = tmp_path / "user_data" / "neloaica.db"

        assert paths.migrate_legacy_db(legacy, new) is True
        assert not legacy.exists()
        assert new.exists()
        assert new.read_bytes() == b"SQLite format 3\x00"

    def test_does_not_overwrite_existing_new(self, tmp_path):
        legacy = tmp_path / "legacy.db"
        legacy.write_bytes(b"OLD")
        new = tmp_path / "new" / "neloaica.db"
        new.parent.mkdir()
        new.write_bytes(b"AUTHORITATIVE")

        assert paths.migrate_legacy_db(legacy, new) is False
        # Both files still exist; the legacy one is left for the user to deal with.
        assert legacy.exists()
        assert new.read_bytes() == b"AUTHORITATIVE"

    def test_creates_parent_directory(self, tmp_path):
        legacy = tmp_path / "legacy.db"
        legacy.write_bytes(b"x")
        new = tmp_path / "deeply" / "nested" / "user_data" / "neloaica.db"
        assert not new.parent.exists()
        assert paths.migrate_legacy_db(legacy, new) is True
        assert new.parent.is_dir()

    def test_swallows_oserror(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy.db"
        legacy.write_bytes(b"x")
        new = tmp_path / "new" / "neloaica.db"

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(paths.shutil, "move", boom)
        assert paths.migrate_legacy_db(legacy, new) is False


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
