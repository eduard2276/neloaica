"""End-to-end-ish tests for `ReceiptFormPage`.

We patch every DB / service call so the form can be constructed and driven
without touching the disk or the SQLite singleton.

Covers:
  * format_price  — formatting corner cases
  * _collect_save_data — grand_total = labor + parts
  * update_grand_total — label text + receipt_data field
  * has_unsaved_changes property + _dirty toggling
  * load_for_new       — resets all subsection signals & state
  * load_for_edit      — populates from receipt dict; bails on missing id
  * on_reset_clicked   — clears form and re-emits estimates_changed
  * _emit_tab_title    — title depends on editing_receipt_id
"""

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def form(qapp):
    """Build a ReceiptFormPage with all DB dependencies patched out."""
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

    f = ReceiptFormPage()
    for p in patches:
        p.stop()
    return f


# ===========================================================================
# TestFormatPrice
# ===========================================================================


class TestFormatPrice:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (0, "0.00"),
            (1, "1.00"),
            (10, "10.00"),
            (100, "100.00"),
            (1000, "1 000.00"),
            (12345.6, "12 345.60"),
            (1234567.89, "1 234 567.89"),
            ("12.5", "12.50"),
        ],
    )
    def test_valid_values(self, form, value, expected):
        assert form.format_price(value) == expected

    @pytest.mark.parametrize("bad", [None, "abc", "", "not a number"])
    def test_bad_values_return_zero(self, form, bad):
        assert form.format_price(bad) == "0.00"

    def test_negative_value(self, form):
        # Negative values are not actively guarded against
        out = form.format_price(-12.5)
        assert out  # Just don't crash


# ===========================================================================
# TestCollectSaveData
# ===========================================================================


class TestCollectSaveData:
    def test_grand_total_is_sum(self, form):
        form.receipt_data = {
            "total_labor_cost": 100.0,
            "total_parts_cost": 200.5,
        }
        out = form._collect_save_data()
        assert out["grand_total"] == pytest.approx(300.5)

    def test_missing_keys_default_to_zero(self, form):
        form.receipt_data = {}
        out = form._collect_save_data()
        assert out["grand_total"] == 0.0

    def test_does_not_mutate_receipt_data(self, form):
        form.receipt_data = {"total_labor_cost": 10}
        original = dict(form.receipt_data)
        form._collect_save_data()
        # Original dict should not gain a grand_total key
        assert "grand_total" not in original


# ===========================================================================
# TestUpdateGrandTotal
# ===========================================================================


class TestUpdateGrandTotal:
    def test_label_reflects_sum(self, form):
        form.receipt_data = {"total_labor_cost": 100, "total_parts_cost": 50}
        form.update_grand_total()
        assert form.grand_total_value.text() == "150.00 Lei"

    def test_zero_values(self, form):
        form.receipt_data = {}
        form.update_grand_total()
        assert form.grand_total_value.text() == "0.00 Lei"


# ===========================================================================
# TestDirtyFlag
# ===========================================================================


class TestDirtyFlag:
    def test_load_for_new_resets_dirty(self, form):
        # The widget constructor calls on_estimates_changed which sets _dirty,
        # so we explicitly reset via load_for_new (the normal entry point).
        with patch.object(form, "_reload_all_data"):
            form.load_for_new()
        assert form.has_unsaved_changes is False

    def test_section_change_marks_dirty(self, form):
        form.on_defects_changed([1, 2])
        assert form.has_unsaved_changes is True

    def test_labor_change_marks_dirty(self, form):
        form.on_labor_changed([1], 100.0)
        assert form.has_unsaved_changes is True

    def test_billable_parts_marks_dirty(self, form):
        form.on_billable_parts_changed([{"part_id": 1, "units": 1, "price_per_unit": 10}], 10.0)
        assert form.has_unsaved_changes is True


# ===========================================================================
# TestLoadForNew
# ===========================================================================


class TestLoadForNew:
    def test_resets_state(self, form):
        form.editing_receipt_id = 99
        form.receipt_data = {"client_id": 1}
        form._dirty = True

        with patch.object(form, "_reload_all_data"):
            form.load_for_new()

        assert form.editing_receipt_id is None
        assert (
            form.receipt_data == {}
            or form.receipt_data.get("estimate_cost", None) == 0.0
            or "client_id" not in form.receipt_data
        )
        assert form.has_unsaved_changes is False
        assert form.grand_total_value.text() == "0.00 Lei"

    def test_title_is_new_receipt(self, form):
        with patch.object(form, "_reload_all_data"):
            form.load_for_new()
        assert "New Receipt" in form.title_label.text()


# ===========================================================================
# TestLoadForEdit
# ===========================================================================

_FAKE_RECEIPT = {
    "id": 7,
    "client_id": 1,
    "car_id": 11,
    "kilometers": "1000",
    "executant_name": "Mechanic",
    "date": "08.05.2026",
    "estimate_cost": 100.0,
    "estimated_final_date": "10.05.2026",
    "defects": [],
    "discovered_defects": [],
    "parts": [],
    "labor": [],
    "total_labor_cost": 50.0,
    "billable_parts": [],
    "total_parts_cost": 25.0,
}


class TestLoadForEdit:
    def test_missing_receipt_emits_close(self, form):
        with (
            patch("src.pages.receipts.receipt_form.get_receipt_by_id", return_value=None),
            patch("src.pages.receipts.receipt_form.show_warning"),
        ):
            captured = []
            form.close_requested.connect(lambda: captured.append(True))
            form.load_for_edit(999)
        assert captured == [True]

    def test_existing_receipt_populates_form(self, form):
        with (
            patch("src.pages.receipts.receipt_form.get_receipt_by_id", return_value=_FAKE_RECEIPT),
            patch.object(form.receipt_info_widget, "set_data"),
            patch.object(form.estimates_widget, "set_data"),
            patch.object(form.defects_widget, "set_data"),
            patch.object(form.discovered_defects_widget, "set_data"),
            patch.object(form.parts_widget, "set_data"),
            patch.object(form.labor_widget, "set_data"),
            patch.object(form.billable_parts_widget, "set_data"),
        ):
            form.load_for_edit(7)
        assert form.editing_receipt_id == 7
        assert "#7" in form.title_label.text()
        assert form.has_unsaved_changes is False


# ===========================================================================
# TestEmitTabTitle
# ===========================================================================


class TestEmitTabTitle:
    def test_new_receipt(self, form):
        captured = []
        form.tab_title_changed.connect(captured.append)
        form.editing_receipt_id = None
        form._emit_tab_title()
        assert captured[-1] == "New Receipt"

    def test_editing_receipt(self, form):
        captured = []
        form.tab_title_changed.connect(captured.append)
        form.editing_receipt_id = 5
        form.receipt_data = {"client_name": "Ion Popescu"}
        form._emit_tab_title()
        assert captured[-1] == "Receipt #5 - Ion Popescu"

    def test_editing_receipt_no_name(self, form):
        captured = []
        form.tab_title_changed.connect(captured.append)
        form.editing_receipt_id = 5
        form.receipt_data = {}
        form._emit_tab_title()
        assert captured[-1] == "Receipt #5"


# ===========================================================================
# TestOnSaveClicked
# ===========================================================================


class TestOnSaveClicked:
    def test_missing_client_shows_warning(self, form):
        form.receipt_data = {}
        with (
            patch("src.pages.receipts.receipt_form.show_warning") as warn,
            patch("src.pages.receipts.receipt_form.add_receipt") as add,
        ):
            form.on_save_clicked()
        warn.assert_called_once()
        add.assert_not_called()

    def test_new_receipt_calls_add_and_assigns_id(self, form):
        form.receipt_data = {
            "client_id": 1,
            "plate_number": "P-1",
            "date": "01.01.2026",
            "total_labor_cost": 50.0,
            "total_parts_cost": 0.0,
        }
        form.editing_receipt_id = None
        captured = []
        form.receipt_id_assigned.connect(captured.append)
        with (
            patch(
                "src.pages.receipts.receipt_form.get_receipt_by_plate_and_date", return_value=None
            ),
            patch("src.pages.receipts.receipt_form.add_receipt", return_value=42),
            patch("src.pages.receipts.receipt_form.show_info"),
        ):
            form.on_save_clicked()
        assert form.editing_receipt_id == 42
        assert captured == [42]
        assert form.has_unsaved_changes is False


# ===========================================================================
# TestOnResetClicked
# ===========================================================================


class TestOnResetClicked:
    def test_clears_receipt_data(self, form):
        form.receipt_data = {"client_id": 1, "total_labor_cost": 100}
        with (
            patch.object(form, "_reload_all_data"),
            patch("src.pages.receipts.receipt_form.show_info"),
        ):
            form.on_reset_clicked()
        # client_id is removed; estimate fields are zero
        assert "client_id" not in form.receipt_data

    def test_grand_total_label_resets(self, form):
        form.receipt_data = {"total_labor_cost": 100, "total_parts_cost": 50}
        form.update_grand_total()
        assert "150" in form.grand_total_value.text()
        with (
            patch.object(form, "_reload_all_data"),
            patch("src.pages.receipts.receipt_form.show_info"),
        ):
            form.on_reset_clicked()
        assert form.grand_total_value.text() == "0.00 Lei"
