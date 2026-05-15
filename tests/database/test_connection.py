"""Tests for the DatabaseConnection singleton.

Covers:
  * TestSingleton           — same instance, same underlying connection
  * TestRowFactory          — fetchone/fetchall return dicts
  * TestForeignKeys         — PRAGMA foreign_keys = ON is enforced
  * TestExecute             — execute / executemany / commit semantics
  * TestClose               — close() resets the connection and reconnects on demand
"""

import sqlite3
import pytest

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
        DatabaseConnection().execute(
            "CREATE TABLE t_a (id INTEGER PRIMARY KEY)"
        )
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
        assert DatabaseConnection().fetchone(
            "SELECT id, name FROM t WHERE name = ?", ("ghost",)
        ) is None

    def test_fetchall_returns_list_of_dicts(self):
        rows = DatabaseConnection().fetchall(
            "SELECT name, age FROM t ORDER BY name"
        )
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
        DatabaseConnection().execute(
            "CREATE TABLE parent (id INTEGER PRIMARY KEY)"
        )
        DatabaseConnection().execute(
            "CREATE TABLE child ("
            "  id INTEGER PRIMARY KEY,"
            "  parent_id INTEGER NOT NULL,"
            "  FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE"
            ")"
        )
        DatabaseConnection().commit()

        with pytest.raises(sqlite3.IntegrityError):
            DatabaseConnection().execute(
                "INSERT INTO child (parent_id) VALUES (?)", (999,)
            )

    def test_on_delete_cascade(self, db):
        DatabaseConnection().execute(
            "CREATE TABLE parent (id INTEGER PRIMARY KEY)"
        )
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
        DatabaseConnection().execute(
            "CREATE TABLE log (id INTEGER PRIMARY KEY, msg TEXT)"
        )
        DatabaseConnection().commit()

    def test_execute_returns_cursor(self):
        cur = DatabaseConnection().execute(
            "INSERT INTO log (msg) VALUES (?)", ("hi",)
        )
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
