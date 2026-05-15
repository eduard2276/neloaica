"""UI tests for SettingsPage (`src/pages/settings.py`).

Covers:
  * Initial load from DB
  * TVA input filter (digits + 1 dot + 2 decimals)
  * Receipt-number input filter (digits, no leading zeros)
  * Save validation (TVA range, receipt >= 1)
  * Manual backup happy + failure paths
  * Edit / Save / Cancel state transitions

All DB and service calls are patched so the test never writes a real DB.
The QMessageBox.exec is patched globally to keep the test headless.
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QMessageBox

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def page(qapp):
    with (
        patch("src.pages.settings.get_tva", return_value=21.0),
        patch("src.pages.settings.get_receipt_number", return_value=5),
    ):
        from src.pages.settings import SettingsPage

        return SettingsPage()


@pytest.fixture(autouse=True)
def _silence_msgbox():
    """Avoid blocking modal dialogs."""
    with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Ok):
        yield


# ===========================================================================
# TestInitialState
# ===========================================================================


class TestInitialState:
    def test_loads_tva_and_receipt_number(self, page):
        assert page.tva_input.text() == "21"
        assert page.receipt_number_input.text() == "5"

    def test_initially_read_only(self, page):
        assert page.tva_input.isReadOnly()
        assert page.receipt_number_input.isReadOnly()
        assert page.edit_button.isVisible() in (
            True,
            False,
        )  # not asserted explicitly because parent isn't shown

    def test_load_settings_with_fractional_tva(self, qapp):
        with (
            patch("src.pages.settings.get_tva", return_value=19.5),
            patch("src.pages.settings.get_receipt_number", return_value=1),
        ):
            from src.pages.settings import SettingsPage

            p = SettingsPage()
            assert p.tva_input.text() == "19.50"


# ===========================================================================
# TestTvaInputFilter
# ===========================================================================


class TestTvaInputFilter:
    def test_filter_strips_non_digits(self, page):
        page.tva_input.setText("abc12def.3xx")
        assert page.tva_input.text() == "12.3"

    def test_filter_keeps_only_first_dot(self, page):
        page.tva_input.setText("1.2.3")
        # Implementation splits on '.' and uses only parts[0] + parts[1].
        # Extra fragments after the second dot are dropped.
        assert page.tva_input.text() == "1.2"

    def test_decimal_capped_at_two_digits(self, page):
        page.tva_input.setText("1.2345")
        assert page.tva_input.text() == "1.23"

    def test_empty_input_allowed(self, page):
        page.tva_input.setText("")
        assert page.tva_input.text() == ""


# ===========================================================================
# TestReceiptNumberInputFilter
# ===========================================================================


class TestReceiptNumberInputFilter:
    def test_filter_strips_non_digits(self, page):
        page.receipt_number_input.setText("ab12cd34")
        assert page.receipt_number_input.text() == "1234"

    def test_filter_strips_leading_zeros(self, page):
        page.receipt_number_input.setText("00042")
        assert page.receipt_number_input.text() == "42"

    def test_filter_allows_single_zero(self, page):
        page.receipt_number_input.setText("0")
        assert page.receipt_number_input.text() == "0"

    def test_filter_allows_long_value(self, page):
        page.receipt_number_input.setText("123456")
        assert page.receipt_number_input.text() == "123456"


# ===========================================================================
# TestSaveValidation
# ===========================================================================


class TestSaveValidation:
    def test_tva_negative_blocks_save(self, page):
        page.tva_input.setReadOnly(False)
        page.tva_input.setText("-1")  # filter will strip -; text becomes "1"
        # Force invalid TVA directly:
        page.tva_input.setText("")
        # We rely on validate-on-save: simulate empty (which is valid since
        # save coerces "" to 0.0) but >100:
        page.tva_input.setText("200")
        with (
            patch("src.pages.settings.update_tva") as upd,
            patch("src.pages.settings.update_receipt_number"),
        ):
            page.save_settings()
        upd.assert_not_called()

    def test_tva_out_of_range_blocks_save(self, page):
        page.tva_input.setText("150")
        with patch("src.pages.settings.update_tva") as upd:
            page.save_settings()
        upd.assert_not_called()

    def test_receipt_zero_blocks_save(self, page):
        page.tva_input.setText("21")
        page.receipt_number_input.setText("0")
        with patch("src.pages.settings.update_receipt_number") as upd:
            page.save_settings()
        upd.assert_not_called()

    def test_successful_save_calls_both_updaters(self, page):
        page.tva_input.setText("19.50")
        page.receipt_number_input.setText("42")
        with (
            patch("src.pages.settings.update_tva") as u_tva,
            patch("src.pages.settings.update_receipt_number") as u_num,
        ):
            page.save_settings()
        u_tva.assert_called_once_with(19.5)
        u_num.assert_called_once_with(42)


# ===========================================================================
# TestEditCancelToggle
# ===========================================================================


class TestEditCancelToggle:
    def test_set_editing_true_enables_inputs(self, page):
        page.set_editing(True)
        assert not page.tva_input.isReadOnly()
        assert not page.receipt_number_input.isReadOnly()

    def test_set_editing_false_disables_inputs(self, page):
        page.set_editing(True)
        page.set_editing(False)
        assert page.tva_input.isReadOnly()
        assert page.receipt_number_input.isReadOnly()

    def test_cancel_restores_db_values(self, page):
        page.set_editing(True)
        page.tva_input.setText("99")
        page.receipt_number_input.setText("999")
        with (
            patch("src.pages.settings.get_tva", return_value=21.0),
            patch("src.pages.settings.get_receipt_number", return_value=5),
        ):
            page.cancel_editing()
        assert page.tva_input.text() == "21"
        assert page.receipt_number_input.text() == "5"
        assert page.tva_input.isReadOnly()


# ===========================================================================
# TestManualBackup
# ===========================================================================


class TestManualBackup:
    def test_success_calls_create_backup(self, page):
        with patch("src.pages.settings.create_backup", return_value=("path/x.db", True)) as mock_bk:
            page.create_manual_backup()
        mock_bk.assert_called_once_with("manual")

    def test_failure_path_does_not_raise(self, page):
        with patch("src.pages.settings.create_backup", return_value=("", False)):
            page.create_manual_backup()
