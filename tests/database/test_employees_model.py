"""Comprehensive tests for the Employees database model.

Employees are unique by the COMBINATION of (first_name, last_name).
  - Two people can share a first name (Ion Popescu vs Ion Ionescu).
  - Two people can share a last name (Ion Popescu vs Maria Popescu).
  - The pair must be unique.

Covers:
  - TestCreateTable       — idempotency
  - TestAdd               — basic, multiple, count, sequential IDs, reuse after delete
  - TestGetByName         — found / not-found / case-insensitive / partial match disambiguation
  - TestGetById           — found / not-found
  - TestGetAll            — empty, populated, correct structure, ordered
  - TestGetForDropdown    — format, ordering
  - TestUpdate            — rename to unique, same-record no-op, isolation, name freed
  - TestDelete            — existing, non-existent (silent), count, isolation
  - TestEdgeCases         — special chars, unicode, very long names, mixed-op count
"""

import pytest

from src.database.models.employees import (
    create_employees_table,
    add_employee,
    get_all_employees,
    get_employee_by_id,
    get_employee_by_name,
    get_employees_for_dropdown,
    update_employee,
    delete_employee,
    get_employees_count,
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def employees_table(db):
    create_employees_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================

class TestCreateTable:
    def test_create_table_is_idempotent(self):
        create_employees_table()

    def test_table_starts_empty(self):
        assert get_employees_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================

class TestAdd:
    def test_add_one_returns_id(self):
        emp_id = add_employee("Ion", "Popescu")
        assert isinstance(emp_id, int)
        assert emp_id > 0

    def test_add_two_different_employees(self):
        id1 = add_employee("Ion", "Popescu")
        id2 = add_employee("Maria", "Ionescu")
        assert id1 != id2
        assert get_employees_count() == 2

    def test_add_same_first_name_different_last_name_is_allowed(self):
        add_employee("Ion", "Popescu")
        add_employee("Ion", "Ionescu")
        assert get_employees_count() == 2

    def test_add_same_last_name_different_first_name_is_allowed(self):
        add_employee("Ion", "Popescu")
        add_employee("Maria", "Popescu")
        assert get_employees_count() == 2

    def test_add_increments_count(self):
        add_employee("A", "X")
        add_employee("B", "Y")
        add_employee("C", "Z")
        assert get_employees_count() == 3

    def test_add_returns_sequential_ids(self):
        id1 = add_employee("First", "Employee")
        id2 = add_employee("Second", "Employee")
        assert id2 > id1

    def test_add_same_pair_after_delete_is_allowed(self):
        original_id = add_employee("Ion", "Popescu")
        delete_employee(original_id)
        new_id = add_employee("Ion", "Popescu")
        assert new_id != original_id


# ===========================================================================
# TestGetByName
# ===========================================================================

class TestGetByName:
    def test_get_by_name_found(self):
        add_employee("Ion", "Popescu")
        result = get_employee_by_name("Ion", "Popescu")
        assert result is not None
        assert result["first_name"] == "Ion"
        assert result["last_name"] == "Popescu"

    def test_get_by_name_not_found_returns_none(self):
        assert get_employee_by_name("Ghost", "Person") is None

    def test_get_by_name_case_insensitive_lower(self):
        add_employee("Ion", "Popescu")
        assert get_employee_by_name("ion", "popescu") is not None

    def test_get_by_name_case_insensitive_upper(self):
        add_employee("Ion", "Popescu")
        assert get_employee_by_name("ION", "POPESCU") is not None

    def test_get_by_name_case_insensitive_mixed(self):
        add_employee("Maria", "Ionescu")
        assert get_employee_by_name("mArIa", "IoNeScU") is not None

    def test_get_by_name_returns_correct_id(self):
        expected_id = add_employee("Ion", "Popescu")
        result = get_employee_by_name("ion", "popescu")
        assert result["id"] == expected_id

    def test_get_by_name_does_not_match_partial(self):
        """(Ion, Pop) must NOT match (Ion, Popescu)."""
        add_employee("Ion", "Popescu")
        assert get_employee_by_name("Ion", "Pop") is None

    def test_get_by_name_same_first_different_last(self):
        add_employee("Ion", "Popescu")
        id2 = add_employee("Ion", "Ionescu")
        result = get_employee_by_name("Ion", "Ionescu")
        assert result is not None
        assert result["id"] == id2

    def test_get_by_name_returns_only_exact_pair(self):
        """Ensure only the matching pair is returned when both share a first name."""
        id1 = add_employee("Ion", "Popescu")
        id2 = add_employee("Ion", "Ionescu")
        r1 = get_employee_by_name("Ion", "Popescu")
        r2 = get_employee_by_name("Ion", "Ionescu")
        assert r1["id"] == id1
        assert r2["id"] == id2


# ===========================================================================
# TestGetById
# ===========================================================================

class TestGetById:
    def test_get_by_id_found(self):
        emp_id = add_employee("Ion", "Popescu")
        result = get_employee_by_id(emp_id)
        assert result is not None
        assert result["id"] == emp_id
        assert result["first_name"] == "Ion"
        assert result["last_name"] == "Popescu"

    def test_get_by_id_not_found_returns_none(self):
        assert get_employee_by_id(9999) is None


# ===========================================================================
# TestGetAll
# ===========================================================================

class TestGetAll:
    def test_get_all_empty(self):
        assert get_all_employees() == []

    def test_get_all_returns_all_entries(self):
        add_employee("Ion", "Popescu")
        add_employee("Maria", "Ionescu")
        add_employee("Andrei", "Stan")
        assert len(get_all_employees()) == 3

    def test_get_all_contains_correct_data(self):
        add_employee("Ion", "Popescu")
        add_employee("Maria", "Ionescu")
        names = {(e["first_name"], e["last_name"]) for e in get_all_employees()}
        assert ("Ion", "Popescu") in names
        assert ("Maria", "Ionescu") in names

    def test_get_all_returns_dicts_with_expected_keys(self):
        add_employee("Ion", "Popescu")
        result = get_all_employees()[0]
        assert isinstance(result, dict)
        assert "id" in result
        assert "first_name" in result
        assert "last_name" in result

    def test_get_all_ordered_by_last_name_then_first_name(self):
        add_employee("Maria", "Zeescu")
        add_employee("Ion", "Aaronescu")
        add_employee("Bogdan", "Aaronescu")
        results = get_all_employees()
        # Aaronescu should come first; within Aaronescu: Bogdan before Ion
        assert results[0]["last_name"] == "Aaronescu"
        assert results[0]["first_name"] == "Bogdan"
        assert results[1]["first_name"] == "Ion"
        assert results[2]["last_name"] == "Zeescu"


# ===========================================================================
# TestGetForDropdown
# ===========================================================================

class TestGetForDropdown:
    def test_dropdown_returns_combined_name(self):
        add_employee("Ion", "Popescu")
        results = get_employees_for_dropdown()
        assert len(results) == 1
        assert results[0]["name"] == "Ion Popescu"

    def test_dropdown_ordered_by_last_name(self):
        add_employee("Maria", "Zeescu")
        add_employee("Ion", "Aaronescu")
        results = get_employees_for_dropdown()
        assert results[0]["name"] == "Ion Aaronescu"
        assert results[1]["name"] == "Maria Zeescu"

    def test_dropdown_includes_id(self):
        emp_id = add_employee("Ion", "Popescu")
        results = get_employees_for_dropdown()
        assert results[0]["id"] == emp_id

    def test_dropdown_empty_when_no_employees(self):
        assert get_employees_for_dropdown() == []


# ===========================================================================
# TestUpdate
# ===========================================================================

class TestUpdate:
    def test_update_to_new_unique_name(self):
        emp_id = add_employee("Ion", "Popescu")
        update_employee(emp_id, "Ion", "Ionescu")
        result = get_employee_by_id(emp_id)
        assert result["last_name"] == "Ionescu"

    def test_update_same_name_on_same_record(self):
        emp_id = add_employee("Ion", "Popescu")
        update_employee(emp_id, "Ion", "Popescu")  # no-op, no error
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "Ion"
        assert result["last_name"] == "Popescu"

    def test_update_does_not_affect_other_records(self):
        id1 = add_employee("Ion", "Popescu")
        id2 = add_employee("Maria", "Ionescu")
        update_employee(id1, "Ion Updated", "Popescu")
        result2 = get_employee_by_id(id2)
        assert result2["first_name"] == "Maria"
        assert result2["last_name"] == "Ionescu"

    def test_update_old_name_is_freed(self):
        emp_id = add_employee("Temp", "Name")
        update_employee(emp_id, "Permanent", "Name")
        # "Temp Name" pair is now free
        new_id = add_employee("Temp", "Name")
        assert new_id != emp_id

    def test_update_first_name_only(self):
        emp_id = add_employee("Ion", "Popescu")
        update_employee(emp_id, "George", "Popescu")
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "George"
        assert result["last_name"] == "Popescu"

    def test_update_last_name_only(self):
        emp_id = add_employee("Ion", "Popescu")
        update_employee(emp_id, "Ion", "Ionescu")
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "Ion"
        assert result["last_name"] == "Ionescu"


# ===========================================================================
# TestDelete
# ===========================================================================

class TestDelete:
    def test_delete_existing(self):
        emp_id = add_employee("Ion", "Popescu")
        delete_employee(emp_id)
        assert get_employee_by_id(emp_id) is None

    def test_delete_reduces_count(self):
        id1 = add_employee("Ion", "Popescu")
        add_employee("Maria", "Ionescu")
        assert get_employees_count() == 2
        delete_employee(id1)
        assert get_employees_count() == 1

    def test_delete_nonexistent_does_not_raise(self):
        delete_employee(9999)

    def test_delete_removes_from_get_all(self):
        emp_id = add_employee("Ion", "Popescu")
        delete_employee(emp_id)
        pairs = [(e["first_name"], e["last_name"]) for e in get_all_employees()]
        assert ("Ion", "Popescu") not in pairs

    def test_delete_only_removes_target(self):
        id1 = add_employee("Ion", "Popescu")
        id2 = add_employee("Maria", "Ionescu")
        delete_employee(id1)
        assert get_employee_by_id(id2) is not None


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    def test_name_stored_as_given(self):
        emp_id = add_employee("  Ion  ", "  Popescu  ")
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "  Ion  "
        assert result["last_name"] == "  Popescu  "

    def test_very_long_names(self):
        first = "I" * 300
        last = "P" * 300
        emp_id = add_employee(first, last)
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == first
        assert result["last_name"] == last

    def test_special_characters(self):
        emp_id = add_employee("Ioăn-Aureliu", "Pîrîianu-Blănaru")
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "Ioăn-Aureliu"

    def test_unicode_names(self):
        emp_id = add_employee("Дмитрий", "Иванов")
        result = get_employee_by_id(emp_id)
        assert result["first_name"] == "Дмитрий"
        assert result["last_name"] == "Иванов"

    def test_count_after_mixed_operations(self):
        id1 = add_employee("A", "X")
        id2 = add_employee("B", "Y")
        id3 = add_employee("C", "Z")
        delete_employee(id2)
        add_employee("D", "W")
        assert get_employees_count() == 3
