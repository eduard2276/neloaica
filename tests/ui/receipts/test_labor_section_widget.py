"""Tests for `LaborSectionWidget`.

Covers:
  * Initial state empty
  * Adding labor from the combo
  * Removing labor returns it to the combo
  * Cost text formatting (thousand separators, max 2 decimals)
  * get_total_labor_cost parses formatted text
  * labor_changed signal carries (ids, total)
  * set_data round-trip
"""

from unittest.mock import patch

import pytest

_LABOR = [
    {"id": 1, "service_name": "Oil change"},
    {"id": 2, "service_name": "Brake replacement"},
    {"id": 3, "service_name": "Wheel alignment"},
]


@pytest.fixture
def widget(qapp):
    with patch("src.pages.receipts.labor_section.get_all_labor", return_value=list(_LABOR)):
        from src.pages.receipts.labor_section import LaborSectionWidget

        return LaborSectionWidget()


# ===========================================================================
# TestInitialState
# ===========================================================================


class TestInitialState:
    def test_empty(self, widget):
        assert widget.get_selected_labor() == []
        assert widget.get_total_labor_cost() == 0.0

    def test_combo_populated(self, widget):
        assert widget.labor_combo.count() == 4  # sentinel + 3


# ===========================================================================
# TestAddRemove
# ===========================================================================


class TestAddRemove:
    def test_select_combo_adds(self, widget):
        widget.labor_combo.setCurrentIndex(1)
        assert 1 in widget.get_selected_labor()

    def test_remove(self, widget):
        widget.labor_combo.setCurrentIndex(1)
        widget.remove_labor(1)
        assert 1 not in widget.get_selected_labor()

    def test_remove_unknown_is_silent(self, widget):
        widget.remove_labor(9999)
        assert widget.get_selected_labor() == []


# ===========================================================================
# TestCostFormatting
# ===========================================================================


class TestCostFormatting:
    def test_thousand_separator(self, widget):
        widget.total_cost_input.setText("12345")
        assert widget.total_cost_input.text() == "12 345"

    def test_decimal_kept(self, widget):
        widget.total_cost_input.setText("12.34")
        assert widget.total_cost_input.text() == "12.34"

    def test_decimal_capped(self, widget):
        widget.total_cost_input.setText("12.3456")
        assert widget.total_cost_input.text() == "12.34"

    def test_total_cost_parsing(self, widget):
        widget.total_cost_input.setText("1 234.50")
        assert widget.get_total_labor_cost() == pytest.approx(1234.5)

    def test_blank_total_is_zero(self, widget):
        widget.total_cost_input.setText("")
        assert widget.get_total_labor_cost() == 0.0


# ===========================================================================
# TestSignal
# ===========================================================================


class TestSignal:
    def test_signal_payload(self, widget):
        captured = []
        widget.labor_changed.connect(lambda ids, total: captured.append((list(ids), total)))
        widget.labor_combo.setCurrentIndex(1)
        widget.total_cost_input.setText("500.00")
        ids, total = captured[-1]
        assert ids == [1]
        assert total == pytest.approx(500.0)


# ===========================================================================
# TestSetData
# ===========================================================================


class TestSetData:
    def test_round_trip(self, widget):
        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=list(_LABOR)):
            widget.set_data([1, 3], total_cost=2500.0)
        assert sorted(widget.get_selected_labor()) == [1, 3]
        assert widget.get_total_labor_cost() == pytest.approx(2500.0)

    def test_set_data_zero_cost_leaves_input_blank(self, widget):
        widget.total_cost_input.setText("")
        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=list(_LABOR)):
            widget.set_data([1], total_cost=0.0)
        assert widget.total_cost_input.text() == ""

    def test_format_cost_helper(self, widget):
        assert widget._format_cost(1500.0) == "1 500.00"
        assert widget._format_cost(0.5) == "0.50"
        assert widget._format_cost(1234567.89) == "1 234 567.89"
