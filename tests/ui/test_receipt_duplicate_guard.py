"""UI-layer tests for duplicate receipt prevention in ReceiptFormPage.

The duplicate check uses plate_number + date as the uniqueness key.
Tests verify:
  1. on_save_clicked:
       - no plate → no check, proceeds to save
       - no duplicate → proceeds
       - duplicate found → shows warning, does NOT call add/update
       - editing own record (same plate+date, same id) → allowed
       - editing, different receipt has same plate+date → blocked
  2. _do_generate:
       - duplicate found → shows warning, does NOT call add/update
       - own plate+date when editing → allowed
       - no duplicate → proceeds to generate

All DB and service calls are mocked so no real DB is touched.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Session-scoped Qt application
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXISTING_RECEIPT = {
    "id": 99,
    "plate_number": "B123ABC",
    "date": "08.05.2026",
    "client_name": "Ion Popescu",
}

_RECEIPT_DATA = {
    "client_id": 1,
    "client_name": "Ion Popescu",
    "car_id": 1,
    "plate_number": "B123ABC",
    "date": "08.05.2026",
    "vin": "",
    "model": "Dacia Logan",
    "kilometers": "50000",
    "executant_name": "Gelu Mecanic",
    "estimate_cost": 0.0,
    "estimated_final_date": "10.05.2026",
    "defects": [],
    "discovered_defects": [],
    "parts": [],
    "labor": [],
    "total_labor_cost": 0.0,
    "billable_parts": [],
    "total_parts_cost": 0.0,
    "grand_total": 0.0,
    "status": "Ongoing",
}


def _make_form(qapp) -> "ReceiptFormPage":
    """Create a ReceiptFormPage with all DB dependencies patched."""
    patches = [
        patch("src.pages.receipts.receipt_info.get_all_clients", return_value=[]),
        patch("src.pages.receipts.receipt_info.get_all_cars", return_value=[]),
        patch("src.pages.receipts.receipt_info.get_all_employees", return_value=[]),
        patch("src.pages.receipts.defects_section.get_all_defects", return_value=[]),
        patch("src.pages.receipts.parts_section.get_all_parts", return_value=[]),
        patch("src.pages.receipts.labor_section.get_all_labor", return_value=[]),
        patch("src.pages.receipts.billable_parts_section.get_all_parts", return_value=[]),
    ]
    for p in patches:
        p.start()

    from src.pages.receipts.receipt_form import ReceiptFormPage
    form = ReceiptFormPage()
    form.receipt_data = dict(_RECEIPT_DATA)

    for p in patches:
        p.stop()

    return form


# ===========================================================================
# TestSaveClickedDuplicateGuard
# ===========================================================================

class TestSaveClickedDuplicateGuard:
    @pytest.fixture(autouse=True)
    def form(self, qapp):
        self._form = _make_form(qapp)

    # --- new receipt ---------------------------------------------------------

    def test_save_no_plate_skips_duplicate_check_and_saves(self):
        """When there is no plate number the model returns None (no conflict)."""
        self._form.receipt_data = dict(_RECEIPT_DATA, plate_number="")
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.add_receipt", return_value=1) as mock_add, \
             patch("src.pages.receipts.receipt_form.show_info"), \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn:
            self._form.on_save_clicked()

        mock_check.assert_called_once()
        mock_add.assert_called_once()
        mock_warn.assert_not_called()

    def test_save_no_duplicate_calls_add_receipt(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.add_receipt", return_value=42) as mock_add, \
             patch("src.pages.receipts.receipt_form.show_info"):
            self._form.on_save_clicked()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=None)
        mock_add.assert_called_once()

    def test_save_duplicate_shows_warning(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=_EXISTING_RECEIPT), \
             patch("src.pages.receipts.receipt_form.add_receipt") as mock_add, \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn:
            self._form.on_save_clicked()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()
        title = mock_warn.call_args[0][1]
        assert "Duplicate" in title or "duplicate" in title

    def test_save_duplicate_does_not_add_receipt(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=_EXISTING_RECEIPT), \
             patch("src.pages.receipts.receipt_form.add_receipt") as mock_add, \
             patch("src.pages.receipts.receipt_form.show_warning"):
            self._form.on_save_clicked()

        mock_add.assert_not_called()

    def test_save_missing_client_blocks_before_duplicate_check(self):
        """No client set → warning shown, duplicate check never reached."""
        self._form.receipt_data = dict(_RECEIPT_DATA, client_id=None)
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date") as mock_check, \
             patch("src.pages.receipts.receipt_form.add_receipt") as mock_add, \
             patch("src.pages.receipts.receipt_form.show_warning"):
            self._form.on_save_clicked()

        mock_check.assert_not_called()
        mock_add.assert_not_called()

    # --- editing existing receipt --------------------------------------------

    def test_save_edit_no_duplicate_calls_update(self):
        self._form.editing_receipt_id = 7

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.update_receipt") as mock_update, \
             patch("src.pages.receipts.receipt_form.show_info"):
            self._form.on_save_clicked()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=7)
        mock_update.assert_called_once()

    def test_save_edit_own_plate_date_is_allowed(self):
        """Same plate+date but exclude_id matches → no conflict."""
        self._form.editing_receipt_id = 7

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None), \
             patch("src.pages.receipts.receipt_form.update_receipt") as mock_update, \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn, \
             patch("src.pages.receipts.receipt_form.show_info"):
            self._form.on_save_clicked()

        mock_update.assert_called_once()
        mock_warn.assert_not_called()

    def test_save_edit_other_receipt_has_same_plate_date_is_blocked(self):
        self._form.editing_receipt_id = 7

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=_EXISTING_RECEIPT), \
             patch("src.pages.receipts.receipt_form.update_receipt") as mock_update, \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn:
            self._form.on_save_clicked()

        mock_update.assert_not_called()
        mock_warn.assert_called_once()

    def test_save_exclude_id_passed_correctly_when_editing(self):
        self._form.editing_receipt_id = 55

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.update_receipt"), \
             patch("src.pages.receipts.receipt_form.show_info"):
            self._form.on_save_clicked()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=55)

    def test_save_exclude_id_is_none_when_new(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.add_receipt", return_value=1), \
             patch("src.pages.receipts.receipt_form.show_info"):
            self._form.on_save_clicked()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=None)


# ===========================================================================
# TestGenerateDuplicateGuard
# ===========================================================================

class TestGenerateDuplicateGuard:
    @pytest.fixture(autouse=True)
    def form(self, qapp):
        self._form = _make_form(qapp)

    def test_generate_duplicate_shows_warning_and_does_not_add(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=_EXISTING_RECEIPT), \
             patch("src.pages.receipts.receipt_form.add_receipt") as mock_add, \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn:
            self._form._do_generate()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()
        title = mock_warn.call_args[0][1]
        assert "Duplicate" in title or "duplicate" in title

    def test_generate_no_duplicate_proceeds_to_add(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None), \
             patch("src.pages.receipts.receipt_form.generate_receipt_excel",
                   return_value=("out.xlsx", [])), \
             patch("src.pages.receipts.receipt_form.add_receipt", return_value=1) as mock_add, \
             patch("src.pages.receipts.receipt_form.show_info"), \
             patch("os.startfile"):
            self._form._do_generate()

        mock_add.assert_called_once()

    def test_generate_edit_own_plate_date_allowed(self):
        self._form.editing_receipt_id = 7

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.generate_receipt_excel",
                   return_value=("out.xlsx", [])), \
             patch("src.pages.receipts.receipt_form.update_receipt") as mock_update, \
             patch("src.pages.receipts.receipt_form.show_info"), \
             patch("os.startfile"):
            self._form._do_generate()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=7)
        mock_update.assert_called_once()

    def test_generate_edit_other_duplicate_is_blocked(self):
        self._form.editing_receipt_id = 7

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=_EXISTING_RECEIPT), \
             patch("src.pages.receipts.receipt_form.update_receipt") as mock_update, \
             patch("src.pages.receipts.receipt_form.show_warning") as mock_warn:
            self._form._do_generate()

        mock_update.assert_not_called()
        mock_warn.assert_called_once()

    def test_generate_missing_template_blocks_before_duplicate_check(self):
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=False), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date") as mock_check, \
             patch("src.pages.receipts.receipt_form.show_warning"):
            self._form._do_generate()

        mock_check.assert_not_called()

    def test_generate_missing_client_blocks_before_duplicate_check(self):
        self._form.receipt_data = dict(_RECEIPT_DATA, client_id=None)
        self._form.editing_receipt_id = None

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date") as mock_check, \
             patch("src.pages.receipts.receipt_form.show_warning"):
            self._form._do_generate()

        mock_check.assert_not_called()

    def test_generate_exclude_id_passed_correctly_when_editing(self):
        self._form.editing_receipt_id = 33

        with patch("src.pages.receipts.receipt_form.template_exists", return_value=True), \
             patch("src.pages.receipts.receipt_form.create_backup"), \
             patch("src.pages.receipts.receipt_form.get_receipt_by_plate_and_date",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.receipt_form.generate_receipt_excel",
                   return_value=("out.xlsx", [])), \
             patch("src.pages.receipts.receipt_form.update_receipt"), \
             patch("src.pages.receipts.receipt_form.show_info"), \
             patch("os.startfile"):
            self._form._do_generate()

        mock_check.assert_called_once_with("B123ABC", "08.05.2026", exclude_id=33)
