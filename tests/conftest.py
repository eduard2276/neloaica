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

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication shared by every UI test in the session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
