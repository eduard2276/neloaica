"""Tests for ReceiptsPage — sort order dropdown.

The receipts list must expose a "Sort by" combo box with six options:
  - "Date: Newest first"       → descending date order  (default)
  - "Date: Oldest first"       → ascending  date order
  - "Grand Total: High to low" → descending grand_total
  - "Grand Total: Low to high" → ascending  grand_total
  - "Client: A to Z"           → ascending  client_name
  - "Client: Z to A"           → descending client_name
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QComboBox

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


def _make_receipt(
    rid: int, date: str, status: str = "Ongoing", grand_total: float = 0.0, client_name: str = ""
) -> dict:
    """Minimal receipt dict suitable for ReceiptsPage."""
    return {
        "id": rid,
        "client_id": None,
        "car_id": None,
        "client_name": client_name or f"Client {rid}",
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
        "grand_total": grand_total,
        "status": status,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
    }


def _make_page(receipts: list):
    """Create a ReceiptsPage with the given receipts mocked."""
    from src.pages.receipts.receipts import ReceiptsPage

    with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
        page = ReceiptsPage()
    return page


def _table_dates(page) -> list[str]:
    """Return date strings from column 3 of the receipts table."""
    table = page.receipts_table
    return [table.item(row, 3).text() for row in range(table.rowCount())]


def _table_clients(page) -> list[str]:
    """Return client name strings from column 1 of the receipts table."""
    table = page.receipts_table
    return [table.item(row, 1).text() for row in range(table.rowCount())]


def _table_totals_raw(page) -> list[float]:
    """Return grand-total floats from column 4 (strips ' Lei' suffix)."""
    table = page.receipts_table
    result = []
    for row in range(table.rowCount()):
        text = table.item(row, 4).text()  # e.g. "1 500.00 Lei"
        numeric = text.replace(" Lei", "").replace(" ", "")  # "1500.00"
        result.append(float(numeric))
    return result


SORT_OPTS = [
    "Date: Newest first",
    "Date: Oldest first",
    "Grand Total: High to low",
    "Grand Total: Low to high",
    "Client: A to Z",
    "Client: Z to A",
]

RECEIPTS_MIXED = [
    _make_receipt(1, "01.01.2026"),  # oldest
    _make_receipt(2, "15.03.2026"),  # newest
    _make_receipt(3, "01.02.2026"),  # middle
]


# ===========================================================================
# Widget presence
# ===========================================================================


class TestSortDropdownPresence:

    def test_sort_combo_exists(self, qapp):
        """ReceiptsPage must have a 'sort_combo' attribute."""
        page = _make_page(RECEIPTS_MIXED)
        assert hasattr(
            page, "sort_combo"
        ), "ReceiptsPage must expose a 'sort_combo' widget for sort control."

    def test_sort_combo_is_combo_box(self, qapp):
        """sort_combo must be a QComboBox (or subclass)."""
        page = _make_page(RECEIPTS_MIXED)
        assert isinstance(page.sort_combo, QComboBox), "'sort_combo' must be a QComboBox instance."

    def test_sort_combo_has_all_six_options(self, qapp):
        """The combo must contain all six sort options."""
        page = _make_page(RECEIPTS_MIXED)
        texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        for opt in SORT_OPTS:
            assert opt in texts, f"'{opt}' missing from sort_combo. Found: {texts}"

    def test_sort_combo_has_exactly_six_options(self, qapp):
        """The combo must have exactly 6 options — no extras."""
        page = _make_page(RECEIPTS_MIXED)
        assert (
            page.sort_combo.count() == 6
        ), f"sort_combo must have 6 items, found {page.sort_combo.count()}"

    def test_sort_combo_default_is_date_newest_first(self, qapp):
        """The default selected option must be 'Date: Newest first'."""
        page = _make_page(RECEIPTS_MIXED)
        assert page.sort_combo.currentText() == "Date: Newest first", (
            f"Default sort must be 'Date: Newest first', " f"got: '{page.sort_combo.currentText()}'"
        )


# ===========================================================================
# Sorting behaviour
# ===========================================================================


class TestSortBehaviour:

    # ── Date sorts ───────────────────────────────────────────────────────

    def test_date_newest_first_is_default_order(self, qapp):
        """On page load, receipts appear newest-date first (default)."""
        page = _make_page(RECEIPTS_MIXED)
        assert _table_dates(page) == [
            "15.03.2026",
            "01.02.2026",
            "01.01.2026",
        ], "Default order should be newest-first."

    def test_date_oldest_first_reverses_order(self, qapp):
        """Selecting 'Date: Oldest first' reverses the display order."""
        page = _make_page(RECEIPTS_MIXED)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))

        assert _table_dates(page) == [
            "01.01.2026",
            "01.02.2026",
            "15.03.2026",
        ], "'Date: Oldest first' must give ascending date order."

    def test_switching_back_to_date_newest_first(self, qapp):
        """Switching back to 'Date: Newest first' restores descending order."""
        page = _make_page(RECEIPTS_MIXED)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Newest first"))

        assert _table_dates(page) == [
            "15.03.2026",
            "01.02.2026",
            "01.01.2026",
        ], "After switching back to 'Date: Newest first' table must be descending."

    def test_date_oldest_first_with_same_year(self, qapp):
        """'Date: Oldest first' sorts correctly within the same year."""
        receipts = [
            _make_receipt(1, "31.12.2025"),
            _make_receipt(2, "01.01.2025"),
            _make_receipt(3, "15.06.2025"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))

        assert _table_dates(page) == ["01.01.2025", "15.06.2025", "31.12.2025"]

    def test_date_oldest_first_across_years(self, qapp):
        """'Date: Oldest first' sorts correctly across multiple years."""
        receipts = [
            _make_receipt(1, "01.01.2026"),
            _make_receipt(2, "15.07.2025"),
            _make_receipt(3, "01.01.2024"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))

        assert _table_dates(page) == ["01.01.2024", "15.07.2025", "01.01.2026"]

    # ── Grand Total sorts ────────────────────────────────────────────────

    def test_grand_total_high_to_low(self, qapp):
        """'Grand Total: High to low' sorts receipts descending by grand_total."""
        receipts = [
            _make_receipt(1, "01.01.2026", grand_total=100.0),
            _make_receipt(2, "01.02.2026", grand_total=500.0),
            _make_receipt(3, "01.03.2026", grand_total=250.0),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Grand Total: High to low"))

        totals = _table_totals_raw(page)
        assert totals == [
            500.0,
            250.0,
            100.0,
        ], f"'Grand Total: High to low' must give descending totals. Got: {totals}"

    def test_grand_total_low_to_high(self, qapp):
        """'Grand Total: Low to high' sorts receipts ascending by grand_total."""
        receipts = [
            _make_receipt(1, "01.01.2026", grand_total=300.0),
            _make_receipt(2, "01.02.2026", grand_total=50.0),
            _make_receipt(3, "01.03.2026", grand_total=750.0),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Grand Total: Low to high"))

        totals = _table_totals_raw(page)
        assert totals == [
            50.0,
            300.0,
            750.0,
        ], f"'Grand Total: Low to high' must give ascending totals. Got: {totals}"

    def test_grand_total_equal_values_stable(self, qapp):
        """Receipts with equal grand totals must all appear in the table."""
        receipts = [
            _make_receipt(1, "01.01.2026", grand_total=200.0),
            _make_receipt(2, "01.02.2026", grand_total=200.0),
            _make_receipt(3, "01.03.2026", grand_total=200.0),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Grand Total: High to low"))

        assert page.receipts_table.rowCount() == 3

    # ── Client sorts ─────────────────────────────────────────────────────

    def test_client_a_to_z(self, qapp):
        """'Client: A to Z' sorts receipts ascending by client name."""
        receipts = [
            _make_receipt(1, "01.01.2026", client_name="Zara"),
            _make_receipt(2, "01.02.2026", client_name="Alice"),
            _make_receipt(3, "01.03.2026", client_name="Mihai"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Client: A to Z"))

        clients = _table_clients(page)
        assert clients == [
            "Alice",
            "Mihai",
            "Zara",
        ], f"'Client: A to Z' must give ascending client names. Got: {clients}"

    def test_client_z_to_a(self, qapp):
        """'Client: Z to A' sorts receipts descending by client name."""
        receipts = [
            _make_receipt(1, "01.01.2026", client_name="Alice"),
            _make_receipt(2, "01.02.2026", client_name="Zara"),
            _make_receipt(3, "01.03.2026", client_name="Mihai"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Client: Z to A"))

        clients = _table_clients(page)
        assert clients == [
            "Zara",
            "Mihai",
            "Alice",
        ], f"'Client: Z to A' must give descending client names. Got: {clients}"

    def test_client_sort_is_case_insensitive(self, qapp):
        """Client sort ignores case."""
        receipts = [
            _make_receipt(1, "01.01.2026", client_name="zara"),
            _make_receipt(2, "01.02.2026", client_name="Alice"),
            _make_receipt(3, "01.03.2026", client_name="Mihai"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Client: A to Z"))

        clients = _table_clients(page)
        assert clients == [
            "Alice",
            "Mihai",
            "zara",
        ], f"Client sort must be case-insensitive. Got: {clients}"


# ===========================================================================
# Interaction with other filters
# ===========================================================================


class TestSortWithFilters:

    def test_date_oldest_first_combined_with_status_filter(self, qapp):
        """Sort order is applied after status filter."""
        from src.pages.receipts.receipts import ReceiptsPage

        receipts = [
            _make_receipt(1, "01.01.2026", "Done"),
            _make_receipt(2, "15.03.2026", "Ongoing"),
            _make_receipt(3, "01.02.2026", "Ongoing"),
            _make_receipt(4, "10.04.2026", "Ongoing"),
        ]
        with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
            page = ReceiptsPage()

        page.active_status_filter = "Ongoing"
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))

        dates = _table_dates(page)
        assert dates == [
            "01.02.2026",
            "15.03.2026",
            "10.04.2026",
        ], f"'Date: Oldest first' after status filter should give ascending Ongoing receipts. Got: {dates}"

    def test_date_oldest_first_combined_with_search(self, qapp):
        """Sort order is preserved when a search filter is active."""
        from src.pages.receipts.receipts import ReceiptsPage

        receipts = [
            _make_receipt(1, "01.01.2026"),
            _make_receipt(2, "15.03.2026"),
            _make_receipt(3, "01.02.2026"),
        ]
        receipts[0]["client_name"] = "Alpha Client"
        receipts[1]["client_name"] = "Alpha Client"
        receipts[2]["client_name"] = "Beta Client"

        with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
            page = ReceiptsPage()

        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))
        page.search_input.setText("alpha")

        dates = _table_dates(page)
        assert dates == [
            "01.01.2026",
            "15.03.2026",
        ], f"Search + 'Date: Oldest first' should give ascending order for matching rows. Got: {dates}"

    def test_invalid_dates_stay_at_end_in_oldest_first(self, qapp):
        """Receipts with empty/invalid dates fall to the END in 'Date: Oldest first' mode."""
        receipts = [
            _make_receipt(1, ""),
            _make_receipt(2, "07.05.2026"),
            _make_receipt(3, "01.01.2026"),
        ]
        page = _make_page(receipts)
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Date: Oldest first"))

        dates = _table_dates(page)
        assert dates.index("01.01.2026") < dates.index(
            ""
        ), f"In 'Date: Oldest first', valid dates must precede empty/invalid ones. Got: {dates}"
        assert dates.index("07.05.2026") < dates.index(
            ""
        ), f"In 'Date: Oldest first', valid dates must precede empty/invalid ones. Got: {dates}"

    def test_grand_total_sort_combined_with_status_filter(self, qapp):
        """Grand total sort applies after status filter."""
        from src.pages.receipts.receipts import ReceiptsPage

        receipts = [
            _make_receipt(1, "01.01.2026", "Done", grand_total=999.0),
            _make_receipt(2, "01.02.2026", "Ongoing", grand_total=100.0),
            _make_receipt(3, "01.03.2026", "Ongoing", grand_total=500.0),
        ]
        with patch("src.pages.receipts.receipts.get_all_receipts", return_value=receipts):
            page = ReceiptsPage()

        page.active_status_filter = "Ongoing"
        combo_texts = [page.sort_combo.itemText(i) for i in range(page.sort_combo.count())]
        page.sort_combo.setCurrentIndex(combo_texts.index("Grand Total: High to low"))

        totals = _table_totals_raw(page)
        assert totals == [
            500.0,
            100.0,
        ], f"Grand Total sort after status filter wrong. Got: {totals}"
