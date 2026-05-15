"""Comprehensive tests for the Clients database model.

Covers:
  * TestCreateTable     — idempotency, empty table after creation
  * TestAdd             — add, returns id, supports many, optional address
  * TestGetById         — found / not-found
  * TestGetAll          — empty / ordered by (last_name, first_name)
  * TestUpdate          — update all fields, partial update, missing record
  * TestDelete          — existing / non-existent
  * TestCount           — empty, populated
  * TestDropdownQuery   — concatenated `name`, ordering, empty
  * TestEdgeCases       — empty address, very long names, special chars
  * TestMockData        — populate_clients_mock_data is idempotent
"""

import pytest

from src.database.models.clients import (
    add_client,
    create_clients_table,
    delete_client,
    get_all_clients,
    get_client_by_id,
    get_clients_count,
    get_clients_for_dropdown,
    populate_clients_mock_data,
    update_client,
)

# ---------------------------------------------------------------------------
# Autouse: every test gets a fresh `clients` table
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clients_table(db):
    create_clients_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================


class TestCreateTable:
    def test_create_table_is_idempotent(self):
        create_clients_table()  # second call must not raise

    def test_table_starts_empty(self):
        assert get_clients_count() == 0


# ===========================================================================
# TestAdd
# ===========================================================================


class TestAdd:
    def test_add_returns_positive_id(self):
        cid = add_client("John", "Doe", "1 Main St")
        assert isinstance(cid, int) and cid > 0

    def test_add_persists(self):
        cid = add_client("Jane", "Roe", "2 Elm Ave")
        row = get_client_by_id(cid)
        assert row is not None
        assert row["first_name"] == "Jane"
        assert row["last_name"] == "Roe"
        assert row["address"] == "2 Elm Ave"

    def test_add_many_assigns_unique_ids(self):
        ids = {add_client(f"F{i}", f"L{i}", f"{i} St") for i in range(20)}
        assert len(ids) == 20

    def test_add_with_default_address(self):
        cid = add_client("Alex", "Smith")
        row = get_client_by_id(cid)
        assert row["address"] == ""

    def test_count_after_add(self):
        add_client("A", "B", "x")
        add_client("C", "D", "y")
        assert get_clients_count() == 2


# ===========================================================================
# TestGetById
# ===========================================================================


class TestGetById:
    def test_get_existing(self):
        cid = add_client("First", "Last", "Addr")
        row = get_client_by_id(cid)
        assert row["id"] == cid
        assert row["first_name"] == "First"

    def test_get_missing_returns_none(self):
        assert get_client_by_id(9999) is None


# ===========================================================================
# TestGetAll
# ===========================================================================


class TestGetAll:
    def test_empty(self):
        assert get_all_clients() == []

    def test_ordered_by_last_then_first(self):
        add_client("Zara", "Adams", "")
        add_client("Bob", "Adams", "")
        add_client("Charlie", "Brown", "")
        names = [(c["last_name"], c["first_name"]) for c in get_all_clients()]
        assert names == [("Adams", "Bob"), ("Adams", "Zara"), ("Brown", "Charlie")]


# ===========================================================================
# TestUpdate
# ===========================================================================


class TestUpdate:
    def test_update_all_fields(self):
        cid = add_client("Old", "Name", "Old Addr")
        update_client(cid, "New", "Name2", "New Addr")
        row = get_client_by_id(cid)
        assert row["first_name"] == "New"
        assert row["last_name"] == "Name2"
        assert row["address"] == "New Addr"

    def test_update_default_address(self):
        cid = add_client("A", "B", "before")
        update_client(cid, "A", "B")  # address default ""
        assert get_client_by_id(cid)["address"] == ""

    def test_update_missing_row_is_no_op(self):
        update_client(9999, "Nobody", "There", "Nowhere")
        assert get_clients_count() == 0


# ===========================================================================
# TestDelete
# ===========================================================================


class TestDelete:
    def test_delete_existing(self):
        cid = add_client("A", "B", "")
        delete_client(cid)
        assert get_client_by_id(cid) is None

    def test_delete_missing_is_silent(self):
        delete_client(99)  # must not raise
        assert get_clients_count() == 0

    def test_count_after_delete(self):
        cid = add_client("A", "B", "")
        add_client("C", "D", "")
        delete_client(cid)
        assert get_clients_count() == 1


# ===========================================================================
# TestDropdownQuery
# ===========================================================================


class TestDropdownQuery:
    def test_empty_dropdown(self):
        assert get_clients_for_dropdown() == []

    def test_concatenated_name(self):
        cid = add_client("Jane", "Smith", "")
        rows = get_clients_for_dropdown()
        assert rows == [{"id": cid, "name": "Jane Smith"}]

    def test_dropdown_ordering(self):
        add_client("Zara", "Brown", "")
        add_client("Anne", "Adams", "")
        add_client("Bob", "Adams", "")
        names = [r["name"] for r in get_clients_for_dropdown()]
        assert names == ["Anne Adams", "Bob Adams", "Zara Brown"]


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    def test_empty_address_default(self):
        cid = add_client("F", "L", "")
        assert get_client_by_id(cid)["address"] == ""

    def test_very_long_name(self):
        long_name = "X" * 500
        cid = add_client(long_name, "Last", "")
        assert get_client_by_id(cid)["first_name"] == long_name

    def test_special_characters(self):
        cid = add_client("Anne-Marie", "O'Connor", "1 Smith & Co.")
        row = get_client_by_id(cid)
        assert row["first_name"] == "Anne-Marie"
        assert row["last_name"] == "O'Connor"
        assert row["address"] == "1 Smith & Co."

    def test_unicode_name(self):
        cid = add_client("Ștefan", "Mărgărit", "Strada Aleea")
        row = get_client_by_id(cid)
        assert row["first_name"] == "Ștefan"
        assert row["last_name"] == "Mărgărit"


# ===========================================================================
# TestMockData
# ===========================================================================


class TestMockData:
    def test_first_call_seeds_rows(self):
        populate_clients_mock_data()
        assert get_clients_count() > 0

    def test_idempotent(self):
        populate_clients_mock_data()
        n1 = get_clients_count()
        populate_clients_mock_data()
        n2 = get_clients_count()
        assert n1 == n2
