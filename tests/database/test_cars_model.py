"""Comprehensive tests for the Cars database model.

Covers:
  * TestCreateTable     — idempotency
  * TestAdd             — happy path, returns id, default kilometers
  * TestUniqueVin       — VIN must be unique; raises IntegrityError
  * TestGetById         — found / not-found, JOIN brings client_name
  * TestGetAll          — empty, ordering by (model, plate_number)
  * TestUpdate          — full update, partial via update_car_kilometers
  * TestDelete          — existing / non-existent
  * TestForeignKeyCascade — deleting a client cascades to their cars
  * TestCount           — empty / populated
  * TestMockData        — idempotent seeding
"""

import sqlite3
import pytest

from src.database.models.clients import create_clients_table, add_client, delete_client
from src.database.models.cars import (
    create_cars_table,
    add_car,
    get_all_cars,
    get_car_by_id,
    update_car,
    delete_car,
    get_cars_count,
    update_car_kilometers,
    populate_cars_mock_data,
)


# ---------------------------------------------------------------------------
# Fresh tables for each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def car_tables(db):
    create_clients_table()
    create_cars_table()


@pytest.fixture
def client_id():
    return add_client("Owner", "One", "Addr")


# ===========================================================================
# TestCreateTable
# ===========================================================================

class TestCreateTable:
    def test_idempotent(self):
        create_cars_table()  # second call must not raise

    def test_empty_at_start(self):
        assert get_cars_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================

class TestAdd:
    def test_add_returns_id(self, client_id):
        cid = add_car(client_id, "B-123-ABC", "WVWZZZ3CZWE123456", "Golf", 12000)
        assert isinstance(cid, int) and cid > 0

    def test_add_persists_all_fields(self, client_id):
        cid = add_car(client_id, "B-123-ABC", "WVWZZZ3CZWE123456", "Golf", 12000)
        row = get_car_by_id(cid)
        assert row["plate_number"] == "B-123-ABC"
        assert row["vin"] == "WVWZZZ3CZWE123456"
        assert row["model"] == "Golf"
        assert row["kilometers"] == 12000
        assert row["client_id"] == client_id

    def test_default_kilometers_is_zero(self, client_id):
        cid = add_car(client_id, "B-1", "V" * 17, "Model", )
        assert get_car_by_id(cid)["kilometers"] == 0

    def test_count_after_add(self, client_id):
        add_car(client_id, "P1", "A" * 17, "M1", 1)
        add_car(client_id, "P2", "B" * 17, "M2", 2)
        assert get_cars_count() == 2


# ===========================================================================
# TestUniqueVin
# ===========================================================================

class TestUniqueVin:
    def test_duplicate_vin_raises(self, client_id):
        vin = "DUPLICATEVIN12345"
        add_car(client_id, "P1", vin, "M1", 1)
        with pytest.raises(sqlite3.IntegrityError):
            add_car(client_id, "P2", vin, "M2", 2)


# ===========================================================================
# TestGetById
# ===========================================================================

class TestGetById:
    def test_includes_client_name(self, client_id):
        cid = add_car(client_id, "P1", "V" * 17, "M1", 1)
        row = get_car_by_id(cid)
        assert row["client_name"] == "Owner One"

    def test_missing_returns_none(self):
        assert get_car_by_id(99999) is None


# ===========================================================================
# TestGetAll
# ===========================================================================

class TestGetAll:
    def test_empty(self):
        assert get_all_cars() == []

    def test_orders_by_model_then_plate(self, client_id):
        add_car(client_id, "ZZ-1", "A" * 17, "BMW", 1)
        add_car(client_id, "AA-1", "B" * 17, "BMW", 2)
        add_car(client_id, "MM-1", "C" * 17, "Audi", 3)
        rows = get_all_cars()
        ordering = [(r["model"], r["plate_number"]) for r in rows]
        assert ordering == [
            ("Audi", "MM-1"),
            ("BMW", "AA-1"),
            ("BMW", "ZZ-1"),
        ]


# ===========================================================================
# TestUpdate
# ===========================================================================

class TestUpdate:
    def test_update_all_fields(self, client_id):
        cid = add_car(client_id, "P1", "A" * 17, "Old", 100)
        new_client = add_client("Other", "Owner", "addr")
        update_car(cid, new_client, "P9", "B" * 17, "New", 999)
        row = get_car_by_id(cid)
        assert row["client_id"] == new_client
        assert row["plate_number"] == "P9"
        assert row["vin"] == "B" * 17
        assert row["model"] == "New"
        assert row["kilometers"] == 999

    def test_update_kilometers_only(self, client_id):
        cid = add_car(client_id, "P", "V" * 17, "M", 100)
        update_car_kilometers(cid, 500)
        assert get_car_by_id(cid)["kilometers"] == 500

    def test_update_unknown_id_is_no_op(self, client_id):
        update_car_kilometers(9999, 5)
        update_car(9999, client_id, "X-1", "Y" * 17, "M", 1)
        assert get_cars_count() == 0


# ===========================================================================
# TestDelete
# ===========================================================================

class TestDelete:
    def test_delete_existing(self, client_id):
        cid = add_car(client_id, "P", "V" * 17, "M", 1)
        delete_car(cid)
        assert get_car_by_id(cid) is None

    def test_delete_missing_is_silent(self):
        delete_car(99)
        assert get_cars_count() == 0


# ===========================================================================
# TestForeignKeyCascade
# ===========================================================================

class TestForeignKeyCascade:
    def test_deleting_client_deletes_their_cars(self):
        cid = add_client("Cascade", "Test", "")
        add_car(cid, "P1", "A" * 17, "M", 1)
        add_car(cid, "P2", "B" * 17, "M", 2)
        delete_client(cid)
        assert get_cars_count() == 0


# ===========================================================================
# TestMockData
# ===========================================================================

class TestMockData:
    def test_seed_idempotent(self):
        from src.database.models.clients import populate_clients_mock_data
        populate_clients_mock_data()
        populate_cars_mock_data()
        n1 = get_cars_count()
        populate_cars_mock_data()
        assert get_cars_count() == n1
