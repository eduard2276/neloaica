"""Tests for `PartsSectionWidget` (parts received from client).

Covers:
  * Initial empty state
  * Selecting a part adds it to the list
  * Removing a part returns it to the dropdown
  * parts_changed signal carries id list
  * set_data round-trip
"""

from unittest.mock import patch

import pytest

_PARTS = [
    {"id": 1, "part_name": "Brake Disc"},
    {"id": 2, "part_name": "Oil Filter"},
    {"id": 3, "part_name": "Spark Plug"},
]


@pytest.fixture
def widget(qapp):
    with patch("src.pages.receipts.parts_section.get_all_parts", return_value=list(_PARTS)):
        from src.pages.receipts.parts_section import PartsSectionWidget

        return PartsSectionWidget()


class TestInitialState:
    def test_empty(self, widget):
        assert widget.get_selected_parts() == []

    def test_combo_has_placeholder_plus_parts(self, widget):
        assert widget.part_combo.count() == 4


class TestAddRemove:
    def test_select_combo_adds_to_list(self, widget):
        widget.part_combo.setCurrentIndex(1)
        assert 1 in widget.get_selected_parts()

    def test_remove_brings_back_combo_item(self, widget):
        widget.part_combo.setCurrentIndex(1)
        widget.remove_part(1)
        assert 1 not in widget.get_selected_parts()
        # combo has placeholder + 3 again
        assert widget.part_combo.count() == 4

    def test_add_unknown_id_via_add_part_is_silent(self, widget):
        # widget.add_part requires a dict, so simulate selecting a phantom
        # part that isn't in the catalog
        widget.add_part({"id": 9999, "part_name": "Phantom"})
        assert 9999 in widget.get_selected_parts()


class TestSignal:
    def test_emit_on_add(self, widget):
        captured = []
        widget.parts_changed.connect(lambda ids: captured.append(list(ids)))
        widget.part_combo.setCurrentIndex(1)
        assert captured[-1] == [1]

    def test_emit_on_remove(self, widget):
        widget.part_combo.setCurrentIndex(1)
        captured = []
        widget.parts_changed.connect(lambda ids: captured.append(list(ids)))
        widget.remove_part(1)
        assert captured[-1] == []


class TestSetData:
    def test_round_trip(self, widget):
        with patch("src.pages.receipts.parts_section.get_all_parts", return_value=list(_PARTS)):
            widget.set_data([2, 3])
        assert sorted(widget.get_selected_parts()) == [2, 3]
