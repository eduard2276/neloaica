"""Tests for ReceiptsPage — receipts list ordering by date.

BUG  Receipts list not ordered by date
     The receipts list page shows receipts in updated_at / insertion
     order.  It should always show the newest receipt DATE first.
     Fix: apply_filters() in ReceiptsPage must sort by the 'date'
     field (dd.MM.yyyy) descending before calling display_receipts().
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Shared Qt application fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_receipt(rid: int, date: str, status: str = "Ongoing") -> dict:
    """Minimal receipt dict for display_receipts / apply_filters."""
    return {
        "id": rid,
        "client_id": None,
        "car_id": None,
        "client_name": f"Client {rid}",
        "car_model": "Model",
        "plate_number": "XX00TST",
        "vin": "",
        "kilometers": "0",
        "executant_name": "",
        "date": date,
        "estimate_cost": 0.0,
        "estimated_final_date": "",
        "defects": [],
        "discovered_defects": [],
        "parts": [],
        "labor": [],
        "total_labor_cost": 0.0,
        "billable_parts": [],
        "total_parts_cost": 0.0,
        "grand_total": 0.0,
        "status": status,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
    }


# ===========================================================================
# Tests
# ===========================================================================


class TestReceiptsDateOrdering:

    def _make_page(self, receipts: list):
        """Create a ReceiptsPage with the given receipts mocked."""
        from src.pages.receipts.receipts import ReceiptsPage

        with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
            page = ReceiptsPage()
        return page

    def _table_dates(self, page) -> list[str]:
        """Return the list of date strings as shown in the table (col 3)."""
        table = page.receipts_table
        return [table.item(row, 3).text() for row in range(table.rowCount())]

    def test_receipts_sorted_newest_first(self, qapp):
        """Receipts with different dates must be displayed newest-date first,
        regardless of their DB insertion order."""
        receipts = [
            _make_receipt(1, "01.01.2026"),  # January  – oldest
            _make_receipt(2, "15.03.2026"),  # March    – newest
            _make_receipt(3, "01.02.2026"),  # February – middle
        ]
        page = self._make_page(receipts)
        dates = self._table_dates(page)

        assert dates == [
            "15.03.2026",
            "01.02.2026",
            "01.01.2026",
        ], f"Expected newest-first order, got: {dates}."

    def test_receipts_sorted_newest_first_same_year(self, qapp):
        """Multiple receipts within the same year are sorted by date."""
        receipts = [
            _make_receipt(1, "10.10.2025"),
            _make_receipt(2, "01.01.2025"),
            _make_receipt(3, "31.12.2025"),
            _make_receipt(4, "15.06.2025"),
        ]
        page = self._make_page(receipts)
        dates = self._table_dates(page)

        assert dates == [
            "31.12.2025",
            "10.10.2025",
            "15.06.2025",
            "01.01.2025",
        ], f"Unexpected order within same year: {dates}"

    def test_receipts_sorted_across_years(self, qapp):
        """Receipts spanning multiple years are sorted correctly."""
        receipts = [
            _make_receipt(1, "01.01.2024"),
            _make_receipt(2, "01.01.2026"),
            _make_receipt(3, "15.07.2025"),
        ]
        page = self._make_page(receipts)
        dates = self._table_dates(page)

        assert dates == [
            "01.01.2026",
            "15.07.2025",
            "01.01.2024",
        ], f"Cross-year ordering wrong: {dates}"

    def test_receipts_with_invalid_date_dont_crash(self, qapp):
        """Receipts with missing/empty dates must not crash the sort."""
        receipts = [
            _make_receipt(1, ""),
            _make_receipt(2, "07.05.2026"),
            _make_receipt(3, "01.01.2026"),
        ]
        page = self._make_page(receipts)
        dates = self._table_dates(page)
        assert dates[0] == "07.05.2026", f"Valid dates must come before empty: {dates}"

    def test_filter_by_status_preserves_date_order(self, qapp):
        """Date ordering is preserved when a status filter is active."""
        from src.pages.receipts.receipts import ReceiptsPage

        receipts = [
            _make_receipt(1, "01.01.2026", "Done"),
            _make_receipt(2, "15.03.2026", "Ongoing"),
            _make_receipt(3, "01.02.2026", "Ongoing"),
        ]
        with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
            page = ReceiptsPage()

        page.active_status_filter = "Ongoing"
        page.apply_filters()

        dates = self._table_dates(page)
        assert dates == [
            "15.03.2026",
            "01.02.2026",
        ], f"After status filter, remaining rows should still be date-sorted: {dates}"
