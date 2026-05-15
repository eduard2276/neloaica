"""Comprehensive tests for the Receipts database model.

Covers:
  - TestCreateTable                    — idempotency
  - TestAddReceipt                     — basic add, returns ID, increments count
  - TestGetReceiptById                 — found / not-found
  - TestGetAllReceipts                 — empty, populated, JSON fields decoded
  - TestUpdateReceipt                  — updates fields, updated_at changes
  - TestUpdateReceiptStatus            — status-only update
  - TestDeleteReceipt                  — existing, non-existent (silent), count
  - TestGetReceiptsCount               — empty, after add, after delete
  - TestGetReceiptByPlateAndDate       — core duplicate-check function:
        found / not-found / case-insensitive plate / exclude_id same /
        exclude_id different / empty plate / empty date / both empty
  - TestDuplicateCheckEdgeCases        — same plate different date, different plate same date
"""

import pytest

from src.database.models.receipts import (
    create_receipts_table,
    add_receipt,
    get_all_receipts,
    get_receipt_by_id,
    get_receipt_by_plate_and_date,
    update_receipt,
    update_receipt_status,
    delete_receipt,
    get_receipts_count,
)
from src.database.models.clients import create_clients_table
from src.database.models.cars import create_cars_table

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = {
    "client_id": None,
    "car_id": None,
    "client_name": "Ion Popescu",
    "model": "Dacia Logan",
    "plate_number": "B123ABC",
    "vin": "1HGCM82633A004352",
    "kilometers": "50000",
    "executant_name": "Gelu Mecanic",
    "date": "08.05.2026",
    "estimate_cost": 500.0,
    "estimated_final_date": "10.05.2026",
    "defects": [],
    "discovered_defects": [],
    "parts": [],
    "labor": [],
    "total_labor_cost": 200.0,
    "billable_parts": [],
    "total_parts_cost": 100.0,
    "grand_total": 300.0,
    "status": "Ongoing",
}


def _receipt(**overrides) -> dict:
    """Return a receipt dict derived from _BASE with any field overridden."""
    r = dict(_BASE)
    r.update(overrides)
    return r


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def receipts_table(db):
    """Create prerequisite tables then the receipts table in the fresh in-memory DB.

    The receipts table has FK references to clients and cars, so those tables
    must exist first when PRAGMA foreign_keys = ON.
    """
    create_clients_table()
    create_cars_table()
    create_receipts_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================

class TestCreateTable:
    def test_create_table_is_idempotent(self):
        create_receipts_table()

    def test_table_starts_empty(self):
        assert get_receipts_count() == 0


# ===========================================================================
# TestAddReceipt
# ===========================================================================

class TestAddReceipt:
    def test_add_returns_integer_id(self):
        rid = add_receipt(_receipt())
        assert isinstance(rid, int)
        assert rid > 0

    def test_add_increments_count(self):
        add_receipt(_receipt())
        add_receipt(_receipt(date="09.05.2026"))
        assert get_receipts_count() == 2

    def test_add_sequential_ids(self):
        id1 = add_receipt(_receipt(date="07.05.2026"))
        id2 = add_receipt(_receipt(date="08.05.2026"))
        assert id2 > id1

    def test_add_stores_plate_number(self):
        rid = add_receipt(_receipt(plate_number="CJ99ZZZ"))
        r = get_receipt_by_id(rid)
        assert r["plate_number"] == "CJ99ZZZ"

    def test_add_stores_date(self):
        rid = add_receipt(_receipt(date="15.06.2026"))
        r = get_receipt_by_id(rid)
        assert r["date"] == "15.06.2026"

    def test_add_stores_client_name(self):
        rid = add_receipt(_receipt(client_name="Maria Ionescu"))
        r = get_receipt_by_id(rid)
        assert r["client_name"] == "Maria Ionescu"

    def test_add_stores_grand_total(self):
        rid = add_receipt(_receipt(grand_total=750.0))
        r = get_receipt_by_id(rid)
        assert r["grand_total"] == 750.0

    def test_add_default_status_is_ongoing(self):
        rid = add_receipt(_receipt())
        r = get_receipt_by_id(rid)
        assert r["status"] == "Ongoing"


# ===========================================================================
# TestGetReceiptById
# ===========================================================================

class TestGetReceiptById:
    def test_get_by_id_found(self):
        rid = add_receipt(_receipt())
        r = get_receipt_by_id(rid)
        assert r is not None
        assert r["id"] == rid

    def test_get_by_id_not_found_returns_none(self):
        assert get_receipt_by_id(9999) is None

    def test_get_by_id_decodes_json_fields(self):
        rid = add_receipt(_receipt(defects=[1, 2, 3]))
        r = get_receipt_by_id(rid)
        assert r["defects"] == [1, 2, 3]


# ===========================================================================
# TestGetAllReceipts
# ===========================================================================

class TestGetAllReceipts:
    def test_get_all_empty(self):
        assert get_all_receipts() == []

    def test_get_all_returns_all(self):
        add_receipt(_receipt(date="07.05.2026"))
        add_receipt(_receipt(date="08.05.2026"))
        add_receipt(_receipt(date="09.05.2026"))
        assert len(get_all_receipts()) == 3

    def test_get_all_returns_dicts_with_id(self):
        add_receipt(_receipt())
        results = get_all_receipts()
        assert "id" in results[0]

    def test_get_all_decodes_json_fields(self):
        add_receipt(_receipt(labor=[10, 20]))
        results = get_all_receipts()
        assert results[0]["labor"] == [10, 20]


# ===========================================================================
# TestUpdateReceipt
# ===========================================================================

class TestUpdateReceipt:
    def test_update_changes_plate_number(self):
        rid = add_receipt(_receipt(plate_number="B123ABC"))
        update_receipt(rid, _receipt(plate_number="CJ55NEW"))
        assert get_receipt_by_id(rid)["plate_number"] == "CJ55NEW"

    def test_update_changes_status(self):
        rid = add_receipt(_receipt(status="Ongoing"))
        update_receipt(rid, _receipt(status="Done"))
        assert get_receipt_by_id(rid)["status"] == "Done"

    def test_update_does_not_affect_other_records(self):
        id1 = add_receipt(_receipt(plate_number="AAA111", date="07.05.2026"))
        id2 = add_receipt(_receipt(plate_number="BBB222", date="08.05.2026"))
        update_receipt(id1, _receipt(plate_number="AAA111", client_name="Updated"))
        assert get_receipt_by_id(id2)["plate_number"] == "BBB222"


# ===========================================================================
# TestUpdateReceiptStatus
# ===========================================================================

class TestUpdateReceiptStatus:
    def test_status_update_only(self):
        rid = add_receipt(_receipt(status="Ongoing"))
        update_receipt_status(rid, "Done")
        assert get_receipt_by_id(rid)["status"] == "Done"

    def test_status_update_does_not_change_other_fields(self):
        rid = add_receipt(_receipt(plate_number="B123ABC"))
        update_receipt_status(rid, "Done")
        assert get_receipt_by_id(rid)["plate_number"] == "B123ABC"


# ===========================================================================
# TestDeleteReceipt
# ===========================================================================

class TestDeleteReceipt:
    def test_delete_existing(self):
        rid = add_receipt(_receipt())
        delete_receipt(rid)
        assert get_receipt_by_id(rid) is None

    def test_delete_reduces_count(self):
        id1 = add_receipt(_receipt(date="07.05.2026"))
        add_receipt(_receipt(date="08.05.2026"))
        delete_receipt(id1)
        assert get_receipts_count() == 1

    def test_delete_nonexistent_does_not_raise(self):
        delete_receipt(9999)

    def test_delete_only_removes_target(self):
        id1 = add_receipt(_receipt(date="07.05.2026"))
        id2 = add_receipt(_receipt(date="08.05.2026"))
        delete_receipt(id1)
        assert get_receipt_by_id(id2) is not None


# ===========================================================================
# TestGetReceiptsCount
# ===========================================================================

class TestGetReceiptsCount:
    def test_count_zero_initially(self):
        assert get_receipts_count() == 0

    def test_count_after_adds(self):
        add_receipt(_receipt(date="07.05.2026"))
        add_receipt(_receipt(date="08.05.2026"))
        assert get_receipts_count() == 2

    def test_count_after_delete(self):
        id1 = add_receipt(_receipt(date="07.05.2026"))
        add_receipt(_receipt(date="08.05.2026"))
        delete_receipt(id1)
        assert get_receipts_count() == 1


# ===========================================================================
# TestGetReceiptByPlateAndDate — core duplicate-check
# ===========================================================================

class TestGetReceiptByPlateAndDate:
    def test_returns_none_when_no_receipts(self):
        assert get_receipt_by_plate_and_date("B123ABC", "08.05.2026") is None

    def test_returns_receipt_when_exact_match(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026")
        assert result is not None

    def test_match_returns_receipt_id(self):
        rid = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026")
        assert result["id"] == rid

    def test_match_returns_plate_number(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026")
        assert result["plate_number"] == "B123ABC"

    def test_match_returns_date(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026")
        assert result["date"] == "08.05.2026"

    def test_plate_match_is_case_insensitive(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("b123abc", "08.05.2026") is not None

    def test_plate_match_case_upper(self):
        add_receipt(_receipt(plate_number="cj55xyz", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("CJ55XYZ", "08.05.2026") is not None

    def test_no_match_when_date_differs(self):
        add_receipt(_receipt(plate_number="B123ABC", date="07.05.2026"))
        assert get_receipt_by_plate_and_date("B123ABC", "08.05.2026") is None

    def test_no_match_when_plate_differs(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("CJ99ZZZ", "08.05.2026") is None

    def test_empty_plate_returns_none(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("", "08.05.2026") is None

    def test_empty_date_returns_none(self):
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("B123ABC", "") is None

    def test_both_empty_returns_none(self):
        assert get_receipt_by_plate_and_date("", "") is None

    # --- exclude_id ----------------------------------------------------------

    def test_exclude_id_same_record_returns_none(self):
        """Editing a receipt: it must NOT conflict with itself."""
        rid = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026", exclude_id=rid)
        assert result is None

    def test_exclude_id_different_record_still_detected(self):
        """A different record with the same plate+date must still be found."""
        id1 = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        id2 = add_receipt(_receipt(plate_number="B123ABC", date="09.05.2026"))
        # editing id2, checking against id1's plate+date — should find id1
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026", exclude_id=id2)
        assert result is not None
        assert result["id"] == id1

    def test_exclude_id_none_behaves_like_no_exclusion(self):
        rid = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026", exclude_id=None)
        assert result is not None
        assert result["id"] == rid


# ===========================================================================
# TestDuplicateCheckEdgeCases
# ===========================================================================

class TestDuplicateCheckEdgeCases:
    def test_same_plate_different_dates_no_conflict(self):
        """The same car on two different days → not a duplicate."""
        add_receipt(_receipt(plate_number="B123ABC", date="07.05.2026"))
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        assert get_receipts_count() == 2  # both exist, no error
        assert get_receipt_by_plate_and_date("B123ABC", "09.05.2026") is None

    def test_different_plates_same_date_no_conflict(self):
        """Two different cars on the same day → not a duplicate."""
        add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        add_receipt(_receipt(plate_number="CJ99ZZZ", date="08.05.2026"))
        assert get_receipts_count() == 2
        assert get_receipt_by_plate_and_date("IS55ABC", "08.05.2026") is None

    def test_multiple_receipts_only_matching_one_returned(self):
        id1 = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        add_receipt(_receipt(plate_number="B123ABC", date="09.05.2026"))
        add_receipt(_receipt(plate_number="CJ99ZZZ", date="08.05.2026"))
        result = get_receipt_by_plate_and_date("B123ABC", "08.05.2026")
        assert result["id"] == id1

    def test_plate_with_spaces_exact_match(self):
        """Plates with spaces are stored and matched exactly (after LOWER)."""
        add_receipt(_receipt(plate_number="B 123 ABC", date="08.05.2026"))
        assert get_receipt_by_plate_and_date("B 123 ABC", "08.05.2026") is not None
        assert get_receipt_by_plate_and_date("B123ABC", "08.05.2026") is None

    def test_after_delete_plate_date_is_free(self):
        rid = add_receipt(_receipt(plate_number="B123ABC", date="08.05.2026"))
        delete_receipt(rid)
        assert get_receipt_by_plate_and_date("B123ABC", "08.05.2026") is None
