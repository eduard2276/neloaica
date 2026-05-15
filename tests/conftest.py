"""Top-level pytest configuration and shared fixtures.

All test categories live underneath this folder:

  * `tests/unit`        — pure logic, no DB / no Qt
  * `tests/database`    — model-layer tests with an in-memory SQLite DB
  * `tests/services`    — service-layer tests (Excel template engine, backup)
  * `tests/ui`          — PySide6 widget and page tests (DB is mocked)

A session-scoped `QApplication` is exposed via the `qapp` fixture for any UI
test that needs it.  Database tests rely on the `db` fixture in
`tests/database/conftest.py` which resets the `DatabaseConnection` singleton
between tests.
"""

import sqlite3

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from src.database.connection import DatabaseConnection


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication shared by every UI test in the session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _silence_qmessageboxes(monkeypatch):
    """Stop any test from showing a real ``QMessageBox``.

    Some PySide6 builds (notably 6.10.3+ on the GitHub Actions Windows runner
    with ``QT_QPA_PLATFORM=offscreen``) segfault inside ``QMessageBox.exec``
    when no real desktop is attached. Tests should already mock the
    ``show_warning`` / ``show_info`` / ``show_critical`` helpers when they
    expect a dialog, but a forgotten mock — for example a code path that
    falls into a ``show_critical`` branch unexpectedly — can crash the whole
    pytest worker. Replace ``exec`` with a no-op so an unmocked dialog
    silently returns ``0`` instead of taking down the process.
    """
    monkeypatch.setattr(QMessageBox, "exec", lambda self, *a, **kw: 0)


@pytest.fixture(autouse=True)
def _ensure_in_memory_db():
    """Provide an isolated in-memory SQLite DB with the full schema per test.

    UI and service tests routinely instantiate ``MainWindow`` or
    ``ReceiptFormPage`` which eagerly query the real ``DatabaseConnection``
    singleton at construction time. On a CI runner there is no
    ``neloaica.db`` on disk so SQLite happily creates an empty file and the
    first ``SELECT`` raises ``OperationalError: no such table: clients``.

    This fixture replaces the singleton with a fresh in-memory connection
    and runs ``init_database()`` so every table exists. Tests that explicitly
    request the ``db`` fixture in ``tests/database/conftest.py`` simply
    overwrite the singleton again with a brand-new empty in-memory DB and
    create only the tables they need — both fixtures are idempotent so the
    interleaving is safe.
    """
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    instance = object.__new__(DatabaseConnection)
    instance._connection = conn
    instance._db_path = ":memory:"
    DatabaseConnection._instance = instance

    from src.database import init_database

    init_database()

    yield

    try:
        conn.close()
    except Exception:
        pass
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
