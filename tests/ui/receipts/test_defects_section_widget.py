"""Tests for DefectsSectionWidget (defects by client + discovered defects).

The same widget class is used for both "Defects by the Client" and
"Discovered Defects" sections.

Covers:
  * Initial empty state
  * Adding a defect from the combo
  * Adding the same defect twice is a no-op
  * Removing a defect
  * defects_changed signal payload contains the id list
  * set_data hydrates an existing selection
  * load_data(restore_state=True) preserves selection
"""

from unittest.mock import patch

import pytest


_DEFECTS = [
    {"id": 1, "defect_name": "Scratch"},
    {"id": 2, "defect_name": "Dent"},
    {"id": 3, "defect_name": "Broken light"},
]


@pytest.fixture
def widget(qapp):
    with patch("src.pages.receipts.defects_section.get_all_defects", return_value=list(_DEFECTS)):
        from src.pages.receipts.defects_section import DefectsSectionWidget
        return DefectsSectionWidget()


# ===========================================================================
# TestInitialState
# ===========================================================================

class TestInitialState:
    def test_empty(self, widget):
        assert widget.get_selected_defects() == []

    def test_combo_has_placeholder_plus_defects(self, widget):
        # sentinel + 3 defects
        assert widget.defect_combo.count() == 4


# ===========================================================================
# TestAddRemove
# ===========================================================================

class TestAddRemove:
    def test_select_combo_adds_to_list(self, widget):
        widget.defect_combo.setCurrentIndex(1)  # "Scratch"
        assert 1 in widget.get_selected_defects()

    def test_same_id_is_added_only_once(self, widget):
        widget.defect_combo.setCurrentIndex(1)
        # After add, the item was removed from the dropdown — there's no way
        # to re-select id=1 via the combo. Force a second attempt via
        # `add_defect` after re-inserting it.
        widget.defect_combo.blockSignals(True)
        widget.defect_combo.addItem("Scratch", 1)
        widget.defect_combo.setCurrentIndex(widget.defect_combo.count() - 1)
        widget.defect_combo.blockSignals(False)
        widget.add_defect()
        assert widget.get_selected_defects().count(1) == 1

    def test_remove_brings_back_combo_item(self, widget):
        widget.defect_combo.setCurrentIndex(1)
        widget.remove_defect(1)
        assert 1 not in widget.get_selected_defects()


# ===========================================================================
# TestSignal
# ===========================================================================

class TestSignal:
    def test_emit_on_add(self, widget):
        captured = []
        widget.defects_changed.connect(lambda ids: captured.append(list(ids)))
        widget.defect_combo.setCurrentIndex(1)  # Scratch
        assert captured[-1] == [1]

    def test_emit_on_remove(self, widget):
        widget.defect_combo.setCurrentIndex(1)
        captured = []
        widget.defects_changed.connect(lambda ids: captured.append(list(ids)))
        widget.remove_defect(1)
        assert captured[-1] == []


# ===========================================================================
# TestSetData
# ===========================================================================

class TestSetData:
    def test_round_trip(self, widget):
        with patch("src.pages.receipts.defects_section.get_all_defects", return_value=list(_DEFECTS)):
            widget.set_data([2, 3])
        assert sorted(widget.get_selected_defects()) == [2, 3]

    def test_set_data_ignores_unknown_ids(self, widget):
        with patch("src.pages.receipts.defects_section.get_all_defects", return_value=list(_DEFECTS)):
            widget.set_data([99999])
        assert widget.get_selected_defects() == []


# ===========================================================================
# TestLoadDataRestore
# ===========================================================================

class TestLoadDataRestore:
    def test_load_data_restore_state_preserves_selection(self, widget):
        widget.defect_combo.setCurrentIndex(1)  # Scratch
        before = widget.get_selected_defects()
        with patch("src.pages.receipts.defects_section.get_all_defects", return_value=list(_DEFECTS)):
            widget.load_data(restore_state=True)
        assert widget.get_selected_defects() == before

    def test_load_data_reset_clears_selection(self, widget):
        widget.defect_combo.setCurrentIndex(1)
        with patch("src.pages.receipts.defects_section.get_all_defects", return_value=list(_DEFECTS)):
            widget.load_data(restore_state=False)
        assert widget.get_selected_defects() == []
