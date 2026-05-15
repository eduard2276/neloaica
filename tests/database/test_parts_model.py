"""Comprehensive tests for the Parts database model.

Covers:
  - TestCreateTable   — idempotency
  - TestAdd           — basic add, multiple, count increment, sequential IDs, reuse after delete
  - TestGetByName     — found / not-found / case-insensitive variants
  - TestGetById       — found / not-found
  - TestGetAll        — empty, populated, returns dicts
  - TestUpdate        — rename to unique, same-record no-op, isolation
  - TestDelete        — existing, non-existent (silent), count, list membership
  - TestEdgeCases     — special chars, unicode, very long name
"""

import pytest

from src.database.models.parts import (
    create_parts_table,
    add_part,
    get_all_parts,
    get_part_by_id,
    get_part_by_name,
    update_part,
    delete_part,
    get_parts_count,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def parts_table(db):
    create_parts_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================

class TestCreateTable:
    def test_create_table_is_idempotent(self):
        create_parts_table()

    def test_table_starts_empty(self):
        assert get_parts_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================

class TestAdd:
    def test_add_one_returns_id(self):
        part_id = add_part("Brake Disc")
        assert isinstance(part_id, int)
        assert part_id > 0

    def test_add_two_different_parts(self):
        id1 = add_part("Brake Disc")
        id2 = add_part("Air Filter")
        assert id1 != id2
        assert get_parts_count() == 2

    def test_add_increments_count(self):
        add_part("A")
        add_part("B")
        add_part("C")
        assert get_parts_count() == 3

    def test_add_returns_sequential_ids(self):
        id1 = add_part("First Part")
        id2 = add_part("Second Part")
        assert id2 > id1

    def test_add_same_name_after_delete_is_allowed(self):
        original_id = add_part("Brake Disc")
        delete_part(original_id)
        new_id = add_part("Brake Disc")
        assert new_id != original_id


# ===========================================================================
# TestGetByName
# ===========================================================================

class TestGetByName:
    def test_get_by_name_found(self):
        add_part("Brake Disc")
        result = get_part_by_name("Brake Disc")
        assert result is not None
        assert result["part_name"] == "Brake Disc"

    def test_get_by_name_not_found_returns_none(self):
        result = get_part_by_name("Nonexistent")
        assert result is None

    def test_get_by_name_case_insensitive_lower(self):
        add_part("Brake Disc")
        assert get_part_by_name("brake disc") is not None

    def test_get_by_name_case_insensitive_upper(self):
        add_part("Brake Disc")
        assert get_part_by_name("BRAKE DISC") is not None

    def test_get_by_name_case_insensitive_mixed(self):
        add_part("Air Filter")
        assert get_part_by_name("aIr fIlTeR") is not None

    def test_get_by_name_returns_correct_id(self):
        expected_id = add_part("Brake Disc")
        result = get_part_by_name("brake disc")
        assert result["id"] == expected_id


# ===========================================================================
# TestGetById
# ===========================================================================

class TestGetById:
    def test_get_by_id_found(self):
        part_id = add_part("Spark Plug")
        result = get_part_by_id(part_id)
        assert result is not None
        assert result["id"] == part_id
        assert result["part_name"] == "Spark Plug"

    def test_get_by_id_not_found_returns_none(self):
        assert get_part_by_id(9999) is None


# ===========================================================================
# TestGetAll
# ===========================================================================

class TestGetAll:
    def test_get_all_empty(self):
        assert get_all_parts() == []

    def test_get_all_returns_all_entries(self):
        add_part("A")
        add_part("B")
        add_part("C")
        assert len(get_all_parts()) == 3

    def test_get_all_contains_correct_names(self):
        names = {"Brake Disc", "Air Filter", "Spark Plug"}
        for n in names:
            add_part(n)
        returned = {r["part_name"] for r in get_all_parts()}
        assert returned == names

    def test_get_all_returns_dicts(self):
        add_part("Test Part")
        results = get_all_parts()
        assert isinstance(results[0], dict)
        assert "id" in results[0]
        assert "part_name" in results[0]


# ===========================================================================
# TestUpdate
# ===========================================================================

class TestUpdate:
    def test_update_to_new_unique_name(self):
        part_id = add_part("Old Name")
        update_part(part_id, "New Name")
        assert get_part_by_id(part_id)["part_name"] == "New Name"

    def test_update_same_name_on_same_record(self):
        part_id = add_part("Brake Disc")
        update_part(part_id, "Brake Disc")  # same name, should not error
        assert get_part_by_id(part_id)["part_name"] == "Brake Disc"

    def test_update_does_not_affect_other_records(self):
        id1 = add_part("Part A")
        id2 = add_part("Part B")
        update_part(id1, "Part A Updated")
        assert get_part_by_id(id2)["part_name"] == "Part B"

    def test_update_old_name_is_freed(self):
        part_id = add_part("Temp Name")
        update_part(part_id, "Permanent Name")
        new_id = add_part("Temp Name")
        assert new_id != part_id


# ===========================================================================
# TestDelete
# ===========================================================================

class TestDelete:
    def test_delete_existing(self):
        part_id = add_part("Brake Disc")
        delete_part(part_id)
        assert get_part_by_id(part_id) is None

    def test_delete_reduces_count(self):
        id1 = add_part("Part A")
        add_part("Part B")
        assert get_parts_count() == 2
        delete_part(id1)
        assert get_parts_count() == 1

    def test_delete_nonexistent_does_not_raise(self):
        delete_part(9999)

    def test_delete_removes_from_get_all(self):
        part_id = add_part("Brake Disc")
        delete_part(part_id)
        names = [r["part_name"] for r in get_all_parts()]
        assert "Brake Disc" not in names

    def test_delete_only_removes_target(self):
        id1 = add_part("Part A")
        id2 = add_part("Part B")
        delete_part(id1)
        assert get_part_by_id(id2) is not None


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    def test_name_stored_as_given(self):
        part_id = add_part("  Padded  ")
        assert get_part_by_id(part_id)["part_name"] == "  Padded  "

    def test_very_long_name(self):
        long_name = "B" * 500
        part_id = add_part(long_name)
        assert get_part_by_id(part_id)["part_name"] == long_name

    def test_special_characters(self):
        name = "Disc frână față (320mm) — stânga/dreapta"
        part_id = add_part(name)
        assert get_part_by_id(part_id)["part_name"] == name

    def test_unicode_name(self):
        name = "Filtru ulei 5W-40 синтетика"
        part_id = add_part(name)
        assert get_part_by_id(part_id)["part_name"] == name

    def test_count_after_mixed_operations(self):
        id1 = add_part("A")
        id2 = add_part("B")
        id3 = add_part("C")
        delete_part(id2)
        add_part("D")
        assert get_parts_count() == 3
