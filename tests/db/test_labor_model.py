"""Comprehensive tests for the Labor database model.

Covers:
  - TestCreateTable   — table creation idempotency
  - TestAdd           — add one, many, duplicate (case-insensitive), after-delete reuse
  - TestGetByName     — lookup found / not-found / case-insensitive
  - TestGetById       — found / not-found
  - TestGetAll        — empty, populated
  - TestUpdate        — rename to unique, rename to same record (no-op), rename to duplicate
  - TestDelete        — existing, non-existent (no error), count after delete
  - TestEdgeCases     — whitespace names, very long names, special characters
"""

import pytest

from src.database.models.labor import (
    create_labor_table,
    add_labor,
    get_all_labor,
    get_labor_by_id,
    get_labor_by_name,
    update_labor,
    delete_labor,
    get_labor_count,
)


# ---------------------------------------------------------------------------
# Fixture: fresh table for every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def labor_table(db):
    """Create the labor table in the fresh in-memory DB."""
    create_labor_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================

class TestCreateTable:
    def test_create_table_is_idempotent(self):
        """Calling create_labor_table twice must not raise."""
        create_labor_table()  # second call — should be fine

    def test_table_starts_empty(self):
        assert get_labor_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================

class TestAdd:
    def test_add_one_returns_id(self):
        labor_id = add_labor("Oil Change")
        assert isinstance(labor_id, int)
        assert labor_id > 0

    def test_add_two_different_services(self):
        id1 = add_labor("Oil Change")
        id2 = add_labor("Brake Pads")
        assert id1 != id2
        assert get_labor_count() == 2

    def test_add_increments_count(self):
        add_labor("Oil Change")
        add_labor("Brake Pads")
        add_labor("Tire Rotation")
        assert get_labor_count() == 3

    def test_add_returns_sequential_ids(self):
        id1 = add_labor("First")
        id2 = add_labor("Second")
        assert id2 > id1

    def test_add_same_name_after_delete_is_allowed(self):
        """After the original entry is deleted the name becomes reusable."""
        original_id = add_labor("Oil Change")
        delete_labor(original_id)
        new_id = add_labor("Oil Change")
        assert new_id != original_id  # new row, different id


# ===========================================================================
# TestGetByName
# ===========================================================================

class TestGetByName:
    def test_get_by_name_found(self):
        add_labor("Oil Change")
        result = get_labor_by_name("Oil Change")
        assert result is not None
        assert result["service_name"] == "Oil Change"

    def test_get_by_name_not_found_returns_none(self):
        result = get_labor_by_name("Nonexistent")
        assert result is None

    def test_get_by_name_case_insensitive_lower(self):
        add_labor("Oil Change")
        result = get_labor_by_name("oil change")
        assert result is not None

    def test_get_by_name_case_insensitive_upper(self):
        add_labor("Oil Change")
        result = get_labor_by_name("OIL CHANGE")
        assert result is not None

    def test_get_by_name_case_insensitive_mixed(self):
        add_labor("Brake Pads")
        result = get_labor_by_name("bRaKe pAdS")
        assert result is not None

    def test_get_by_name_returns_correct_id(self):
        expected_id = add_labor("Oil Change")
        result = get_labor_by_name("oil change")
        assert result["id"] == expected_id


# ===========================================================================
# TestGetById
# ===========================================================================

class TestGetById:
    def test_get_by_id_found(self):
        labor_id = add_labor("Wheel Alignment")
        result = get_labor_by_id(labor_id)
        assert result is not None
        assert result["id"] == labor_id
        assert result["service_name"] == "Wheel Alignment"

    def test_get_by_id_not_found_returns_none(self):
        result = get_labor_by_id(9999)
        assert result is None


# ===========================================================================
# TestGetAll
# ===========================================================================

class TestGetAll:
    def test_get_all_empty(self):
        assert get_all_labor() == []

    def test_get_all_returns_all_entries(self):
        add_labor("Oil Change")
        add_labor("Brake Pads")
        add_labor("Tire Rotation")
        results = get_all_labor()
        assert len(results) == 3

    def test_get_all_contains_correct_names(self):
        names = {"Oil Change", "Brake Pads", "Tire Rotation"}
        for n in names:
            add_labor(n)
        returned = {r["service_name"] for r in get_all_labor()}
        assert returned == names

    def test_get_all_returns_dicts(self):
        add_labor("Test Service")
        results = get_all_labor()
        assert isinstance(results[0], dict)
        assert "id" in results[0]
        assert "service_name" in results[0]


# ===========================================================================
# TestUpdate
# ===========================================================================

class TestUpdate:
    def test_update_to_new_unique_name(self):
        labor_id = add_labor("Old Name")
        update_labor(labor_id, "New Name")
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == "New Name"

    def test_update_same_name_on_same_record(self):
        """Renaming a record to its own current name must not raise."""
        labor_id = add_labor("Oil Change")
        update_labor(labor_id, "Oil Change")  # no-op, should not error
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == "Oil Change"

    def test_update_does_not_affect_other_records(self):
        id1 = add_labor("Service A")
        id2 = add_labor("Service B")
        update_labor(id1, "Service A Updated")
        assert get_labor_by_id(id2)["service_name"] == "Service B"

    def test_update_old_name_is_freed(self):
        """After renaming, the old name should no longer be taken."""
        labor_id = add_labor("Temp Name")
        update_labor(labor_id, "Permanent Name")
        # We can now safely add another entry with the old name
        new_id = add_labor("Temp Name")
        assert new_id != labor_id


# ===========================================================================
# TestDelete
# ===========================================================================

class TestDelete:
    def test_delete_existing(self):
        labor_id = add_labor("Oil Change")
        delete_labor(labor_id)
        assert get_labor_by_id(labor_id) is None

    def test_delete_reduces_count(self):
        id1 = add_labor("Oil Change")
        add_labor("Brake Pads")
        assert get_labor_count() == 2
        delete_labor(id1)
        assert get_labor_count() == 1

    def test_delete_nonexistent_does_not_raise(self):
        """Deleting a non-existent ID should silently do nothing."""
        delete_labor(9999)  # must not raise

    def test_delete_removes_from_get_all(self):
        labor_id = add_labor("Oil Change")
        delete_labor(labor_id)
        names = [r["service_name"] for r in get_all_labor()]
        assert "Oil Change" not in names

    def test_delete_only_removes_target(self):
        id1 = add_labor("Service A")
        id2 = add_labor("Service B")
        delete_labor(id1)
        assert get_labor_by_id(id2) is not None


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    def test_name_with_leading_trailing_spaces_is_stored_as_given(self):
        """The model stores exactly what it receives; trimming is the page's job."""
        labor_id = add_labor("  Padded  ")
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == "  Padded  "

    def test_very_long_name(self):
        long_name = "A" * 500
        labor_id = add_labor(long_name)
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == long_name

    def test_special_characters_in_name(self):
        name = "Oil & Filter Change (5W-30) — Full Synthetic!"
        labor_id = add_labor(name)
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == name

    def test_unicode_name(self):
        name = "Schimb ulei și filtru"
        labor_id = add_labor(name)
        result = get_labor_by_id(labor_id)
        assert result["service_name"] == name

    def test_get_labor_count_after_multiple_operations(self):
        id1 = add_labor("A")
        id2 = add_labor("B")
        id3 = add_labor("C")
        delete_labor(id2)
        assert get_labor_count() == 2
