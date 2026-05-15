"""UI-layer tests for duplicate prevention in receipt section inline-add buttons.

The receipt form has ➕ buttons inside DefectsSectionWidget, PartsSectionWidget
(client parts), LaborSectionWidget, and BillablePartsSectionWidget (used parts)
that let users add catalog entries directly from the receipt form.

These tests verify:
  - When a duplicate name is found → warning shown, DB insert NOT called
  - When no duplicate → insert IS called
  - Case-insensitive detection (same logic as the catalog pages)
"""

import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication, QDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ===========================================================================
# DefectsSectionWidget — inline add
# ===========================================================================

class TestDefectsSectionInlineAdd:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        with patch("src.pages.receipts.defects_section.get_all_defects", return_value=[]):
            from src.pages.receipts.defects_section import DefectsSectionWidget
            self.widget = DefectsSectionWidget()

    def test_no_duplicate_calls_add_defect(self):
        with patch("src.pages.receipts.defects_section.get_defect_by_name",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.defects_section.AddDefectDialog") as MockDialog, \
             patch("src.pages.receipts.defects_section.add_defect_to_db",
                   return_value=1) as mock_add, \
             patch("src.pages.receipts.defects_section.get_all_defects", return_value=[]), \
             patch("src.pages.receipts.defects_section.show_info"):
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_defect_name.return_value = "New Defect"
            MockDialog.return_value = dlg
            self.widget.add_new_defect_to_database()

        mock_check.assert_called_once_with("New Defect")
        mock_add.assert_called_once_with("New Defect")

    def test_duplicate_shows_warning_and_does_not_add(self):
        with patch("src.pages.receipts.defects_section.get_defect_by_name",
                   return_value={"id": 5, "defect_name": "Scratch"}), \
             patch("src.pages.receipts.defects_section.AddDefectDialog") as MockDialog, \
             patch("src.pages.receipts.defects_section.add_defect_to_db") as mock_add, \
             patch("src.pages.receipts.defects_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_defect_name.return_value = "scratch"
            MockDialog.return_value = dlg
            self.widget.add_new_defect_to_database()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()

    def test_duplicate_warning_title_contains_duplicate(self):
        with patch("src.pages.receipts.defects_section.get_defect_by_name",
                   return_value={"id": 5, "defect_name": "Scratch"}), \
             patch("src.pages.receipts.defects_section.AddDefectDialog") as MockDialog, \
             patch("src.pages.receipts.defects_section.add_defect_to_db"), \
             patch("src.pages.receipts.defects_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_defect_name.return_value = "SCRATCH"
            MockDialog.return_value = dlg
            self.widget.add_new_defect_to_database()

        title = mock_warn.call_args[0][1]
        assert "Duplicate" in title or "duplicate" in title

    def test_dialog_cancelled_does_not_check_or_add(self):
        with patch("src.pages.receipts.defects_section.get_defect_by_name") as mock_check, \
             patch("src.pages.receipts.defects_section.AddDefectDialog") as MockDialog, \
             patch("src.pages.receipts.defects_section.add_defect_to_db") as mock_add:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.widget.add_new_defect_to_database()

        mock_check.assert_not_called()
        mock_add.assert_not_called()


# ===========================================================================
# PartsSectionWidget (client parts) — inline add
# ===========================================================================

class TestPartsSectionInlineAdd:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        with patch("src.pages.receipts.parts_section.get_all_parts", return_value=[]):
            from src.pages.receipts.parts_section import PartsSectionWidget
            self.widget = PartsSectionWidget()

    def test_no_duplicate_calls_add_part(self):
        with patch("src.pages.receipts.parts_section.get_part_by_name",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.parts_section.add_part_to_db",
                   return_value=1) as mock_add, \
             patch("src.pages.receipts.parts_section.show_info"):
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_part_name.return_value = "New Part"
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_check.assert_called_once_with("New Part")
        mock_add.assert_called_once_with("New Part")

    def test_duplicate_shows_warning_and_does_not_add(self):
        with patch("src.pages.receipts.parts_section.get_part_by_name",
                   return_value={"id": 3, "part_name": "Brake Disc"}), \
             patch("src.pages.receipts.parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.parts_section.add_part_to_db") as mock_add, \
             patch("src.pages.receipts.parts_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_part_name.return_value = "brake disc"
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()

    def test_dialog_cancelled_does_not_check_or_add(self):
        with patch("src.pages.receipts.parts_section.get_part_by_name") as mock_check, \
             patch("src.pages.receipts.parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.parts_section.add_part_to_db") as mock_add:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_check.assert_not_called()
        mock_add.assert_not_called()


# ===========================================================================
# LaborSectionWidget — inline add
# ===========================================================================

class TestLaborSectionInlineAdd:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=[]):
            from src.pages.receipts.labor_section import LaborSectionWidget
            self.widget = LaborSectionWidget()

    def test_no_duplicate_calls_add_labor(self):
        with patch("src.pages.receipts.labor_section.get_labor_by_name",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.labor_section.AddLaborDialog") as MockDialog, \
             patch("src.pages.receipts.labor_section.add_labor_to_db",
                   return_value=1) as mock_add, \
             patch("src.pages.receipts.labor_section.show_info"):
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_service_name.return_value = "New Service"
            MockDialog.return_value = dlg
            self.widget.add_new_labor_to_database()

        mock_check.assert_called_once_with("New Service")
        mock_add.assert_called_once_with("New Service")

    def test_duplicate_shows_warning_and_does_not_add(self):
        with patch("src.pages.receipts.labor_section.get_labor_by_name",
                   return_value={"id": 2, "service_name": "Oil Change"}), \
             patch("src.pages.receipts.labor_section.AddLaborDialog") as MockDialog, \
             patch("src.pages.receipts.labor_section.add_labor_to_db") as mock_add, \
             patch("src.pages.receipts.labor_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_service_name.return_value = "oil change"
            MockDialog.return_value = dlg
            self.widget.add_new_labor_to_database()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()

    def test_duplicate_warning_title_contains_duplicate(self):
        with patch("src.pages.receipts.labor_section.get_labor_by_name",
                   return_value={"id": 2, "service_name": "Oil Change"}), \
             patch("src.pages.receipts.labor_section.AddLaborDialog") as MockDialog, \
             patch("src.pages.receipts.labor_section.add_labor_to_db"), \
             patch("src.pages.receipts.labor_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_service_name.return_value = "OIL CHANGE"
            MockDialog.return_value = dlg
            self.widget.add_new_labor_to_database()

        title = mock_warn.call_args[0][1]
        assert "Duplicate" in title or "duplicate" in title

    def test_dialog_cancelled_does_not_check_or_add(self):
        with patch("src.pages.receipts.labor_section.get_labor_by_name") as mock_check, \
             patch("src.pages.receipts.labor_section.AddLaborDialog") as MockDialog, \
             patch("src.pages.receipts.labor_section.add_labor_to_db") as mock_add:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.widget.add_new_labor_to_database()

        mock_check.assert_not_called()
        mock_add.assert_not_called()


# ===========================================================================
# BillablePartsSectionWidget (parts used) — inline add
# ===========================================================================

class TestBillablePartsSectionInlineAdd:
    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        with patch("src.pages.receipts.billable_parts_section.get_all_parts", return_value=[]):
            from src.pages.receipts.billable_parts_section import BillablePartsSectionWidget
            self.widget = BillablePartsSectionWidget()

    def test_no_duplicate_calls_add_part(self):
        with patch("src.pages.receipts.billable_parts_section.get_part_by_name",
                   return_value=None) as mock_check, \
             patch("src.pages.receipts.billable_parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.billable_parts_section.add_part_to_db",
                   return_value=1) as mock_add, \
             patch("src.pages.receipts.billable_parts_section.show_info"):
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_part_name.return_value = "New Part"
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_check.assert_called_once_with("New Part")
        mock_add.assert_called_once_with("New Part")

    def test_duplicate_shows_warning_and_does_not_add(self):
        with patch("src.pages.receipts.billable_parts_section.get_part_by_name",
                   return_value={"id": 8, "part_name": "Air Filter"}), \
             patch("src.pages.receipts.billable_parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.billable_parts_section.add_part_to_db") as mock_add, \
             patch("src.pages.receipts.billable_parts_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_part_name.return_value = "AIR FILTER"
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_add.assert_not_called()
        mock_warn.assert_called_once()

    def test_duplicate_warning_title_contains_duplicate(self):
        with patch("src.pages.receipts.billable_parts_section.get_part_by_name",
                   return_value={"id": 8, "part_name": "Air Filter"}), \
             patch("src.pages.receipts.billable_parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.billable_parts_section.add_part_to_db"), \
             patch("src.pages.receipts.billable_parts_section.show_warning") as mock_warn:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Accepted
            dlg.get_part_name.return_value = "air filter"
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        title = mock_warn.call_args[0][1]
        assert "Duplicate" in title or "duplicate" in title

    def test_dialog_cancelled_does_not_check_or_add(self):
        with patch("src.pages.receipts.billable_parts_section.get_part_by_name") as mock_check, \
             patch("src.pages.receipts.billable_parts_section.AddPartDialog") as MockDialog, \
             patch("src.pages.receipts.billable_parts_section.add_part_to_db") as mock_add:
            dlg = MagicMock()
            dlg.exec.return_value = QDialog.DialogCode.Rejected
            MockDialog.return_value = dlg
            self.widget.add_new_part_to_database()

        mock_check.assert_not_called()
        mock_add.assert_not_called()
