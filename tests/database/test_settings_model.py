"""Tests for the Settings model (singleton row #1).

Covers:
  * TestCreateTable     — idempotency, default row inserted, migration safe
  * TestTva             — get default, update + get, fractional, missing
  * TestReceiptNumber   — defaults to 1, update + get
  * TestAllSettings     — returns full dict, fallback when no row
"""

import pytest

from src.database.connection import DatabaseConnection
from src.database.models.settings import (
    create_settings_table,
    get_all_settings,
    get_receipt_number,
    get_tva,
    update_receipt_number,
    update_tva,
)

# ---------------------------------------------------------------------------
# Auto-create the singleton settings row for every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def settings_table(db):
    create_settings_table()


# ===========================================================================
# TestCreateTable
# ===========================================================================


class TestCreateTable:
    def test_idempotent(self):
        create_settings_table()  # second call must not raise

    def test_default_row_created(self):
        row = DatabaseConnection().fetchone("SELECT * FROM settings WHERE id = 1")
        assert row is not None
        assert row["tva"] == 21.0
        assert row["receipt_number"] == 1

    def test_only_one_row(self):
        row = DatabaseConnection().fetchone("SELECT COUNT(*) AS n FROM settings")
        assert row["n"] == 1


# ===========================================================================
# TestTva
# ===========================================================================


class TestTva:
    def test_default_tva(self):
        assert get_tva() == 21.0

    def test_update_and_read_back(self):
        update_tva(19.5)
        assert get_tva() == 19.5

    def test_zero_tva(self):
        update_tva(0.0)
        assert get_tva() == 0.0

    def test_high_tva(self):
        update_tva(99.99)
        assert get_tva() == 99.99

    def test_get_tva_falls_back_when_no_row(self):
        DatabaseConnection().execute("DELETE FROM settings")
        DatabaseConnection().commit()
        assert get_tva() == 21.0


# ===========================================================================
# TestReceiptNumber
# ===========================================================================


class TestReceiptNumber:
    def test_default(self):
        assert get_receipt_number() == 1

    def test_update_and_read_back(self):
        update_receipt_number(42)
        assert get_receipt_number() == 42

    def test_large_value(self):
        update_receipt_number(999_999)
        assert get_receipt_number() == 999_999

    def test_fallback_when_no_row(self):
        DatabaseConnection().execute("DELETE FROM settings")
        DatabaseConnection().commit()
        assert get_receipt_number() == 1


# ===========================================================================
# TestAllSettings
# ===========================================================================


class TestAllSettings:
    def test_default_contents(self):
        row = get_all_settings()
        assert row["id"] == 1
        assert row["tva"] == 21.0
        assert row["receipt_number"] == 1

    def test_after_updates(self):
        update_tva(5.5)
        update_receipt_number(10)
        row = get_all_settings()
        assert row["tva"] == 5.5
        assert row["receipt_number"] == 10

    def test_returns_fallback_when_no_row(self):
        DatabaseConnection().execute("DELETE FROM settings")
        DatabaseConnection().commit()
        row = get_all_settings()
        assert row == {"id": 1, "tva": 21.0, "receipt_number": 1}
