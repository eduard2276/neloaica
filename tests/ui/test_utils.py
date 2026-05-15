"""Tests for the styled message-box helpers in `src/utils.py`.

`show_warning`, `show_info`, `show_critical` each:
  * construct a `QMessageBox`,
  * set its icon, title, text,
  * apply the themed stylesheet,
  * call `.exec()` to display it.

To keep the test suite headless we patch QMessageBox.exec so no modal blocks.
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox, QWidget

from src.utils import show_critical, show_info, show_warning


@pytest.fixture
def parent(qapp):
    return QWidget()


def _capture(func, parent):
    """Run `func`, capturing the QMessageBox instance that was shown."""
    captured = {}

    def fake_exec(self_):
        captured["msg"] = self_
        return QMessageBox.StandardButton.Ok

    with patch.object(QMessageBox, "exec", fake_exec):
        func()
    return captured["msg"]


class TestShowWarning:
    def test_icon_title_text(self, parent):
        msg = _capture(lambda: show_warning(parent, "Oops", "Be careful"), parent)
        assert msg.icon() == QMessageBox.Icon.Warning
        assert msg.windowTitle() == "Oops"
        assert msg.text() == "Be careful"

    def test_stylesheet_applied(self, parent):
        msg = _capture(lambda: show_warning(parent, "T", "Body"), parent)
        # Must not be empty, must contain a QMessageBox selector
        ss = msg.styleSheet()
        assert ss
        assert "QMessageBox" in ss

    def test_parent_is_set(self, parent):
        msg = _capture(lambda: show_warning(parent, "T", "B"), parent)
        assert msg.parent() is parent


class TestShowInfo:
    def test_icon_is_information(self, parent):
        msg = _capture(lambda: show_info(parent, "T", "B"), parent)
        assert msg.icon() == QMessageBox.Icon.Information


class TestShowCritical:
    def test_icon_is_critical(self, parent):
        msg = _capture(lambda: show_critical(parent, "T", "B"), parent)
        assert msg.icon() == QMessageBox.Icon.Critical

    def test_parent_none_is_allowed(self, qapp):
        msg = _capture(lambda: show_critical(None, "T", "B"), None)
        # PySide may report parent as either None or a QApplication-owned widget
        assert msg.windowTitle() == "T"
