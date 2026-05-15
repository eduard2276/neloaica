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
        """Get the database file path (same folder as the application)."""
        from src.paths import get_app_dir

        return get_app_dir() / "neloaica.db"

    def _connect(self):
        """Establish database connection."""
        self._connection = sqlite3.connect(str(self._db_path), check_same_thread=False)
        # Enable foreign keys
        self._connection.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
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
