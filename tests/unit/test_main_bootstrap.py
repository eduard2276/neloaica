"""Tests for ``src.main.bootstrap``.

``bootstrap`` is the non-Qt half of the startup sequence and is split out so
we can test it without spinning up a real ``QApplication``. It is responsible
for, in order:

  1. Configuring rotating-file logging.
  2. Migrating any legacy ``neloaica.db`` sitting next to the executable.
  3. Initialising the DB schema.
  4. Triggering startup + daily backups.

These tests heavily monkeypatch the dependencies so we can verify the call
ordering and side effects in isolation.
"""

import logging
from pathlib import Path

import pytest

from src import main as main_mod


@pytest.fixture
def fake_setup(monkeypatch, tmp_path):
    """Replace every external collaborator of ``bootstrap`` with a spy.

    The fixture yields a dict with the spies and the recording surfaces so
    each test can assert on whichever facet it cares about.
    """
    log_file = tmp_path / "logs" / "neloaica.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    calls = []

    def fake_setup_logging():
        calls.append("setup_logging")
        return log_file

    def fake_get_app_dir():
        return tmp_path / "app"

    def fake_get_database_path():
        return tmp_path / "user_data" / "neloaica.db"

    def fake_migrate(legacy: Path, new: Path) -> bool:
        calls.append(("migrate", str(legacy), str(new)))
        # Default: pretend nothing was migrated. Tests that need a positive
        # result override this directly.
        return False

    def fake_init_db():
        calls.append("init_database")

    def fake_create_backup(kind: str):
        calls.append(("create_backup", kind))
        return ("ignored", True)

    def fake_should_daily():
        calls.append("should_create_daily_backup")
        return True

    monkeypatch.setattr(main_mod, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(main_mod, "get_app_dir", fake_get_app_dir)
    monkeypatch.setattr(main_mod, "get_database_path", fake_get_database_path)
    monkeypatch.setattr(main_mod, "migrate_legacy_db", fake_migrate)
    monkeypatch.setattr(main_mod, "init_database", fake_init_db)
    monkeypatch.setattr(main_mod, "create_backup", fake_create_backup)
    monkeypatch.setattr(main_mod, "should_create_daily_backup", fake_should_daily)

    return {
        "calls": calls,
        "log_file": log_file,
        "app_dir": tmp_path / "app",
        "db_path": tmp_path / "user_data" / "neloaica.db",
    }


# ===========================================================================
# TestBootstrapOrder
# ===========================================================================


class TestBootstrapOrder:
    def test_logging_runs_first(self, fake_setup):
        main_mod.bootstrap()
        assert fake_setup["calls"][0] == "setup_logging"

    def test_db_migration_before_init(self, fake_setup):
        main_mod.bootstrap()
        names = [c if isinstance(c, str) else c[0] for c in fake_setup["calls"]]
        # migrate must happen strictly before init_database
        assert names.index("migrate") < names.index("init_database")

    def test_init_database_before_backups(self, fake_setup):
        main_mod.bootstrap()
        names = [c if isinstance(c, str) else c[0] for c in fake_setup["calls"]]
        assert names.index("init_database") < names.index("create_backup")

    def test_full_call_sequence(self, fake_setup):
        main_mod.bootstrap()
        names = [c if isinstance(c, str) else c[0] for c in fake_setup["calls"]]
        # We don't assert exact equality (logging order, etc. may vary) but the
        # canonical flow must be present in this order.
        for marker in (
            "setup_logging",
            "migrate",
            "init_database",
            "should_create_daily_backup",
        ):
            assert marker in names
        assert names.index("setup_logging") < names.index("migrate")
        assert names.index("migrate") < names.index("init_database")
        assert names.index("init_database") < names.index("should_create_daily_backup")


# ===========================================================================
# TestLegacyDbMigration
# ===========================================================================


class TestLegacyDbMigration:
    def test_migrate_called_with_correct_paths(self, fake_setup):
        main_mod.bootstrap()
        migrate_calls = [
            c for c in fake_setup["calls"] if isinstance(c, tuple) and c[0] == "migrate"
        ]
        assert len(migrate_calls) == 1
        _, legacy, new = migrate_calls[0]
        assert legacy == str(fake_setup["app_dir"] / "neloaica.db")
        assert new == str(fake_setup["db_path"])

    def test_skips_when_legacy_equals_new(self, monkeypatch, fake_setup):
        # In dev mode the legacy and new locations are identical (project root).
        # bootstrap() must skip the migration call entirely in that case so we
        # don't try to move a file onto itself.
        same = fake_setup["app_dir"] / "neloaica.db"
        monkeypatch.setattr(main_mod, "get_database_path", lambda: same)

        # Reset spy
        fake_setup["calls"].clear()
        main_mod.bootstrap()

        migrate_calls = [
            c for c in fake_setup["calls"] if isinstance(c, tuple) and c[0] == "migrate"
        ]
        assert migrate_calls == []

    def test_logs_when_migration_succeeds(self, fake_setup, monkeypatch, caplog):
        monkeypatch.setattr(main_mod, "migrate_legacy_db", lambda legacy, new: True)
        with caplog.at_level(logging.INFO, logger="src.main"):
            main_mod.bootstrap()
        assert any("Migrated legacy DB" in r.message for r in caplog.records)


# ===========================================================================
# TestBackups
# ===========================================================================


class TestBackups:
    def test_startup_backup_always_created(self, fake_setup):
        main_mod.bootstrap()
        startup = [
            c
            for c in fake_setup["calls"]
            if isinstance(c, tuple) and c == ("create_backup", "startup")
        ]
        assert len(startup) == 1

    def test_daily_backup_when_should(self, fake_setup):
        main_mod.bootstrap()
        auto = [
            c
            for c in fake_setup["calls"]
            if isinstance(c, tuple) and c == ("create_backup", "auto")
        ]
        assert len(auto) == 1

    def test_daily_backup_skipped_when_already_exists(self, monkeypatch, fake_setup):
        monkeypatch.setattr(main_mod, "should_create_daily_backup", lambda: False)
        main_mod.bootstrap()
        auto = [
            c
            for c in fake_setup["calls"]
            if isinstance(c, tuple) and c == ("create_backup", "auto")
        ]
        assert auto == []


# ===========================================================================
# TestNoPrint
# ===========================================================================


class TestNoPrint:
    """Bootstrap must use ``logging`` rather than ``print``."""

    def test_no_print_calls_in_main_source(self):
        import inspect

        source = inspect.getsource(main_mod)
        assert "print(" not in source

    def test_logging_emits_startup_message(self, fake_setup, caplog):
        with caplog.at_level(logging.INFO, logger="src.main"):
            main_mod.bootstrap()
        assert any("starting up" in r.message for r in caplog.records)
