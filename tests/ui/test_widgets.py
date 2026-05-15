"""Tests for the custom no-scroll widgets in `src/widgets/combo_box.py`.

The widgets exist to prevent accidental value changes when a user is just
scrolling a page that happens to contain a focused combo / spin box. The
widgets must:
  * accept wheel events (no crash),
  * call event.ignore() on them so the parent scroll area handles scrolling,
  * still allow keyboard / programmatic value changes.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent

from src.widgets.combo_box import (
    NoScrollComboBox,
    NoScrollSpinBox,
    NoScrollDoubleSpinBox,
)


def _wheel_event(delta: int = 120) -> QWheelEvent:
    """Build a synthetic vertical wheel event."""
    return QWheelEvent(
        QPointF(0, 0),
        QPointF(0, 0),
        QPoint(0, delta),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


# ===========================================================================
# NoScrollComboBox
# ===========================================================================

class TestNoScrollComboBox:
    def test_wheel_event_is_ignored(self, qapp):
        cb = NoScrollComboBox()
        cb.addItems(["A", "B", "C"])
        cb.setCurrentIndex(1)

        evt = _wheel_event()
        evt.ignore = MagicMock(wraps=evt.ignore)
        cb.wheelEvent(evt)

        evt.ignore.assert_called_once()
        # Index must not change due to wheel
        assert cb.currentIndex() == 1

    def test_programmatic_index_change_still_works(self, qapp):
        cb = NoScrollComboBox()
        cb.addItems(["A", "B", "C"])
        cb.setCurrentIndex(2)
        assert cb.currentText() == "C"

    def test_add_item_data(self, qapp):
        cb = NoScrollComboBox()
        cb.addItem("first", 100)
        cb.addItem("second", 200)
        assert cb.itemData(0) == 100
        assert cb.itemData(1) == 200


# ===========================================================================
# NoScrollSpinBox
# ===========================================================================

class TestNoScrollSpinBox:
    def test_wheel_event_is_ignored(self, qapp):
        sb = NoScrollSpinBox()
        sb.setRange(0, 100)
        sb.setValue(42)

        evt = _wheel_event()
        evt.ignore = MagicMock(wraps=evt.ignore)
        sb.wheelEvent(evt)

        evt.ignore.assert_called_once()
        assert sb.value() == 42

    def test_set_value(self, qapp):
        sb = NoScrollSpinBox()
        sb.setRange(0, 100)
        sb.setValue(7)
        assert sb.value() == 7


# ===========================================================================
# NoScrollDoubleSpinBox
# ===========================================================================

class TestNoScrollDoubleSpinBox:
    def test_wheel_event_is_ignored(self, qapp):
        sb = NoScrollDoubleSpinBox()
        sb.setRange(0.0, 1000.0)
        sb.setValue(3.14)

        evt = _wheel_event(-120)
        evt.ignore = MagicMock(wraps=evt.ignore)
        sb.wheelEvent(evt)

        evt.ignore.assert_called_once()
        assert sb.value() == pytest.approx(3.14)

    def test_decimals(self, qapp):
        sb = NoScrollDoubleSpinBox()
        sb.setDecimals(2)
        sb.setRange(0.0, 100.0)
        sb.setValue(9.99)
        assert sb.value() == pytest.approx(9.99)
