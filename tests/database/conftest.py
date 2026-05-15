"""Shared fixtures for database model tests.

Each test gets a fresh, isolated in-memory SQLite database so tests
never interfere with each other and never touch the real neloaica.db.
"""

import sqlite3
import pytest

from src.database.connection import DatabaseConnection


def _make_in_memory_db() -> DatabaseConnection:
    """Create a fresh DatabaseConnection backed by an in-memory SQLite DB."""
    # Fully reset the singleton so the next call recreates it
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    # Bypass __init__ so we can inject the connection directly
    instance = object.__new__(DatabaseConnection)
    instance._connection = conn
    DatabaseConnection._instance = instance
    return instance


def _teardown_db(instance: DatabaseConnection):
    """Close and fully remove the singleton."""
    try:
        instance._connection.close()
    except Exception:
        pass
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None


@pytest.fixture
def db():
    """Fresh in-memory DB for each test — tables are NOT created here.
    Callers must call the relevant create_*_table() themselves."""
    instance = _make_in_memory_db()
    yield instance
    _teardown_db(instance)
