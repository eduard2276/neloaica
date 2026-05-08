"""Tests for the main application window."""

import pytest
from PySide6.QtWidgets import QApplication

from src.main import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    """Create MainWindow instance for tests."""
    window = MainWindow()
    yield window
    window.close()


def test_main_window_title(main_window):
    """Test that main window has correct title."""
    assert main_window.windowTitle() == "Neloaica"


def test_main_window_minimum_size(main_window):
    """Test that main window has correct minimum size."""
    assert main_window.minimumWidth() == 800
    assert main_window.minimumHeight() == 600
