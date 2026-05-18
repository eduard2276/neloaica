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
# TestMigrateLegacyDir
# ===========================================================================


class TestMigrateLegacyDir:
    """Used for the ``backups/`` folder migration. Mirrors :func:`migrate_legacy_db`
    but at directory granularity."""

    def test_returns_zero_when_legacy_missing(self, tmp_path):
        legacy = tmp_path / "missing"
        new = tmp_path / "new"
        assert paths.migrate_legacy_dir(legacy, new) == 0
        assert not new.exists()

    def test_returns_zero_when_legacy_is_a_file(self, tmp_path):
        # Defensive: someone passes a file path instead of a directory.
        legacy = tmp_path / "not_a_dir"
        legacy.write_text("oops")
        new = tmp_path / "new"
        assert paths.migrate_legacy_dir(legacy, new) == 0

    def test_returns_zero_when_legacy_equals_new(self, tmp_path):
        # Dev-mode no-op: backups dir is the same as new dir.
        same = tmp_path / "backups"
        same.mkdir()
        (same / "neloaica_backup_manual_x.db").write_bytes(b"x")
        moved = paths.migrate_legacy_dir(same, same)
        assert moved == 0
        # File must still be there.
        assert (same / "neloaica_backup_manual_x.db").exists()

    def test_moves_all_files(self, tmp_path):
        legacy = tmp_path / "legacy"
        new = tmp_path / "user_data" / "backups"
        legacy.mkdir()
        for i in range(3):
            (legacy / f"neloaica_backup_manual_{i}.db").write_bytes(bytes([i]))

        moved = paths.migrate_legacy_dir(legacy, new)
        assert moved == 3
        assert not legacy.exists()  # cleaned up
        for i in range(3):
            assert (new / f"neloaica_backup_manual_{i}.db").read_bytes() == bytes([i])

    def test_creates_new_dir_when_missing(self, tmp_path):
        legacy = tmp_path / "legacy"
        legacy.mkdir()
        (legacy / "a.db").write_bytes(b"x")
        new = tmp_path / "deeply" / "nested" / "backups"

        assert not new.exists()
        moved = paths.migrate_legacy_dir(legacy, new)
        assert moved == 1
        assert new.is_dir()
        assert (new / "a.db").exists()

    def test_skips_files_that_already_exist_in_new(self, tmp_path):
        legacy = tmp_path / "legacy"
        new = tmp_path / "new"
        legacy.mkdir()
        new.mkdir()

        (legacy / "conflict.db").write_bytes(b"OLD")
        (legacy / "fresh.db").write_bytes(b"NEW")
        (new / "conflict.db").write_bytes(b"AUTHORITATIVE")

        moved = paths.migrate_legacy_dir(legacy, new)
        # Only "fresh.db" got moved; "conflict.db" stays in legacy.
        assert moved == 1
        assert (new / "conflict.db").read_bytes() == b"AUTHORITATIVE"
        assert (new / "fresh.db").read_bytes() == b"NEW"
        # Legacy folder still exists because the conflict file is left behind.
        assert legacy.exists()
        assert (legacy / "conflict.db").read_bytes() == b"OLD"
        assert not (legacy / "fresh.db").exists()

    def test_keeps_legacy_dir_when_files_remain(self, tmp_path):
        legacy = tmp_path / "legacy"
        new = tmp_path / "new"
        legacy.mkdir()
        (legacy / "stay.db").write_bytes(b"x")
        (new).mkdir()
        (new / "stay.db").write_bytes(b"already there")

        paths.migrate_legacy_dir(legacy, new)
        # Conflict → file untouched in legacy → legacy must NOT be removed.
        assert legacy.exists()
        assert (legacy / "stay.db").exists()

    def test_recurses_into_subdirectories(self, tmp_path):
        legacy = tmp_path / "legacy"
        new = tmp_path / "new"
        (legacy / "sub").mkdir(parents=True)
        (legacy / "top.db").write_bytes(b"a")
        (legacy / "sub" / "nested.db").write_bytes(b"b")

        moved = paths.migrate_legacy_dir(legacy, new)
        assert moved == 2
        assert (new / "top.db").read_bytes() == b"a"
        assert (new / "sub" / "nested.db").read_bytes() == b"b"
        assert not legacy.exists()

    def test_swallows_per_file_oserror(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy"
        new = tmp_path / "new"
        legacy.mkdir()
        (legacy / "a.db").write_bytes(b"a")
        (legacy / "b.db").write_bytes(b"b")

        original_move = paths.shutil.move
        calls = {"n": 0}

        def flaky_move(src, dst, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("transient")
            return original_move(src, dst, *args, **kwargs)

        monkeypatch.setattr(paths.shutil, "move", flaky_move)

        moved = paths.migrate_legacy_dir(legacy, new)
        # One file failed, the other succeeded.
        assert moved == 1
        # Legacy still has the failed file.
        assert legacy.exists()
        assert any(legacy.iterdir())

    def test_returns_int_not_bool(self, tmp_path):
        # Important for the bootstrap log line: it must be a count, not a flag.
        legacy = tmp_path / "legacy"
        new = tmp_path / "new"
        legacy.mkdir()
        (legacy / "a.db").write_bytes(b"x")
        result = paths.migrate_legacy_dir(legacy, new)
        assert isinstance(result, int)
        assert result == 1


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


# ===========================================================================
# TestLogoPaths
# ===========================================================================


class TestLogoPaths:
    """Logo assets live under ``templates/images/`` and must be
    resolvable both in dev mode and after PyInstaller bundles them
    under ``_MEIPASS``."""

    def test_png_path_under_templates_images(self):
        assert paths.get_logo_png_path() == (
            paths.get_bundle_dir() / "templates" / "images" / "Neloaica_logo.png"
        )

    def test_ico_path_under_templates_images(self):
        assert paths.get_logo_ico_path() == (
            paths.get_bundle_dir() / "templates" / "images" / "Neloaica_logo.ico"
        )

    def test_png_returns_path(self):
        assert isinstance(paths.get_logo_png_path(), Path)

    def test_ico_returns_path(self):
        assert isinstance(paths.get_logo_ico_path(), Path)

    def test_png_resolves_against_meipass_when_frozen(self):
        fake_dir = "C:/tmp/_MEI12345"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", fake_dir, create=True),
        ):
            assert paths.get_logo_png_path() == (
                Path(fake_dir) / "templates" / "images" / "Neloaica_logo.png"
            )

    def test_ico_resolves_against_meipass_when_frozen(self):
        fake_dir = "C:/tmp/_MEI12345"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", fake_dir, create=True),
        ):
            assert paths.get_logo_ico_path() == (
                Path(fake_dir) / "templates" / "images" / "Neloaica_logo.ico"
            )

    def test_logo_png_file_exists_in_repo(self):
        # Branding asset must ship with the repo — otherwise the sidebar
        # silently falls back to the text title and the spec file's
        # ``icon=...`` reference becomes a broken path.
        assert paths.get_logo_png_path().is_file()

    def test_logo_ico_file_exists_in_repo(self):
        assert paths.get_logo_ico_path().is_file()
