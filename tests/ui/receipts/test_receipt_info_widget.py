"""Tests for `ReceiptInfoWidget` in `src/pages/receipts/receipt_info.py`.

The widget glues clients, cars and employees into the receipt header. We
exercise:
  * client/car cascade — selecting a client filters cars
  * car selection populates plate/VIN/model/kilometers
  * data_changed signal fires on each user-driven change
  * kilometers formatter / parser round-trip
  * get_data() and set_data() round-trip
"""

from unittest.mock import patch

import pytest

_CLIENTS = [
    {"id": 1, "first_name": "Alice", "last_name": "Apple", "address": "1 Main"},
    {"id": 2, "first_name": "Bob", "last_name": "Banana", "address": "2 Elm"},
]

_CARS = [
    {
        "id": 11,
        "client_id": 1,
        "plate_number": "B-1",
        "vin": "A" * 17,
        "model": "Audi",
        "kilometers": 1000,
    },
    {
        "id": 12,
        "client_id": 1,
        "plate_number": "B-2",
        "vin": "B" * 17,
        "model": "BMW",
        "kilometers": 2000,
    },
    {
        "id": 21,
        "client_id": 2,
        "plate_number": "C-1",
        "vin": "C" * 17,
        "model": "Volvo",
        "kilometers": 3000,
    },
]

_EMPLOYEES = [
    {"id": 100, "first_name": "Mecanic", "last_name": "One"},
    {"id": 200, "first_name": "Mecanic", "last_name": "Two"},
]


@pytest.fixture
def widget(qapp):
    with (
        patch("src.pages.receipts.receipt_info.get_all_clients", return_value=list(_CLIENTS)),
        patch("src.pages.receipts.receipt_info.get_all_cars", return_value=list(_CARS)),
        patch("src.pages.receipts.receipt_info.get_all_employees", return_value=list(_EMPLOYEES)),
    ):
        from src.pages.receipts.receipt_info import ReceiptInfoWidget

        return ReceiptInfoWidget()


# ===========================================================================
# Initial state
# ===========================================================================


class TestInitialState:
    def test_clients_loaded(self, widget):
        # sentinel + 2 real clients
        assert widget.client_combo.count() == 3

    def test_executants_loaded(self, widget):
        # sentinel + 2 employees
        assert widget.executant_combo.count() == 3

    def test_no_client_selected_initially(self, widget):
        # The combo box starts at index -1 (no selection) or 0 (placeholder)
        # depending on PySide6 internals; what matters is that there's no client_id.
        assert widget.client_combo.currentData() is None

    def test_car_combo_disabled_initially(self, widget):
        assert not widget.car_combo.isEnabled()


# ===========================================================================
# Client → car cascade
# ===========================================================================


class TestCascade:
    def test_selecting_client_enables_car_combo_and_filters(self, widget):
        widget.client_combo.setCurrentIndex(1)  # Alice
        assert widget.car_combo.isEnabled()
        # sentinel + Alice's 2 cars
        assert widget.car_combo.count() == 3

    def test_other_client_filters_to_their_cars(self, widget):
        widget.client_combo.setCurrentIndex(2)  # Bob
        # sentinel + Bob's 1 car
        assert widget.car_combo.count() == 2

    def test_selecting_car_fills_details(self, widget):
        widget.client_combo.setCurrentIndex(1)  # Alice
        widget.car_combo.setCurrentIndex(1)  # 1st of Alice's cars
        assert widget.plate_input.text() != ""
        assert widget.vin_input.text() != ""
        assert widget.model_input.text() != ""
        assert widget.km_input.text() != ""

    def test_unselecting_client_clears_car(self, widget):
        widget.client_combo.setCurrentIndex(1)
        widget.car_combo.setCurrentIndex(1)
        widget.client_combo.setCurrentIndex(0)
        assert widget.plate_input.text() == ""
        assert widget.vin_input.text() == ""
        assert widget.model_input.text() == ""
        assert not widget.car_combo.isEnabled()


# ===========================================================================
# Kilometers formatting
# ===========================================================================


class TestKilometers:
    def test_format(self, widget):
        assert widget.format_kilometers(1) == "1"
        assert widget.format_kilometers(1000) == "1 000"
        assert widget.format_kilometers(1234567) == "1 234 567"

    def test_format_invalid(self, widget):
        assert widget.format_kilometers("abc") == "abc"
        assert widget.format_kilometers("") == ""

    def test_parse(self, widget):
        assert widget.parse_kilometers("1 000") == "1000"
        assert widget.parse_kilometers("12,345 km") == "12345"
        assert widget.parse_kilometers("") == ""

    def test_input_reformats(self, widget):
        widget.km_input.setText("123456")
        assert widget.km_input.text() == "123 456"


# ===========================================================================
# data_changed signal
# ===========================================================================


class TestSignal:
    def test_data_changed_payload_contains_keys(self, widget):
        captured = []
        widget.data_changed.connect(lambda d: captured.append(d))
        widget.client_combo.setCurrentIndex(1)
        assert captured
        last = captured[-1]
        for key in [
            "client_id",
            "client_name",
            "client_address",
            "car_id",
            "plate_number",
            "vin",
            "model",
            "kilometers",
            "executant_name",
            "date",
        ]:
            assert key in last

    def test_data_changed_includes_executant_name(self, widget):
        captured = []
        widget.data_changed.connect(lambda d: captured.append(d))
        widget.executant_combo.setCurrentIndex(1)
        assert captured[-1]["executant_name"] == "Mecanic One"


# ===========================================================================
# get_data / set_data
# ===========================================================================


class TestGetSetData:
    def test_get_data_empty(self, widget):
        data = widget.get_data()
        assert data["client_id"] is None
        assert data["client_name"] == ""
        assert data["car_id"] is None

    def test_get_data_after_selection(self, widget):
        widget.client_combo.setCurrentIndex(1)
        widget.car_combo.setCurrentIndex(1)
        widget.executant_combo.setCurrentIndex(2)
        data = widget.get_data()
        assert data["client_id"] == 1
        assert data["client_name"] == "Alice Apple"
        assert data["car_id"] in (11, 12)
        assert data["executant_name"] == "Mecanic Two"

    def test_set_data_round_trip(self, widget):
        with (
            patch("src.pages.receipts.receipt_info.get_all_clients", return_value=list(_CLIENTS)),
            patch("src.pages.receipts.receipt_info.get_all_cars", return_value=list(_CARS)),
            patch(
                "src.pages.receipts.receipt_info.get_all_employees", return_value=list(_EMPLOYEES)
            ),
        ):
            widget.set_data(
                {
                    "client_id": 1,
                    "car_id": 11,
                    "kilometers": "1500",
                    "executant_name": "Mecanic One",
                    "date": "08.05.2026",
                }
            )
        data = widget.get_data()
        assert data["client_id"] == 1
        assert data["car_id"] == 11
        assert data["executant_name"] == "Mecanic One"
        assert data["date"] == "08.05.2026"

    def test_set_data_invalid_date_keeps_default(self, widget):
        with (
            patch("src.pages.receipts.receipt_info.get_all_clients", return_value=list(_CLIENTS)),
            patch("src.pages.receipts.receipt_info.get_all_cars", return_value=list(_CARS)),
            patch(
                "src.pages.receipts.receipt_info.get_all_employees", return_value=list(_EMPLOYEES)
            ),
        ):
            widget.set_data({"client_id": 1, "date": "not-a-date"})
        data = widget.get_data()
        # date stays in dd.MM.yyyy format (current date)
        assert len(data["date"]) == 10
