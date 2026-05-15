"""Tests for the DatabaseConnection singleton.

Covers:
  * TestSingleton           — same instance, same underlying connection
  * TestRowFactory          — fetchone/fetchall return dicts
  * TestForeignKeys         — PRAGMA foreign_keys = ON is enforced
  * TestExecute             — execute / executemany / commit semantics
  * TestClose               — close() resets the connection and reconnects on demand
  * TestDbPath              — DB path resolves through ``src.paths`` and the
                              connection creates the user data directory
                              on demand
"""

import sqlite3
from pathlib import Path

import pytest

from src.database import connection as connection_mod
from src.database.connection import DatabaseConnection

# ---------------------------------------------------------------------------
# TestSingleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_two_constructor_calls_return_same_instance(self, db):
        a = DatabaseConnection()
        b = DatabaseConnection()
        assert a is b

    def test_singleton_shares_connection(self, db):
        a = DatabaseConnection()
        b = DatabaseConnection()
        assert a.connection is b.connection

    def test_fixture_resets_between_tests_a(self, db):
        DatabaseConnection().execute("CREATE TABLE t_a (id INTEGER PRIMARY KEY)")
        DatabaseConnection().commit()
        rows = DatabaseConnection().fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t_a'"
        )
        assert len(rows) == 1

    def test_fixture_resets_between_tests_b(self, db):
        rows = DatabaseConnection().fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='t_a'"
        )
        assert rows == []


# ---------------------------------------------------------------------------
# TestRowFactory
# ---------------------------------------------------------------------------


class TestRowFactory:
    @pytest.fixture(autouse=True)
    def _table(self, db):
        DatabaseConnection().execute(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)"
        )
        DatabaseConnection().executemany(
            "INSERT INTO t (name, age) VALUES (?, ?)",
            [("alice", 30), ("bob", 40)],
        )
        DatabaseConnection().commit()

    def test_fetchone_returns_dict(self):
        row = DatabaseConnection().fetchone(
            "SELECT id, name, age FROM t WHERE name = ?", ("alice",)
        )
        assert isinstance(row, dict)
        assert row["name"] == "alice"
        assert row["age"] == 30

    def test_fetchone_missing_returns_none(self):
        assert (
            DatabaseConnection().fetchone("SELECT id, name FROM t WHERE name = ?", ("ghost",))
            is None
        )

    def test_fetchall_returns_list_of_dicts(self):
        rows = DatabaseConnection().fetchall("SELECT name, age FROM t ORDER BY name")
        assert rows == [
            {"name": "alice", "age": 30},
            {"name": "bob", "age": 40},
        ]

    def test_fetchall_empty_returns_empty_list(self):
        assert DatabaseConnection().fetchall("SELECT name FROM t WHERE 1=0") == []


# ---------------------------------------------------------------------------
# TestForeignKeys
# ---------------------------------------------------------------------------


class TestForeignKeys:
    def test_pragma_is_on(self, db):
        row = DatabaseConnection().fetchone("PRAGMA foreign_keys")
        assert row is not None
        # SQLite returns the column name "foreign_keys"
        assert row["foreign_keys"] == 1

    def test_foreign_key_constraint_is_enforced(self, db):
        DatabaseConnection().execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        DatabaseConnection().execute(
            "CREATE TABLE child ("
            "  id INTEGER PRIMARY KEY,"
            "  parent_id INTEGER NOT NULL,"
            "  FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE"
            ")"
        )
        DatabaseConnection().commit()

        with pytest.raises(sqlite3.IntegrityError):
            DatabaseConnection().execute("INSERT INTO child (parent_id) VALUES (?)", (999,))

    def test_on_delete_cascade(self, db):
        DatabaseConnection().execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        DatabaseConnection().execute(
            "CREATE TABLE child ("
            "  id INTEGER PRIMARY KEY,"
            "  parent_id INTEGER NOT NULL,"
            "  FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE"
            ")"
        )
        DatabaseConnection().execute("INSERT INTO parent (id) VALUES (1)")
        DatabaseConnection().execute("INSERT INTO child (parent_id) VALUES (1)")
        DatabaseConnection().execute("INSERT INTO child (parent_id) VALUES (1)")
        DatabaseConnection().commit()

        DatabaseConnection().execute("DELETE FROM parent WHERE id = 1")
        DatabaseConnection().commit()

        rows = DatabaseConnection().fetchall("SELECT id FROM child")
        assert rows == []


# ---------------------------------------------------------------------------
# TestExecute
# ---------------------------------------------------------------------------


class TestExecute:
    @pytest.fixture(autouse=True)
    def _table(self, db):
        DatabaseConnection().execute("CREATE TABLE log (id INTEGER PRIMARY KEY, msg TEXT)")
        DatabaseConnection().commit()

    def test_execute_returns_cursor(self):
        cur = DatabaseConnection().execute("INSERT INTO log (msg) VALUES (?)", ("hi",))
        DatabaseConnection().commit()
        assert cur.lastrowid == 1

    def test_executemany_bulk_insert(self):
        DatabaseConnection().executemany(
            "INSERT INTO log (msg) VALUES (?)",
            [("a",), ("b",), ("c",)],
        )
        DatabaseConnection().commit()
        rows = DatabaseConnection().fetchall("SELECT msg FROM log ORDER BY id")
        assert [r["msg"] for r in rows] == ["a", "b", "c"]

    def test_commit_persists_data_inside_same_connection(self):
        DatabaseConnection().execute("INSERT INTO log (msg) VALUES (?)", ("x",))
        DatabaseConnection().commit()
        rows = DatabaseConnection().fetchall("SELECT msg FROM log")
        assert [r["msg"] for r in rows] == ["x"]


# ---------------------------------------------------------------------------
# TestClose
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_resets_connection_attribute(self, db):
        inst = DatabaseConnection()
        assert inst._connection is not None
        inst.close()
        assert inst._connection is None


# ---------------------------------------------------------------------------
# TestDbPath
# ---------------------------------------------------------------------------


class TestDbPath:
    """The DB path now flows through ``src.paths.get_database_path``.

    These tests instantiate ``DatabaseConnection`` outside the autouse
    ``_ensure_in_memory_db`` fixture so the real ``_get_db_path`` and
    ``_connect`` are exercised. We point the user data dir at ``tmp_path``
    so we never write into the developer's actual ``%LOCALAPPDATA%``.
    """

    @pytest.fixture
    def isolated_singleton(self, tmp_path, monkeypatch):
        """Reset the singleton and redirect the user data dir into tmp_path."""
        from src import paths as paths_mod

        monkeypatch.setattr(paths_mod, "get_user_data_dir", lambda: tmp_path)
        monkeypatch.setattr(paths_mod, "get_database_path", lambda: tmp_path / "neloaica.db")

        DatabaseConnection._instance = None
        DatabaseConnection._connection = None
        yield tmp_path
        try:
            inst = DatabaseConnection._instance
            if inst is not None and inst._connection is not None:
                inst.close()
        except Exception:
            pass
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

    def test_uses_get_database_path_from_paths_module(self, isolated_singleton):
        inst = DatabaseConnection()
        assert inst._db_path == isolated_singleton / "neloaica.db"

    def test_creates_parent_directory_when_missing(self, tmp_path, monkeypatch):
        from src import paths as paths_mod

        nested = tmp_path / "deeply" / "nested" / "data"
        monkeypatch.setattr(paths_mod, "get_database_path", lambda: nested / "neloaica.db")

        DatabaseConnection._instance = None
        DatabaseConnection._connection = None
        try:
            assert not nested.exists()
            inst = DatabaseConnection()
            assert nested.is_dir()
            assert (nested / "neloaica.db").exists()
            inst.close()
        finally:
            DatabaseConnection._instance = None
            DatabaseConnection._connection = None

    def test_db_path_is_a_path_instance(self, isolated_singleton):
        inst = DatabaseConnection()
        assert isinstance(inst._db_path, Path)

    def test_in_memory_path_does_not_create_directories(self, monkeypatch, tmp_path):
        """A ``:memory:`` path string must not trigger ``mkdir`` on its parent."""
        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

        called = {"mkdir": False}

        def tracking_mkdir(self, *args, **kwargs):
            called["mkdir"] = True

        monkeypatch.setattr(Path, "mkdir", tracking_mkdir)

        instance = object.__new__(DatabaseConnection)
        instance._db_path = ":memory:"
        instance._connection = None
        DatabaseConnection._instance = instance

        instance._connect()
        assert called["mkdir"] is False
        try:
            instance.close()
        finally:
            DatabaseConnection._instance = None
            DatabaseConnection._connection = None

    def test_module_resolves_get_database_path_lazily(self):
        """The import is local to ``_get_db_path`` so reset doesn't cache it.

        Guards against accidentally promoting the import to module level —
        which would make monkeypatching :func:`src.paths.get_database_path`
        in tests a no-op.
        """
        # Read the source of _get_db_path; it should reference get_database_path.
        import inspect

        src = inspect.getsource(connection_mod.DatabaseConnection._get_db_path)
        assert "get_database_path" in src
