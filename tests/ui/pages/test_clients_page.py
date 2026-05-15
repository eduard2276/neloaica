"""UI tests for ClientsPage and ClientDialog (`src/pages/clients.py`).

All DB calls are patched so the tests never touch a real database.
The qapp fixture is provided by tests/conftest.py.
"""

from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QDialog


# ===========================================================================
# ClientDialog — validation
# ===========================================================================

class TestClientDialogValidation:
    def _dialog(self):
        from src.pages.clients import ClientDialog
        return ClientDialog(parent=None, client=None)

    def test_window_title_add(self, qapp):
        dlg = self._dialog()
        assert dlg.windowTitle() == "Add Client"

    def test_window_title_edit(self, qapp):
        from src.pages.clients import ClientDialog
        client = {"id": 1, "first_name": "John", "last_name": "Doe", "address": "Addr"}
        dlg = ClientDialog(parent=None, client=client)
        assert dlg.windowTitle() == "Edit Client"
        assert dlg.first_name_input.text() == "John"
        assert dlg.last_name_input.text() == "Doe"
        assert dlg.address_input.text() == "Addr"

    def test_empty_first_name_blocks_accept(self, qapp):
        dlg = self._dialog()
        dlg.last_name_input.setText("L")
        dlg.address_input.setText("A")
        with patch("src.pages.clients.show_warning") as mock_warn:
            dlg.validate_and_accept()
        assert dlg.result() == 0  # not accepted
        mock_warn.assert_called_once()

    def test_empty_last_name_blocks_accept(self, qapp):
        dlg = self._dialog()
        dlg.first_name_input.setText("F")
        dlg.address_input.setText("A")
        with patch("src.pages.clients.show_warning") as mock_warn:
            dlg.validate_and_accept()
        mock_warn.assert_called_once()

    def test_empty_address_blocks_accept(self, qapp):
        dlg = self._dialog()
        dlg.first_name_input.setText("F")
        dlg.last_name_input.setText("L")
        with patch("src.pages.clients.show_warning") as mock_warn:
            dlg.validate_and_accept()
        mock_warn.assert_called_once()

    def test_all_fields_filled_accepts(self, qapp):
        dlg = self._dialog()
        dlg.first_name_input.setText("First")
        dlg.last_name_input.setText("Last")
        dlg.address_input.setText("Addr")
        dlg.validate_and_accept()
        assert dlg.result() == QDialog.DialogCode.Accepted

    def test_get_data_trims_whitespace(self, qapp):
        dlg = self._dialog()
        dlg.first_name_input.setText("  First  ")
        dlg.last_name_input.setText("  Last ")
        dlg.address_input.setText(" Addr ")
        data = dlg.get_data()
        assert data == {"first_name": "First", "last_name": "Last", "address": "Addr"}

    def test_enter_key_triggers_validate(self, qapp):
        dlg = self._dialog()
        dlg.first_name_input.setText("F")
        dlg.last_name_input.setText("L")
        dlg.address_input.setText("A")
        evt = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        dlg.keyPressEvent(evt)
        assert dlg.result() == QDialog.DialogCode.Accepted


# ===========================================================================
# ClientsPage — table behaviour
# ===========================================================================

_CLIENTS_SAMPLE = [
    {"id": 1, "first_name": "John", "last_name": "Apple", "address": "1 Main St"},
    {"id": 2, "first_name": "Jane", "last_name": "Banana", "address": "2 Pine Ave"},
    {"id": 3, "first_name": "Alice", "last_name": "Cherry", "address": "3 Oak Rd"},
]


class TestClientsPage:
    @pytest.fixture
    def page(self, qapp):
        with patch("src.pages.clients.get_all_clients", return_value=_CLIENTS_SAMPLE):
            from src.pages.clients import ClientsPage
            return ClientsPage()

    def test_loads_all_clients(self, page):
        assert page.clients_table.rowCount() == 3

    def test_filter_by_first_name(self, page):
        page.filter_clients("john")
        assert page.clients_table.rowCount() == 1
        assert page.clients_table.item(0, 1).text() == "John"

    def test_filter_by_last_name(self, page):
        page.filter_clients("banana")
        assert page.clients_table.rowCount() == 1
        assert page.clients_table.item(0, 2).text() == "Banana"

    def test_filter_by_full_name(self, page):
        page.filter_clients("alice cherry")
        assert page.clients_table.rowCount() == 1

    def test_filter_no_match(self, page):
        page.filter_clients("zzzzzz")
        assert page.clients_table.rowCount() == 0

    def test_filter_empty_shows_all(self, page):
        page.filter_clients("alice")
        page.filter_clients("")
        assert page.clients_table.rowCount() == 3

    def test_filter_is_case_insensitive(self, page):
        page.filter_clients("JOHN")
        assert page.clients_table.rowCount() == 1

    def test_add_client_dialog_accepted_calls_db(self, page):
        from PySide6.QtWidgets import QDialog
        with patch("src.pages.clients.ClientDialog") as MockDialog, \
             patch("src.pages.clients.add_client") as mock_add, \
             patch("src.pages.clients.get_all_clients", return_value=_CLIENTS_SAMPLE):
            dlg = MockDialog.return_value
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {
                "first_name": "New", "last_name": "Person", "address": "addr",
            }
            page.add_client()
        mock_add.assert_called_once_with("New", "Person", "addr")

    def test_add_client_dialog_rejected_does_not_call_db(self, page):
        from PySide6.QtWidgets import QDialog
        with patch("src.pages.clients.ClientDialog") as MockDialog, \
             patch("src.pages.clients.add_client") as mock_add:
            dlg = MockDialog.return_value
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            page.add_client()
        mock_add.assert_not_called()

    def test_edit_client_by_id(self, page):
        from PySide6.QtWidgets import QDialog
        with patch("src.pages.clients.ClientDialog") as MockDialog, \
             patch("src.pages.clients.update_client") as mock_update, \
             patch("src.pages.clients.get_all_clients", return_value=_CLIENTS_SAMPLE):
            dlg = MockDialog.return_value
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {
                "first_name": "X", "last_name": "Y", "address": "Z",
            }
            page.edit_client_by_id(1)
        mock_update.assert_called_once_with(1, "X", "Y", "Z")

    def test_edit_unknown_id_is_silent(self, page):
        with patch("src.pages.clients.ClientDialog") as MockDialog, \
             patch("src.pages.clients.update_client") as mock_update:
            page.edit_client_by_id(9999)
        MockDialog.assert_not_called()
        mock_update.assert_not_called()

    def test_delete_unknown_id_is_silent(self, page):
        with patch("src.pages.clients.delete_client") as mock_del:
            page.delete_client_by_id(9999)
        mock_del.assert_not_called()
