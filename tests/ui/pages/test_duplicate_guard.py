"""UI-layer tests for duplicate prevention in Labor, Parts, Defects, Employees pages.

Each test mocks the DB lookup (get_X_by_name) and the add/update call to verify:
  1. When a duplicate name is returned by the lookup → the page shows a warning and
     does NOT call the underlying add/update function.
  2. When no duplicate exists → the page proceeds normally (add/update called).
  3. When updating a record to its own current name (same ID) → allowed (no warning).

Tests use unittest.mock.patch to avoid touching any real database.
"""

import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication, QDialog


# ---------------------------------------------------------------------------
# Session-scoped Qt application
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ===========================================================================
# Helpers
# ===========================================================================

def _accept_dialog(dialog, data: dict):
    """Monkeypatch dialog.exec() to return Accepted and dialog.get_data() to
    return *data*, simulating the user filling the form and pressing Save."""
    dialog.exec = MagicMock(return_value=QDialog.DialogCode.Accepted)
    dialog.get_data = MagicMock(return_value=data)


# ===========================================================================
# Labor Page — Duplicate Guard
# ===========================================================================

class TestLaborPageDuplicateGuard:
    """Verify LaborPage.add_labor and .edit_labor_by_id enforce uniqueness."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        patches = [
            patch("src.pages.labor.get_all_labor", return_value=[]),
            patch("src.pages.labor.get_labor_by_name"),
            patch("src.pages.labor.add_labor"),
            patch("src.pages.labor.update_labor"),
            patch("src.pages.labor.delete_labor"),
        ]
        self.mocks = {p.attribute: p.start() for p in patches}
        self._patches = patches

        from src.pages.labor import LaborPage
        self.page = LaborPage()
        yield
        for p in patches:
            p.stop()

    # --- add_labor -----------------------------------------------------------

    def test_add_labor_no_duplicate_calls_add(self):
        self.mocks["get_labor_by_name"].return_value = None
        with patch("src.pages.labor.LaborDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "New Service"}
            MockDialog.return_value = dlg
            self.page.add_labor()
        self.mocks["add_labor"].assert_called_once_with("New Service")

    def test_add_labor_duplicate_does_not_call_add(self):
        self.mocks["get_labor_by_name"].return_value = {"id": 5, "service_name": "Oil Change"}
        with patch("src.pages.labor.LaborDialog") as MockDialog, \
             patch("src.pages.labor.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "oil change"}
            MockDialog.return_value = dlg
            self.page.add_labor()
        self.mocks["add_labor"].assert_not_called()
        mock_warn.assert_called_once()

    def test_add_labor_duplicate_shows_warning(self):
        self.mocks["get_labor_by_name"].return_value = {"id": 5, "service_name": "Oil Change"}
        with patch("src.pages.labor.LaborDialog") as MockDialog, \
             patch("src.pages.labor.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "OIL CHANGE"}
            MockDialog.return_value = dlg
            self.page.add_labor()
        mock_warn.assert_called_once()
        title = mock_warn.call_args[0][1]
        assert "duplicate" in title.lower() or "Duplicate" in title

    # --- edit_labor_by_id ---------------------------------------------------

    def test_edit_labor_no_duplicate_calls_update(self):
        self.mocks["get_all_labor"].return_value = [{"id": 1, "service_name": "Old"}]
        self.page.load_data()
        self.mocks["get_labor_by_name"].return_value = None
        with patch("src.pages.labor.LaborDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "Unique Name"}
            MockDialog.return_value = dlg
            self.page.edit_labor_by_id(1)
        self.mocks["update_labor"].assert_called_once_with(1, "Unique Name")

    def test_edit_labor_same_name_same_id_calls_update(self):
        """Saving with the record's own current name (same ID) must NOT block."""
        self.mocks["get_all_labor"].return_value = [{"id": 1, "service_name": "Oil Change"}]
        self.page.load_data()
        # lookup returns the same record (same id)
        self.mocks["get_labor_by_name"].return_value = {"id": 1, "service_name": "Oil Change"}
        with patch("src.pages.labor.LaborDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "Oil Change"}
            MockDialog.return_value = dlg
            self.page.edit_labor_by_id(1)
        self.mocks["update_labor"].assert_called_once_with(1, "Oil Change")

    def test_edit_labor_duplicate_other_id_does_not_call_update(self):
        self.mocks["get_all_labor"].return_value = [{"id": 1, "service_name": "Old"}]
        self.page.load_data()
        # lookup returns a DIFFERENT record (id=2)
        self.mocks["get_labor_by_name"].return_value = {"id": 2, "service_name": "Oil Change"}
        with patch("src.pages.labor.LaborDialog") as MockDialog, \
             patch("src.pages.labor.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"service_name": "oil change"}
            MockDialog.return_value = dlg
            self.page.edit_labor_by_id(1)
        self.mocks["update_labor"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_labor_dialog_cancelled_does_not_call_update(self):
        self.mocks["get_all_labor"].return_value = [{"id": 1, "service_name": "Old"}]
        self.page.load_data()
        with patch("src.pages.labor.LaborDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.page.edit_labor_by_id(1)
        self.mocks["update_labor"].assert_not_called()


# ===========================================================================
# Parts Page — Duplicate Guard
# ===========================================================================

class TestPartsPageDuplicateGuard:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        patches = [
            patch("src.pages.parts.get_all_parts", return_value=[]),
            patch("src.pages.parts.get_part_by_name"),
            patch("src.pages.parts.add_part"),
            patch("src.pages.parts.update_part"),
            patch("src.pages.parts.delete_part"),
        ]
        self.mocks = {p.attribute: p.start() for p in patches}
        self._patches = patches

        from src.pages.parts import PartsPage
        self.page = PartsPage()
        yield
        for p in patches:
            p.stop()

    def test_add_part_no_duplicate_calls_add(self):
        self.mocks["get_part_by_name"].return_value = None
        with patch("src.pages.parts.PartDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"part_name": "New Part"}
            MockDialog.return_value = dlg
            self.page.add_part()
        self.mocks["add_part"].assert_called_once_with("New Part")

    def test_add_part_duplicate_does_not_call_add(self):
        self.mocks["get_part_by_name"].return_value = {"id": 3, "part_name": "Brake Disc"}
        with patch("src.pages.parts.PartDialog") as MockDialog, \
             patch("src.pages.parts.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"part_name": "brake disc"}
            MockDialog.return_value = dlg
            self.page.add_part()
        self.mocks["add_part"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_part_no_duplicate_calls_update(self):
        self.mocks["get_all_parts"].return_value = [{"id": 1, "part_name": "Old Part"}]
        self.page.load_data()
        self.mocks["get_part_by_name"].return_value = None
        with patch("src.pages.parts.PartDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"part_name": "New Unique Part"}
            MockDialog.return_value = dlg
            self.page.edit_part_by_id(1)
        self.mocks["update_part"].assert_called_once_with(1, "New Unique Part")

    def test_edit_part_same_name_same_id_calls_update(self):
        self.mocks["get_all_parts"].return_value = [{"id": 1, "part_name": "Brake Disc"}]
        self.page.load_data()
        self.mocks["get_part_by_name"].return_value = {"id": 1, "part_name": "Brake Disc"}
        with patch("src.pages.parts.PartDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"part_name": "Brake Disc"}
            MockDialog.return_value = dlg
            self.page.edit_part_by_id(1)
        self.mocks["update_part"].assert_called_once_with(1, "Brake Disc")

    def test_edit_part_duplicate_other_id_does_not_call_update(self):
        self.mocks["get_all_parts"].return_value = [{"id": 1, "part_name": "Old Part"}]
        self.page.load_data()
        self.mocks["get_part_by_name"].return_value = {"id": 7, "part_name": "Brake Disc"}
        with patch("src.pages.parts.PartDialog") as MockDialog, \
             patch("src.pages.parts.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"part_name": "brake disc"}
            MockDialog.return_value = dlg
            self.page.edit_part_by_id(1)
        self.mocks["update_part"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_part_dialog_cancelled_does_not_call_update(self):
        self.mocks["get_all_parts"].return_value = [{"id": 1, "part_name": "Old Part"}]
        self.page.load_data()
        with patch("src.pages.parts.PartDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.page.edit_part_by_id(1)
        self.mocks["update_part"].assert_not_called()


# ===========================================================================
# Defects Page — Duplicate Guard
# ===========================================================================

class TestDefectsPageDuplicateGuard:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        patches = [
            patch("src.pages.defects.get_all_defects", return_value=[]),
            patch("src.pages.defects.get_defect_by_name"),
            patch("src.pages.defects.add_defect"),
            patch("src.pages.defects.update_defect"),
            patch("src.pages.defects.delete_defect"),
        ]
        self.mocks = {p.attribute: p.start() for p in patches}
        self._patches = patches

        from src.pages.defects import DefectsPage
        self.page = DefectsPage()
        yield
        for p in patches:
            p.stop()

    def test_add_defect_no_duplicate_calls_add(self):
        self.mocks["get_defect_by_name"].return_value = None
        with patch("src.pages.defects.DefectDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"defect_name": "New Defect"}
            MockDialog.return_value = dlg
            self.page.add_defect()
        self.mocks["add_defect"].assert_called_once_with("New Defect")

    def test_add_defect_duplicate_does_not_call_add(self):
        self.mocks["get_defect_by_name"].return_value = {"id": 4, "defect_name": "Scratch"}
        with patch("src.pages.defects.DefectDialog") as MockDialog, \
             patch("src.pages.defects.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"defect_name": "scratch"}
            MockDialog.return_value = dlg
            self.page.add_defect()
        self.mocks["add_defect"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_defect_no_duplicate_calls_update(self):
        self.mocks["get_all_defects"].return_value = [{"id": 1, "defect_name": "Old Defect"}]
        self.page.load_data()
        self.mocks["get_defect_by_name"].return_value = None
        with patch("src.pages.defects.DefectDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"defect_name": "Unique Defect"}
            MockDialog.return_value = dlg
            self.page.edit_defect_by_id(1)
        self.mocks["update_defect"].assert_called_once_with(1, "Unique Defect")

    def test_edit_defect_same_name_same_id_calls_update(self):
        self.mocks["get_all_defects"].return_value = [{"id": 1, "defect_name": "Scratch"}]
        self.page.load_data()
        self.mocks["get_defect_by_name"].return_value = {"id": 1, "defect_name": "Scratch"}
        with patch("src.pages.defects.DefectDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"defect_name": "Scratch"}
            MockDialog.return_value = dlg
            self.page.edit_defect_by_id(1)
        self.mocks["update_defect"].assert_called_once_with(1, "Scratch")

    def test_edit_defect_duplicate_other_id_does_not_call_update(self):
        self.mocks["get_all_defects"].return_value = [{"id": 1, "defect_name": "Old Defect"}]
        self.page.load_data()
        self.mocks["get_defect_by_name"].return_value = {"id": 9, "defect_name": "Scratch"}
        with patch("src.pages.defects.DefectDialog") as MockDialog, \
             patch("src.pages.defects.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"defect_name": "scratch"}
            MockDialog.return_value = dlg
            self.page.edit_defect_by_id(1)
        self.mocks["update_defect"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_defect_dialog_cancelled_does_not_call_update(self):
        self.mocks["get_all_defects"].return_value = [{"id": 1, "defect_name": "Old Defect"}]
        self.page.load_data()
        with patch("src.pages.defects.DefectDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.page.edit_defect_by_id(1)
        self.mocks["update_defect"].assert_not_called()


# ===========================================================================
# Employees Page — Duplicate Guard
# ===========================================================================

class TestEmployeesPageDuplicateGuard:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        patches = [
            patch("src.pages.employees.get_all_employees", return_value=[]),
            patch("src.pages.employees.get_employee_by_name"),
            patch("src.pages.employees.add_employee"),
            patch("src.pages.employees.update_employee"),
            patch("src.pages.employees.delete_employee"),
        ]
        self.mocks = {p.attribute: p.start() for p in patches}
        self._patches = patches

        from src.pages.employees import EmployeesPage
        self.page = EmployeesPage()
        yield
        for p in patches:
            p.stop()

    def test_add_employee_no_duplicate_calls_add(self):
        self.mocks["get_employee_by_name"].return_value = None
        with patch("src.pages.employees.EmployeeDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "Ion", "last_name": "Popescu"}
            MockDialog.return_value = dlg
            self.page.add_employee()
        self.mocks["add_employee"].assert_called_once_with("Ion", "Popescu")

    def test_add_employee_duplicate_does_not_call_add(self):
        self.mocks["get_employee_by_name"].return_value = {
            "id": 5, "first_name": "Ion", "last_name": "Popescu"
        }
        with patch("src.pages.employees.EmployeeDialog") as MockDialog, \
             patch("src.pages.employees.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "ion", "last_name": "popescu"}
            MockDialog.return_value = dlg
            self.page.add_employee()
        self.mocks["add_employee"].assert_not_called()
        mock_warn.assert_called_once()

    def test_add_employee_same_first_different_last_calls_add(self):
        """Ion Ionescu must be addable when Ion Popescu already exists."""
        self.mocks["get_employee_by_name"].return_value = None
        with patch("src.pages.employees.EmployeeDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "Ion", "last_name": "Ionescu"}
            MockDialog.return_value = dlg
            self.page.add_employee()
        self.mocks["add_employee"].assert_called_once_with("Ion", "Ionescu")

    def test_edit_employee_no_duplicate_calls_update(self):
        self.mocks["get_all_employees"].return_value = [
            {"id": 1, "first_name": "Ion", "last_name": "Popescu"}
        ]
        self.page.load_data()
        self.mocks["get_employee_by_name"].return_value = None
        with patch("src.pages.employees.EmployeeDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "Ion", "last_name": "Ionescu"}
            MockDialog.return_value = dlg
            self.page.edit_employee_by_id(1)
        self.mocks["update_employee"].assert_called_once_with(1, "Ion", "Ionescu")

    def test_edit_employee_same_name_same_id_calls_update(self):
        self.mocks["get_all_employees"].return_value = [
            {"id": 1, "first_name": "Ion", "last_name": "Popescu"}
        ]
        self.page.load_data()
        self.mocks["get_employee_by_name"].return_value = {
            "id": 1, "first_name": "Ion", "last_name": "Popescu"
        }
        with patch("src.pages.employees.EmployeeDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "Ion", "last_name": "Popescu"}
            MockDialog.return_value = dlg
            self.page.edit_employee_by_id(1)
        self.mocks["update_employee"].assert_called_once_with(1, "Ion", "Popescu")

    def test_edit_employee_duplicate_other_id_does_not_call_update(self):
        self.mocks["get_all_employees"].return_value = [
            {"id": 1, "first_name": "Ion", "last_name": "Popescu"}
        ]
        self.page.load_data()
        self.mocks["get_employee_by_name"].return_value = {
            "id": 2, "first_name": "Ion", "last_name": "Popescu"
        }
        with patch("src.pages.employees.EmployeeDialog") as MockDialog, \
             patch("src.pages.employees.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_data.return_value = {"first_name": "ion", "last_name": "popescu"}
            MockDialog.return_value = dlg
            self.page.edit_employee_by_id(1)
        self.mocks["update_employee"].assert_not_called()
        mock_warn.assert_called_once()

    def test_edit_employee_dialog_cancelled_does_not_call_update(self):
        self.mocks["get_all_employees"].return_value = [
            {"id": 1, "first_name": "Ion", "last_name": "Popescu"}
        ]
        self.page.load_data()
        with patch("src.pages.employees.EmployeeDialog") as MockDialog:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.page.edit_employee_by_id(1)
        self.mocks["update_employee"].assert_not_called()
