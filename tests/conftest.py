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
from PySide6.QtWidgets import QApplication, QMessageBox


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
