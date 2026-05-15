"""Tests for `EstimatesSectionWidget` in `src/pages/receipts/estimates_section.py`.

Covers:
  * Default state (current date, zero cost)
  * Cost input formatting (thousand separators, max 2 decimals)
  * get_estimate_cost parses formatted text
  * estimates_changed signal carries (cost, date)
  * set_data round-trip
"""

import pytest

from PySide6.QtCore import QDate


@pytest.fixture
def widget(qapp):
    from src.pages.receipts.estimates_section import EstimatesSectionWidget
    return EstimatesSectionWidget()


# ===========================================================================
# TestDefaults
# ===========================================================================

class TestDefaults:
    def test_initial_cost_is_zero(self, widget):
        assert widget.get_estimate_cost() == 0.0

    def test_initial_date_is_today(self, widget):
        assert widget.get_estimated_final_date() == QDate.currentDate().toString("dd.MM.yyyy")


# ===========================================================================
# TestCostFormatting
# ===========================================================================

class TestCostFormatting:
    def test_thousand_separator(self, widget):
        widget.estimate_cost_input.setText("1234567")
        assert widget.estimate_cost_input.text() == "1 234 567"

    def test_decimal_allowed(self, widget):
        widget.estimate_cost_input.setText("1234.56")
        assert widget.estimate_cost_input.text() == "1 234.56"

    def test_decimal_truncated_to_2(self, widget):
        widget.estimate_cost_input.setText("1.987")
        assert widget.estimate_cost_input.text() == "1.98"

    def test_non_digits_stripped(self, widget):
        widget.estimate_cost_input.setText("ab12cd")
        assert widget.estimate_cost_input.text() == "12"

    def test_empty_input(self, widget):
        widget.estimate_cost_input.setText("")
        assert widget.estimate_cost_input.text() == ""


# ===========================================================================
# TestGetEstimateCost
# ===========================================================================

class TestGetEstimateCost:
    def test_blank_returns_zero(self, widget):
        widget.estimate_cost_input.setText("")
        assert widget.get_estimate_cost() == 0.0

    def test_formatted_value_parses_correctly(self, widget):
        widget.estimate_cost_input.setText("1 234.50")
        assert widget.get_estimate_cost() == pytest.approx(1234.5)

    def test_unparseable_value_returns_zero(self, widget):
        # Bypass the formatter by writing directly to the underlying QLineEdit
        widget._cost_updating = True
        widget.estimate_cost_input.setText("abc")
        widget._cost_updating = False
        assert widget.get_estimate_cost() == 0.0


# ===========================================================================
# TestSignal
# ===========================================================================

class TestSignal:
    def test_signal_carries_cost_and_date(self, widget):
        captured = []
        widget.estimates_changed.connect(lambda c, d: captured.append((c, d)))
        widget.estimate_cost_input.setText("100")
        assert captured
        cost, date = captured[-1]
        assert cost == 100.0
        assert isinstance(date, str)
        assert len(date) == 10  # dd.MM.yyyy

    def test_emit_estimates_changed_idempotent(self, widget):
        captured = []
        widget.estimates_changed.connect(lambda c, d: captured.append((c, d)))
        widget.emit_estimates_changed()
        widget.emit_estimates_changed()
        assert len(captured) == 2


# ===========================================================================
# TestSetData
# ===========================================================================

class TestSetData:
    def test_round_trip(self, widget):
        widget.set_data(1234.5, "15.06.2026")
        assert widget.get_estimate_cost() == pytest.approx(1234.5)
        assert widget.get_estimated_final_date() == "15.06.2026"

    def test_invalid_date_keeps_default(self, widget):
        widget.set_data(50.0, "not a date")
        # Date should stay valid (today or unchanged)
        assert len(widget.get_estimated_final_date()) == 10

    def test_zero_cost_leaves_input_unchanged(self, widget):
        widget.estimate_cost_input.setText("")
        widget.set_data(0.0, "")
        assert widget.estimate_cost_input.text() == ""
