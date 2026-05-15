"""Tests for `BillablePartsSectionWidget` (parts used, with units & price).

Covers:
  * Initial empty state
  * Adding a part with default units/price
  * Updating units / price via the per-row inputs
  * Subtotal = units * price; total = sum of subtotals
  * Comma → dot conversion in units
  * Remove a part
  * parts_changed signal carries (parts_list, total)
  * set_data round-trip
  * format_price / parse_price helpers
"""

from unittest.mock import patch

import pytest

_PARTS = [
    {"id": 1, "part_name": "Air Filter"},
    {"id": 2, "part_name": "Brake Disc"},
]


@pytest.fixture
def widget(qapp):
    with patch(
        "src.pages.receipts.billable_parts_section.get_all_parts", return_value=list(_PARTS)
    ):
        from src.pages.receipts.billable_parts_section import BillablePartsSectionWidget

        return BillablePartsSectionWidget()


# ===========================================================================
# TestInitialState
# ===========================================================================


class TestInitialState:
    def test_empty(self, widget):
        assert widget.get_selected_parts() == []
        assert widget.get_total_parts_cost() == 0.0

    def test_combo_populated(self, widget):
        # sentinel + 2 parts
        assert widget.part_combo.count() == 3


# ===========================================================================
# TestAddRemove
# ===========================================================================


class TestAddRemove:
    def test_select_combo_adds_part_with_zero_subtotal(self, widget):
        widget.part_combo.setCurrentIndex(1)
        parts = widget.get_selected_parts()
        assert len(parts) == 1
        assert parts[0]["part_id"] == 1
        assert parts[0]["units"] == 0.0
        assert parts[0]["price_per_unit"] == 0.0

    def test_remove_part(self, widget):
        widget.part_combo.setCurrentIndex(1)
        widget.remove_part(1)
        assert widget.get_selected_parts() == []

    def test_remove_unknown_is_silent(self, widget):
        widget.remove_part(99999)
        assert widget.get_selected_parts() == []


# ===========================================================================
# TestPriceFormatting
# ===========================================================================


class TestPriceFormatting:
    def test_format_price(self, widget):
        assert widget.format_price(1500) == "1 500.00"
        assert widget.format_price(0.5) == "0.50"
        assert widget.format_price(1234567.89) == "1 234 567.89"
        assert widget.format_price(0) == "0.00"

    def test_format_price_invalid(self, widget):
        assert widget.format_price("abc") == "0.00"

    def test_parse_price(self, widget):
        assert widget.parse_price("1 234.50") == 1234.5
        assert widget.parse_price("100") == 100.0
        assert widget.parse_price("") == 0.0
        assert widget.parse_price("abc") == 0.0


# ===========================================================================
# TestUnitsAndSubtotal
# ===========================================================================


class TestUnitsAndSubtotal:
    def _add_part(self, widget):
        widget.part_combo.setCurrentIndex(1)

    def test_units_text_change_updates_state(self, widget):
        from PySide6.QtWidgets import QLineEdit

        self._add_part(widget)
        line = QLineEdit()
        widget.on_units_text_changed(1, "5", line)
        assert widget.selected_parts[0]["units"] == 5.0

    def test_units_comma_treated_as_decimal(self, widget):
        from PySide6.QtWidgets import QLineEdit

        self._add_part(widget)
        line = QLineEdit()
        widget.on_units_text_changed(1, "2,5", line)
        assert widget.selected_parts[0]["units"] == pytest.approx(2.5)

    def test_units_non_digit_stripped(self, widget):
        from PySide6.QtWidgets import QLineEdit

        self._add_part(widget)
        line = QLineEdit()
        widget.on_units_text_changed(1, "ab12", line)
        assert widget.selected_parts[0]["units"] == 12.0

    def test_price_text_change_updates_state(self, widget):
        from PySide6.QtWidgets import QLineEdit

        self._add_part(widget)
        price_input = QLineEdit()
        widget.on_price_text_changed(1, "100.50", price_input)
        assert widget.selected_parts[0]["price_per_unit"] == pytest.approx(100.5)

    def test_total_is_sum_of_subtotals(self, widget):
        from PySide6.QtWidgets import QLineEdit

        widget.part_combo.setCurrentIndex(1)  # part id 1
        widget.part_combo.setCurrentIndex(1)  # now adds id 2
        line = QLineEdit()
        widget.on_units_text_changed(1, "2", line)
        widget.on_price_text_changed(1, "100", line)
        widget.on_units_text_changed(2, "3", line)
        widget.on_price_text_changed(2, "50", line)
        # 2 * 100 + 3 * 50 = 350
        assert widget.get_total_parts_cost() == pytest.approx(350.0)


# ===========================================================================
# TestSignal
# ===========================================================================


class TestSignal:
    def test_signal_payload(self, widget):
        captured = []
        widget.parts_changed.connect(lambda parts, total: captured.append((parts, total)))
        widget.part_combo.setCurrentIndex(1)
        parts, total = captured[-1]
        assert len(parts) == 1
        assert total == 0.0


# ===========================================================================
# TestSetData
# ===========================================================================


class TestSetData:
    def test_round_trip(self, widget):
        with patch(
            "src.pages.receipts.billable_parts_section.get_all_parts", return_value=list(_PARTS)
        ):
            widget.set_data(
                [
                    {"part_id": 1, "units": 2, "price_per_unit": 100.0},
                    {"part_id": 2, "units": 1, "price_per_unit": 200.0},
                ]
            )
        parts = widget.get_selected_parts()
        ids = sorted(p["part_id"] for p in parts)
        assert ids == [1, 2]
        assert widget.get_total_parts_cost() == pytest.approx(400.0)

    def test_set_data_ignores_unknown_part(self, widget):
        with patch(
            "src.pages.receipts.billable_parts_section.get_all_parts", return_value=list(_PARTS)
        ):
            widget.set_data([{"part_id": 9999, "units": 1, "price_per_unit": 10.0}])
        assert widget.get_selected_parts() == []
