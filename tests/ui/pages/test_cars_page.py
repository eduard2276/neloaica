"""UI tests for CarsPage and CarDialog (`src/pages/cars.py`).

The CarDialog has the richest validation in the whole app: plate format,
VIN length, model required, kilometers required and non-negative. We
verify every branch.

All DB calls are patched.
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialog


_CLIENTS_FOR_DROPDOWN = [
    {"id": 1, "name": "Alice Owner"},
    {"id": 2, "name": "Bob Driver"},
]


@pytest.fixture
def dialog_factory(qapp):
    """Return a callable that builds a fresh CarDialog with mocked client list."""

    def _factory(car=None):
        with patch("src.pages.cars.get_clients_for_dropdown", return_value=_CLIENTS_FOR_DROPDOWN):
            from src.pages.cars import CarDialog
            return CarDialog(parent=None, car=car)

    return _factory


# ===========================================================================
# CarDialog — populate from car dict
# ===========================================================================

class TestCarDialogPopulate:
    def test_add_window_title(self, dialog_factory):
        dlg = dialog_factory()
        assert dlg.windowTitle() == "Add Car"

    def test_edit_window_title(self, dialog_factory):
        car = {
            "client_id": 1, "plate_number": "B-123", "vin": "A" * 17,
            "model": "M1", "kilometers": 50000,
        }
        dlg = dialog_factory(car)
        assert dlg.windowTitle() == "Edit Car"
        assert dlg.plate_input.text() == "B-123"
        assert dlg.vin_input.text() == "A" * 17
        assert dlg.model_input.text() == "M1"
        assert dlg.kilometers_input.text() == "50 000"

    def test_edit_zero_kilometers_field_stays_empty(self, dialog_factory):
        car = {"client_id": 1, "plate_number": "P", "vin": "A" * 17, "model": "M", "kilometers": 0}
        dlg = dialog_factory(car)
        assert dlg.kilometers_input.text() == ""

    def test_client_dropdown_populated(self, dialog_factory):
        dlg = dialog_factory()
        # 1 sentinel + 2 clients
        assert dlg.client_combo.count() == 3
        assert dlg.client_combo.itemData(0) is None
        assert dlg.client_combo.itemData(1) == 1
        assert dlg.client_combo.itemData(2) == 2


# ===========================================================================
# CarDialog — kilometers formatting
# ===========================================================================

class TestCarDialogKilometers:
    def test_format_kilometers(self, dialog_factory):
        dlg = dialog_factory()
        assert dlg.format_kilometers(1) == "1"
        assert dlg.format_kilometers(1000) == "1 000"
        assert dlg.format_kilometers(1234567) == "1 234 567"

    def test_format_kilometers_invalid(self, dialog_factory):
        dlg = dialog_factory()
        assert dlg.format_kilometers("abc") == "abc"
        assert dlg.format_kilometers("") == ""

    def test_parse_kilometers(self, dialog_factory):
        dlg = dialog_factory()
        assert dlg.parse_kilometers("1 000") == 1000
        assert dlg.parse_kilometers("100,000") == 100000
        assert dlg.parse_kilometers("abc") == 0
        assert dlg.parse_kilometers("") == 0

    def test_input_reformats_on_text_change(self, dialog_factory):
        dlg = dialog_factory()
        dlg.kilometers_input.setText("123456")
        assert dlg.kilometers_input.text() == "123 456"


# ===========================================================================
# CarDialog — validation
# ===========================================================================

class TestCarDialogValidation:
    def _fill_valid(self, dlg):
        dlg.client_combo.setCurrentIndex(1)
        dlg.plate_input.setText("B-123-ABC")
        dlg.vin_input.setText("V" * 17)
        dlg.model_input.setText("Golf")
        dlg.kilometers_input.setText("12345")

    def test_no_client_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.client_combo.setCurrentIndex(0)  # sentinel
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()
        assert dlg.result() == 0

    def test_empty_plate_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.plate_input.setText("")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_plate_without_dash_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.plate_input.setText("BABC123")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_plate_only_digits_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.plate_input.setText("123-456")  # alphanumeric is all digits
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_empty_vin_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.vin_input.setText("")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_vin_too_short_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.vin_input.setText("SHORT")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_vin_too_long_truncates_via_maxlength(self, dialog_factory):
        dlg = dialog_factory()
        # setMaxLength(17) on the QLineEdit must already enforce this
        assert dlg.vin_input.maxLength() == 17

    def test_empty_model_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.model_input.setText("")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_empty_kilometers_blocks(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.kilometers_input.setText("")
        with patch("src.pages.cars.show_warning") as warn:
            dlg.validate_and_accept()
        warn.assert_called_once()

    def test_all_valid_accepts(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.validate_and_accept()
        assert dlg.result() == QDialog.DialogCode.Accepted

    def test_get_data_uppercases_plate_and_vin(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.plate_input.setText("b-1-abc")
        dlg.vin_input.setText("v" * 17)
        data = dlg.get_data()
        assert data["plate_number"] == "B-1-ABC"
        assert data["vin"] == "V" * 17

    def test_get_data_kilometers_parsed_to_int(self, dialog_factory):
        dlg = dialog_factory()
        self._fill_valid(dlg)
        dlg.kilometers_input.setText("123 456")
        assert dlg.get_data()["kilometers"] == 123456


# ===========================================================================
# CarsPage — table + filter + error handling on UNIQUE VIN
# ===========================================================================

_CARS_SAMPLE = [
    {"id": 1, "client_id": 1, "plate_number": "B-1", "vin": "A" * 17, "model": "Audi", "kilometers": 1000, "client_name": "Alice O."},
    {"id": 2, "client_id": 1, "plate_number": "B-2", "vin": "B" * 17, "model": "BMW",  "kilometers": 2000, "client_name": "Alice O."},
    {"id": 3, "client_id": 2, "plate_number": "B-3", "vin": "C" * 17, "model": "Audi", "kilometers": 3000, "client_name": "Bob D."},
]


@pytest.fixture
def cars_page(qapp):
    with patch("src.pages.cars.get_all_cars", return_value=_CARS_SAMPLE):
        from src.pages.cars import CarsPage
        return CarsPage()


class TestCarsPage:
    def test_loads_all_rows(self, cars_page):
        assert cars_page.cars_table.rowCount() == 3

    def test_filter_by_plate(self, cars_page):
        cars_page.filter_cars("B-1")
        assert cars_page.cars_table.rowCount() == 1

    def test_filter_by_vin(self, cars_page):
        cars_page.filter_cars("B" * 17)
        assert cars_page.cars_table.rowCount() == 1

    def test_filter_by_model(self, cars_page):
        cars_page.filter_cars("audi")
        assert cars_page.cars_table.rowCount() == 2

    def test_filter_by_client(self, cars_page):
        cars_page.filter_cars("alice")
        assert cars_page.cars_table.rowCount() == 2

    def test_filter_empty_shows_all(self, cars_page):
        cars_page.filter_cars("zzz")
        cars_page.filter_cars("")
        assert cars_page.cars_table.rowCount() == 3

    def test_add_car_unique_constraint_shows_warning(self, cars_page):
        with patch("src.pages.cars.CarDialog") as MockDialog, \
             patch("src.pages.cars.add_car", side_effect=Exception("UNIQUE constraint failed: cars.vin")), \
             patch("src.pages.cars.show_warning") as warn:
            dlg = MockDialog.return_value
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {
                "client_id": 1, "plate_number": "P", "vin": "X" * 17, "model": "M", "kilometers": 1,
            }
            cars_page.add_car()
        warn.assert_called_once()
        msg = warn.call_args[0][2]
        assert "VIN" in msg or "vin" in msg

    def test_add_car_unknown_error_shows_critical(self, cars_page):
        with patch("src.pages.cars.CarDialog") as MockDialog, \
             patch("src.pages.cars.add_car", side_effect=Exception("boom")), \
             patch("src.pages.cars.show_critical") as crit:
            dlg = MockDialog.return_value
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {
                "client_id": 1, "plate_number": "P", "vin": "X" * 17, "model": "M", "kilometers": 1,
            }
            cars_page.add_car()
        crit.assert_called_once()
