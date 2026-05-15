"""Database connection manager."""

import sqlite3
from pathlib import Path
from typing import Optional


class DatabaseConnection:
    """SQLite database connection manager using singleton pattern."""

    _instance: Optional["DatabaseConnection"] = None
    _connection: Optional[sqlite3.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self._db_path = self._get_db_path()
            self._connect()

    def _get_db_path(self) -> Path:
        """Resolve the database file path.

        The DB lives under :func:`src.paths.get_user_data_dir` so frozen
        installs can place the executable in a read-only location while
        runtime data goes into ``%LOCALAPPDATA%\\Neloaica`` (or the
        platform equivalent).
        """
        from src.paths import get_database_path

        return get_database_path()

    def _connect(self):
        """Establish database connection."""
        # Make sure the parent directory exists. On a fresh install the
        # user data dir does not yet exist, and ``sqlite3.connect`` will
        # fail with ``unable to open database file`` if any component of
        # the path is missing. The :memory: path used in tests has no
        # parents so guard against that.
        if str(self._db_path) != ":memory:":
            parent = self._db_path.parent
            if str(parent) and parent != Path("."):
                parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.row_factory = sqlite3.Row

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the database connection."""
        if self._connection is None:
            self._connect()
        return self._connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return the cursor."""
        return self.connection.execute(query, params)

    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets."""
        return self.connection.executemany(query, params_list)

    def commit(self):
        """Commit the current transaction."""
        self.connection.commit()

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a query and fetch all results as dictionaries."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Execute a query and fetch one result as dictionary."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
