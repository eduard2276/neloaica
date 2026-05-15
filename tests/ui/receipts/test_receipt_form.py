"""Tests for ReceiptFormPage — labor combo refresh on tab switch.

BUG  Labor list not refreshed in open receipt form
     After adding a new labor service (via the Labor page or the ➕
     button) while a receipt form tab is already open, the new service
     does NOT appear in the labor combo box unless the user opens a
     brand-new receipt.
     Fix: ReceiptFormPage must call _reload_all_data(restore_state=True)
     inside showEvent so any tab-switch back to the form picks up the
     latest DB data.
"""

from unittest.mock import patch

import pytest
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Shared Qt application fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

INITIAL_LABOR = [
    {"id": 1, "service_name": "Schimb ulei"},
    {"id": 2, "service_name": "Inlocuire placute frana"},
]

NEW_LABOR_SERVICE = {"id": 99, "service_name": "Serviciu nou adaugat"}

EXTENDED_LABOR = INITIAL_LABOR + [NEW_LABOR_SERVICE]

MOCK_CLIENTS = []
MOCK_CARS = []
MOCK_EMPLOYEES = []
MOCK_DEFECTS = []
MOCK_PARTS = []


def _all_patches(labor_list):
    """Return a list of patch() context managers needed to create ReceiptFormPage."""
    return [
        patch("src.pages.receipts.receipt_info.get_all_clients", return_value=MOCK_CLIENTS),
        patch("src.pages.receipts.receipt_info.get_all_cars", return_value=MOCK_CARS),
        patch("src.pages.receipts.receipt_info.get_all_employees", return_value=MOCK_EMPLOYEES),
        patch("src.pages.receipts.defects_section.get_all_defects", return_value=MOCK_DEFECTS),
        patch("src.pages.receipts.parts_section.get_all_parts", return_value=MOCK_PARTS),
        patch("src.pages.receipts.labor_section.get_all_labor", return_value=labor_list),
        patch("src.pages.receipts.billable_parts_section.get_all_parts", return_value=MOCK_PARTS),
    ]


# ===========================================================================
# Tests
# ===========================================================================


class TestLaborRefresh:

    def test_labor_section_picks_up_new_service_on_explicit_reload(self, qapp):
        """
        Baseline: LaborSectionWidget.load_data(restore_state=True) does
        pick up new DB entries.  This must pass before AND after the fix.
        """
        from src.pages.receipts.labor_section import LaborSectionWidget

        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=INITIAL_LABOR):
            widget = LaborSectionWidget()

        ids_before = [widget.labor_combo.itemData(i) for i in range(widget.labor_combo.count())]
        assert NEW_LABOR_SERVICE["id"] not in ids_before

        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=EXTENDED_LABOR):
            widget.load_data(restore_state=True)

        ids_after = [widget.labor_combo.itemData(i) for i in range(widget.labor_combo.count())]
        assert (
            NEW_LABOR_SERVICE["id"] in ids_after
        ), "After load_data(restore_state=True) the new service must appear in the combo"

    def test_receipt_form_shows_new_labor_after_being_reshown(self, qapp):
        """
        Regression test: when the user switches back to an open receipt tab,
        newly added labor services must appear in the combo box.

        Scenario:
          1. A ReceiptFormPage is created and load_for_new() is called.
          2. While the tab is open a new labor service is added to the DB.
          3. The user switches away and back – triggering showEvent.
          4. The new service MUST now appear in the labor combo.
        """
        from src.pages.receipts.receipt_form import ReceiptFormPage

        patches = _all_patches(INITIAL_LABOR)
        for p in patches:
            p.__enter__()
        try:
            form = ReceiptFormPage()
            form.load_for_new()
        finally:
            for p in patches:
                p.__exit__(None, None, None)

        ids_before = [
            form.labor_widget.labor_combo.itemData(i)
            for i in range(form.labor_widget.labor_combo.count())
        ]
        assert (
            NEW_LABOR_SERVICE["id"] not in ids_before
        ), "Precondition: new service must not be in combo before tab-switch"

        with patch("src.pages.receipts.labor_section.get_all_labor", return_value=EXTENDED_LABOR):
            form.showEvent(QShowEvent())

        ids_after = [
            form.labor_widget.labor_combo.itemData(i)
            for i in range(form.labor_widget.labor_combo.count())
        ]
        assert (
            NEW_LABOR_SERVICE["id"] in ids_after
        ), "After showEvent, the new labor service must appear in the combo."
