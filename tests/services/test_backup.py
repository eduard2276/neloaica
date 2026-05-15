"""Tests for the database backup service.

`src/services/backup.py` provides:
  * ensure_backups_dir()
  * get_database_path()
  * create_backup(backup_type)            → (path, success)
  * cleanup_old_backups()                 → keep at most MAX_BACKUPS (=7)
  * get_all_backups()                     → list with metadata
  * should_create_daily_backup()          → True if no backup created today
  * restore_backup(backup_path)           → bool, also creates a safety copy

All filesystem operations are redirected to a per-test tmp directory by
patching `BACKUPS_DIR` and `get_database_path` so we never touch the
real `neloaica.db` or `backups/`.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services import backup as backup_mod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dummy_db(path: Path, contents: bytes = b"SQLite format 3\x00") -> Path:
    """Write a stub binary file that looks like a SQLite DB on disk."""
    path.write_bytes(contents)
    return path


@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    """Redirect BACKUPS_DIR and the database path to a tmp folder."""
    db_path = tmp_path / "neloaica.db"
    _make_dummy_db(db_path)
    backups_dir = tmp_path / "backups"

    monkeypatch.setattr(backup_mod, "BACKUPS_DIR", backups_dir)
    monkeypatch.setattr(backup_mod, "get_database_path", lambda: db_path)
    return {"db_path": db_path, "backups_dir": backups_dir}


# ===========================================================================
# TestEnsureBackupsDir
# ===========================================================================


class TestEnsureBackupsDir:
    def test_creates_directory(self, tmp_dirs):
        assert not tmp_dirs["backups_dir"].exists()
        backup_mod.ensure_backups_dir()
        assert tmp_dirs["backups_dir"].is_dir()

    def test_idempotent(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        backup_mod.ensure_backups_dir()
        assert tmp_dirs["backups_dir"].is_dir()


# ===========================================================================
# TestCreateBackup
# ===========================================================================


class TestCreateBackup:
    def test_happy_path_returns_path_and_true(self, tmp_dirs):
        path, ok = backup_mod.create_backup("manual")
        assert ok is True
        assert path.endswith(".db")
        assert Path(path).exists()

    def test_filename_carries_type_token(self, tmp_dirs):
        for kind in ("manual", "auto", "startup", "pre-receipt"):
            path, ok = backup_mod.create_backup(kind)
            assert ok
            assert kind in Path(path).name

    def test_failure_when_source_db_missing(self, tmp_dirs):
        tmp_dirs["db_path"].unlink()
        path, ok = backup_mod.create_backup("manual")
        assert ok is False
        assert path == ""

    def test_failure_when_copy_raises(self, tmp_dirs):
        with patch("src.services.backup.shutil.copy2", side_effect=OSError("disk full")):
            path, ok = backup_mod.create_backup("manual")
        assert ok is False
        assert path == ""


# ===========================================================================
# TestCleanupOldBackups
# ===========================================================================


class TestCleanupOldBackups:
    def test_keeps_only_max(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        # Create 10 backups with descending mtime
        now = datetime.now().timestamp()
        for i in range(10):
            f = tmp_dirs["backups_dir"] / f"neloaica_backup_manual_2026-05-{i+1:02d}_10-00-00.db"
            f.write_bytes(b"x")
            ts = now - i * 3600
            import os

            os.utime(f, (ts, ts))

        backup_mod.cleanup_old_backups()
        remaining = list(tmp_dirs["backups_dir"].glob("neloaica_backup_*.db"))
        assert len(remaining) == backup_mod.MAX_BACKUPS

    def test_does_nothing_when_under_limit(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        (tmp_dirs["backups_dir"] / "neloaica_backup_manual_x.db").write_bytes(b"x")
        backup_mod.cleanup_old_backups()
        assert (tmp_dirs["backups_dir"] / "neloaica_backup_manual_x.db").exists()

    def test_missing_dir_is_silent(self, tmp_dirs):
        backup_mod.cleanup_old_backups()  # backups dir does not exist


# ===========================================================================
# TestGetAllBackups
# ===========================================================================


class TestGetAllBackups:
    def test_empty(self, tmp_dirs):
        assert backup_mod.get_all_backups() == []

    def test_returns_metadata(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        f = tmp_dirs["backups_dir"] / "neloaica_backup_manual_2026-05-15_10-00-00.db"
        f.write_bytes(b"hello")
        rows = backup_mod.get_all_backups()
        assert len(rows) == 1
        row = rows[0]
        assert row["name"] == f.name
        assert row["size"] == 5
        assert isinstance(row["date"], datetime)

    def test_sorted_newest_first(self, tmp_dirs):
        import os

        backup_mod.ensure_backups_dir()
        a = tmp_dirs["backups_dir"] / "neloaica_backup_manual_a.db"
        b = tmp_dirs["backups_dir"] / "neloaica_backup_manual_b.db"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        now = datetime.now().timestamp()
        os.utime(a, (now - 3600, now - 3600))
        os.utime(b, (now, now))
        rows = backup_mod.get_all_backups()
        assert [r["name"] for r in rows] == [b.name, a.name]


# ===========================================================================
# TestShouldCreateDailyBackup
# ===========================================================================


class TestShouldCreateDailyBackup:
    def test_true_when_no_dir(self, tmp_dirs):
        assert backup_mod.should_create_daily_backup() is True

    def test_true_when_no_backup_today(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d_%H-%M-%S")
        (tmp_dirs["backups_dir"] / f"neloaica_backup_manual_{yesterday}.db").write_bytes(b"x")
        assert backup_mod.should_create_daily_backup() is True

    def test_false_when_backup_exists_today(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        today = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        (tmp_dirs["backups_dir"] / f"neloaica_backup_manual_{today}.db").write_bytes(b"x")
        assert backup_mod.should_create_daily_backup() is False


# ===========================================================================
# TestRestoreBackup
# ===========================================================================


class TestRestoreBackup:
    def test_failure_when_file_missing(self, tmp_dirs):
        assert backup_mod.restore_backup(str(tmp_dirs["backups_dir"] / "nope.db")) is False

    def test_overwrites_db_and_creates_safety_copy(self, tmp_dirs):
        backup_mod.ensure_backups_dir()
        backup_file = tmp_dirs["backups_dir"] / "neloaica_backup_manual_x.db"
        backup_file.write_bytes(b"NEW DATA")

        tmp_dirs["db_path"].write_bytes(b"OLD DATA")

        ok = backup_mod.restore_backup(str(backup_file))
        assert ok is True
        assert tmp_dirs["db_path"].read_bytes() == b"NEW DATA"

        # A safety copy should exist beside the (mocked) db
        safety_copies = list(tmp_dirs["db_path"].parent.glob("neloaica_before_restore_*.db"))
        assert len(safety_copies) == 1
        assert safety_copies[0].read_bytes() == b"OLD DATA"

    def test_returns_false_if_copy_raises(self, tmp_dirs):
        backup_file = tmp_dirs["backups_dir"]
        backup_file.mkdir(parents=True, exist_ok=True)
        backup_path = backup_file / "neloaica_backup_manual_x.db"
        backup_path.write_bytes(b"x")
        with patch("src.services.backup.shutil.copy2", side_effect=OSError("nope")):
            assert backup_mod.restore_backup(str(backup_path)) is False


# ===========================================================================
# TestRoundTrip
# ===========================================================================


class TestRoundTrip:
    def test_create_then_get_all_returns_one(self, tmp_dirs):
        path, ok = backup_mod.create_backup("manual")
        assert ok
        rows = backup_mod.get_all_backups()
        assert len(rows) == 1
        assert rows[0]["path"] == path

    def test_create_more_than_max_triggers_cleanup(self, tmp_dirs):
        for _ in range(backup_mod.MAX_BACKUPS + 3):
            backup_mod.create_backup("manual")
        # Even with cleanup triggered after each create, the max must hold
        rows = backup_mod.get_all_backups()
        assert len(rows) <= backup_mod.MAX_BACKUPS


# ===========================================================================
# TestBackupsLocation
# ===========================================================================


class TestBackupsLocation:
    """The default ``BACKUPS_DIR`` must come from ``src.paths.get_backups_dir``.

    These tests exercise the module-level constant rather than the
    per-test ``tmp_dirs`` override so we know the production wiring is
    correct.
    """

    def test_default_backups_dir_matches_paths_module(self):
        from src.paths import get_backups_dir

        # ``BACKUPS_DIR`` is captured at module import time. It must equal
        # what ``get_backups_dir`` would return for the same dev/frozen
        # context — i.e. project root in dev.
        assert backup_mod.BACKUPS_DIR == get_backups_dir()

    def test_default_backups_dir_lives_under_user_data_dir(self):
        from src.paths import get_user_data_dir

        assert backup_mod.BACKUPS_DIR.parent == get_user_data_dir()
        assert backup_mod.BACKUPS_DIR.name == "backups"


# ===========================================================================
# TestLoggingInsteadOfPrint
# ===========================================================================


class TestLoggingInsteadOfPrint:
    """Status messages must flow through ``logging`` so they end up in the
    rotating log file instead of stdout."""

    def test_create_backup_failure_emits_log(self, tmp_dirs, caplog):
        with caplog.at_level(logging.ERROR, logger="src.services.backup"):
            with patch("src.services.backup.shutil.copy2", side_effect=OSError("disk full")):
                _, ok = backup_mod.create_backup("manual")
        assert ok is False
        assert any("Failed to create backup" in r.message for r in caplog.records)

    def test_cleanup_logs_when_removing_old_files(self, tmp_dirs, caplog):
        backup_mod.ensure_backups_dir()
        # Build MAX_BACKUPS+2 files with descending mtimes so cleanup deletes 2.
        import os

        now = datetime.now().timestamp()
        for i in range(backup_mod.MAX_BACKUPS + 2):
            f = tmp_dirs["backups_dir"] / f"neloaica_backup_manual_{i:02d}.db"
            f.write_bytes(b"x")
            ts = now - i * 60
            os.utime(f, (ts, ts))

        with caplog.at_level(logging.INFO, logger="src.services.backup"):
            backup_mod.cleanup_old_backups()
        removed = [r for r in caplog.records if "Removed old backup" in r.message]
        assert len(removed) == 2

    def test_restore_logs_success(self, tmp_dirs, caplog):
        backup_mod.ensure_backups_dir()
        backup_file = tmp_dirs["backups_dir"] / "neloaica_backup_manual_x.db"
        backup_file.write_bytes(b"NEW")
        tmp_dirs["db_path"].write_bytes(b"OLD")

        with caplog.at_level(logging.INFO, logger="src.services.backup"):
            ok = backup_mod.restore_backup(str(backup_file))
        assert ok is True
        messages = [r.message for r in caplog.records]
        assert any("Database restored from" in m for m in messages)
        assert any("Safety backup created" in m for m in messages)

    def test_no_print_calls_in_module_source(self):
        """Guard against accidentally re-introducing ``print`` calls."""
        import inspect

        source = inspect.getsource(backup_mod)
        # Strip docstrings/string literals containing the word "print" out
        # by checking for actual call syntax. ``print(`` (function call) is
        # what we want to forbid.
        assert "print(" not in source
