"""Comprehensive tests for the Defects database model.

Covers:
  - TestCreateTable   — idempotency
  - TestAdd           — basic, multiple, count, sequential IDs, reuse after delete
  - TestGetByName     — found / not-found / case-insensitive
  - TestGetById       — found / not-found
  - TestGetAll        — empty, populated, correct structure
  - TestUpdate        — rename unique, same-record no-op, isolation, name freed after update
  - TestDelete        — existing, non-existent (silent), count, list exclusion, isolation
  - TestEdgeCases     — special chars, unicode, very long name, count after mixed ops
"""

import pytest

from src.database.models.defects import (
    add_defect,
    create_defects_table,
    delete_defect,
    get_all_defects,
    get_defect_by_id,
    get_defect_by_name,
    get_defects_count,
    update_defect,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def defects_table(db):
    create_defects_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================


class TestCreateTable:
    def test_create_table_is_idempotent(self):
        create_defects_table()

    def test_table_starts_empty(self):
        assert get_defects_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================


class TestAdd:
    def test_add_one_returns_id(self):
        defect_id = add_defect("Scratch on door")
        assert isinstance(defect_id, int)
        assert defect_id > 0

    def test_add_two_different_defects(self):
        id1 = add_defect("Scratch on door")
        id2 = add_defect("Broken headlight")
        assert id1 != id2
        assert get_defects_count() == 2

    def test_add_increments_count(self):
        add_defect("A")
        add_defect("B")
        add_defect("C")
        assert get_defects_count() == 3

    def test_add_returns_sequential_ids(self):
        id1 = add_defect("First")
        id2 = add_defect("Second")
        assert id2 > id1

    def test_add_same_name_after_delete_is_allowed(self):
        original_id = add_defect("Scratch on door")
        delete_defect(original_id)
        new_id = add_defect("Scratch on door")
        assert new_id != original_id


# ===========================================================================
# TestGetByName
# ===========================================================================


class TestGetByName:
    def test_get_by_name_found(self):
        add_defect("Scratch on door")
        result = get_defect_by_name("Scratch on door")
        assert result is not None
        assert result["defect_name"] == "Scratch on door"

    def test_get_by_name_not_found_returns_none(self):
        assert get_defect_by_name("Nonexistent") is None

    def test_get_by_name_case_insensitive_lower(self):
        add_defect("Scratch on door")
        assert get_defect_by_name("scratch on door") is not None

    def test_get_by_name_case_insensitive_upper(self):
        add_defect("Scratch on door")
        assert get_defect_by_name("SCRATCH ON DOOR") is not None

    def test_get_by_name_case_insensitive_mixed(self):
        add_defect("Broken Headlight")
        assert get_defect_by_name("bRoKeN hEaDlIgHt") is not None

    def test_get_by_name_returns_correct_id(self):
        expected_id = add_defect("Scratch on door")
        result = get_defect_by_name("scratch on door")
        assert result["id"] == expected_id


# ===========================================================================
# TestGetById
# ===========================================================================


class TestGetById:
    def test_get_by_id_found(self):
        defect_id = add_defect("Dent in bumper")
        result = get_defect_by_id(defect_id)
        assert result is not None
        assert result["id"] == defect_id
        assert result["defect_name"] == "Dent in bumper"

    def test_get_by_id_not_found_returns_none(self):
        assert get_defect_by_id(9999) is None


# ===========================================================================
# TestGetAll
# ===========================================================================


class TestGetAll:
    def test_get_all_empty(self):
        assert get_all_defects() == []

    def test_get_all_returns_all_entries(self):
        add_defect("A")
        add_defect("B")
        add_defect("C")
        assert len(get_all_defects()) == 3

    def test_get_all_contains_correct_names(self):
        names = {"Scratch on door", "Dent in bumper", "Broken headlight"}
        for n in names:
            add_defect(n)
        returned = {r["defect_name"] for r in get_all_defects()}
        assert returned == names

    def test_get_all_returns_dicts(self):
        add_defect("Test Defect")
        results = get_all_defects()
        assert isinstance(results[0], dict)
        assert "id" in results[0]
        assert "defect_name" in results[0]


# ===========================================================================
# TestUpdate
# ===========================================================================


class TestUpdate:
    def test_update_to_new_unique_name(self):
        defect_id = add_defect("Old Defect")
        update_defect(defect_id, "New Defect")
        assert get_defect_by_id(defect_id)["defect_name"] == "New Defect"

    def test_update_same_name_on_same_record(self):
        defect_id = add_defect("Scratch on door")
        update_defect(defect_id, "Scratch on door")  # no-op, no error
        assert get_defect_by_id(defect_id)["defect_name"] == "Scratch on door"

    def test_update_does_not_affect_other_records(self):
        id1 = add_defect("Defect A")
        id2 = add_defect("Defect B")
        update_defect(id1, "Defect A Updated")
        assert get_defect_by_id(id2)["defect_name"] == "Defect B"

    def test_update_old_name_is_freed(self):
        defect_id = add_defect("Temp Defect")
        update_defect(defect_id, "Permanent Defect")
        new_id = add_defect("Temp Defect")
        assert new_id != defect_id


# ===========================================================================
# TestDelete
# ===========================================================================


class TestDelete:
    def test_delete_existing(self):
        defect_id = add_defect("Scratch on door")
        delete_defect(defect_id)
        assert get_defect_by_id(defect_id) is None

    def test_delete_reduces_count(self):
        id1 = add_defect("Defect A")
        add_defect("Defect B")
        assert get_defects_count() == 2
        delete_defect(id1)
        assert get_defects_count() == 1

    def test_delete_nonexistent_does_not_raise(self):
        delete_defect(9999)

    def test_delete_removes_from_get_all(self):
        defect_id = add_defect("Scratch on door")
        delete_defect(defect_id)
        names = [r["defect_name"] for r in get_all_defects()]
        assert "Scratch on door" not in names

    def test_delete_only_removes_target(self):
        id1 = add_defect("Defect A")
        id2 = add_defect("Defect B")
        delete_defect(id1)
        assert get_defect_by_id(id2) is not None


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    def test_name_stored_as_given(self):
        defect_id = add_defect("  Padded  ")
        assert get_defect_by_id(defect_id)["defect_name"] == "  Padded  "

    def test_very_long_name(self):
        long_name = "C" * 500
        defect_id = add_defect(long_name)
        assert get_defect_by_id(defect_id)["defect_name"] == long_name

    def test_special_characters(self):
        name = "Zgârietură capotă — adâncime ~2mm (față/spate)"
        defect_id = add_defect(name)
        assert get_defect_by_id(defect_id)["defect_name"] == name

    def test_unicode_name(self):
        name = "Lovitură bara față — oxidat"
        defect_id = add_defect(name)
        assert get_defect_by_id(defect_id)["defect_name"] == name

    def test_count_after_mixed_operations(self):
        add_defect("A")
        id2 = add_defect("B")
        add_defect("C")
        delete_defect(id2)
        add_defect("D")
        assert get_defects_count() == 3
