# Neloaica — Test Suite

This folder contains the automated test suite for the Neloaica desktop
application. As of the latest run there are **838 tests, all passing**.

The suite is layered to mirror `src/`:

| Layer          | Tests against                       | Where           |
| -------------- | ----------------------------------- | --------------- |
| `unit/`        | pure-Python helpers (no DB, no Qt)  | `tests/unit/`     |
| `database/`    | SQLite model layer (in-memory DB)   | `tests/database/` |
| `services/`    | Excel template engine + backup      | `tests/services/` |
| `ui/`          | PySide6 widgets / pages / dialogs   | `tests/ui/`       |

The runtime stack is:
* `pytest 9.x`
* `pytest-qt 4.x` (only for parts that need a `QApplication`)
* `pytest-cov 7.x` (optional, for coverage reports)
* `openpyxl 3.x`, `PySide6 6.x`

---

## 1. Folder structure

```
tests/
├── README.md                       # this file
├── conftest.py                     # shared `qapp` fixture (session-scoped)
│
├── unit/                           # Pure logic — no DB, no Qt
│   └── test_paths.py               # src/paths.py — get_app_dir / get_bundle_dir
│
├── database/                       # Model layer — uses an in-memory SQLite DB
│   ├── conftest.py                 # `db` fixture (singleton reset + :memory: DB)
│   ├── test_connection.py          # DatabaseConnection (singleton, FK, row factory)
│   ├── test_clients_model.py       # clients CRUD + dropdown query
│   ├── test_cars_model.py          # cars CRUD + UNIQUE VIN + ON DELETE CASCADE
│   ├── test_settings_model.py      # settings (TVA, receipt_number, fallback)
│   ├── test_labor_model.py         # labor CRUD + case-insensitive lookup
│   ├── test_parts_model.py         # parts CRUD + case-insensitive lookup
│   ├── test_defects_model.py       # defects CRUD + case-insensitive lookup
│   ├── test_employees_model.py     # employees CRUD + UNIQUE (first, last) pair
│   └── test_receipts_model.py      # receipts CRUD + JSON columns + plate/date lookup
│
├── services/                       # Service layer — DB mocked
│   ├── test_backup.py              # create / cleanup / list / restore / daily check
│   └── excel/
│       ├── test_export.py          # header fields, sections, receipt # increment
│       ├── test_section_expansion.py     # defects + client-parts row inserts
│       ├── test_disc_section_expansion.py# discovered defects row inserts
│       ├── test_layout_invariants.py     # label shifts, grand-total row, estimates
│       └── test_combinations.py    # parametrised sweep across many sizes
│
└── ui/                             # PySide6 — DB/services mocked
    ├── test_main_window.py         # title + minimum size
    ├── test_widgets.py             # NoScrollComboBox / SpinBox / DoubleSpinBox
    ├── test_utils.py               # show_warning / show_info / show_critical
    ├── test_theme.py               # ThemeManager singleton + style generators
    │
    ├── pages/                      # Catalog CRUD pages
    │   ├── test_clients_page.py    # ClientDialog validation + page filtering
    │   ├── test_cars_page.py       # CarDialog (plate / VIN / km) + UNIQUE VIN
    │   ├── test_settings_page.py   # TVA filter, receipt-# filter, save validation
    │   └── test_duplicate_guard.py # duplicate prevention across all catalog pages
    │
    └── receipts/                   # Receipt form + sub-widgets
        ├── test_receipt_form.py             # combo refresh on tab show
        ├── test_receipt_form_full.py        # load_for_new / edit, format_price, reset
        ├── test_receipt_info_widget.py      # client→car cascade, km format, signals
        ├── test_estimates_section.py        # cost formatter, date picker, set_data
        ├── test_defects_section_widget.py   # add/remove, signal payload, set_data
        ├── test_parts_section_widget.py     # add/remove, signal payload, set_data
        ├── test_labor_section_widget.py     # cost format, signal (ids, total)
        ├── test_billable_parts_widget.py    # units * price math, total, signal
        ├── test_receipts_list.py            # default date sort + invalid dates
        ├── test_receipts_sort.py            # 6 sort modes + filter interaction
        ├── test_receipt_duplicate_guard.py  # save/generate plate+date uniqueness
        └── test_section_inline_add_duplicate.py  # ➕ buttons respect catalog dedup
```

---

## 2. How to run

```powershell
# all tests
python -m pytest tests -q

# by category
python -m pytest tests/database -q
python -m pytest tests/services -q
python -m pytest tests/ui -q
python -m pytest tests/unit -q

# a single file or class
python -m pytest tests/database/test_clients_model.py -v
python -m pytest tests/ui/pages/test_cars_page.py::TestCarDialogValidation -v

# with coverage (requires pytest-cov)
python -m pytest tests --cov=src --cov-report=term-missing
```

The Excel and PySide6 tests are slower (~50 s total) because they really
construct workbooks / widgets. Pure DB and unit tests finish in well under
a second each.

---

## 3. Shared fixtures

### `qapp` — `tests/conftest.py`

A session-scoped `QApplication`. Any test that constructs a Qt widget should
declare `qapp` as a fixture parameter. Without it, the second test that
touches PySide6 will crash because Qt requires exactly one `QApplication`
per process.

```python
def test_something(qapp):
    from src.widgets.combo_box import NoScrollComboBox
    cb = NoScrollComboBox()
    ...
```

### `db` — `tests/database/conftest.py`

A function-scoped, in-memory SQLite database that completely bypasses the
real `neloaica.db`:

```python
def _make_in_memory_db():
    DatabaseConnection._instance = None
    DatabaseConnection._connection = None
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    instance = object.__new__(DatabaseConnection)
    instance._connection = conn
    DatabaseConnection._instance = instance
    return instance
```

Use it in model tests; tables are **not** auto-created so each test
explicitly calls `create_*_table()` for the entities it needs. This keeps
the schema-creation paths tested too.

```python
@pytest.fixture(autouse=True)
def labor_table(db):
    create_labor_table()
```

### `tmp_dirs` — `tests/services/test_backup.py`

Per-test temporary directory plus monkey-patched `BACKUPS_DIR` and
`get_database_path`. Lets the backup service be exercised without ever
touching the real working tree.

---

## 4. Test conventions

* Test files are `test_*.py`; classes are `TestXxx`; methods `test_xxx`.
* Tests are grouped into classes (`TestSaveValidation`, `TestKilometers`, …)
  so failures are localized in the output.
* DB / file / message-box calls in UI tests are **always** mocked. No test
  ever opens a real modal dialog, prints to stdout, or writes to the user
  filesystem outside of `tmp_path`.
* Each test asserts one observable behaviour. Multi-assertion tests are
  reserved for related invariants (e.g. all six PIESE table column headers).
* Tests inside a feature folder use only feature-relevant mocks. For example
  `tests/ui/receipts/` never mocks the DB connection itself; it patches the
  imported model functions inside the page's module (`patch("src.pages.receipts.parts_section.get_all_parts", …)`).

---

## 5. What is covered, by source file

| Source                                            | Test file(s)                                              |
| ------------------------------------------------- | --------------------------------------------------------- |
| `src/paths.py`                                    | `unit/test_paths.py`                                      |
| `src/utils.py`                                    | `ui/test_utils.py`                                        |
| `src/widgets/combo_box.py`                        | `ui/test_widgets.py`                                      |
| `src/styles/theme_manager.py`, `styles/colors.py` | `ui/test_theme.py`                                        |
| `src/database/connection.py`                      | `database/test_connection.py`                             |
| `src/database/models/clients.py`                  | `database/test_clients_model.py`                          |
| `src/database/models/cars.py`                     | `database/test_cars_model.py`                             |
| `src/database/models/settings.py`                 | `database/test_settings_model.py`                         |
| `src/database/models/labor.py`                    | `database/test_labor_model.py`                            |
| `src/database/models/parts.py`                    | `database/test_parts_model.py`                            |
| `src/database/models/defects.py`                  | `database/test_defects_model.py`                          |
| `src/database/models/employees.py`                | `database/test_employees_model.py`                        |
| `src/database/models/receipts.py`                 | `database/test_receipts_model.py`                         |
| `src/services/excel_export.py`                    | all of `services/excel/`                                  |
| `src/services/backup.py`                          | `services/test_backup.py`                                 |
| `src/pages/clients.py`                            | `ui/pages/test_clients_page.py`, `ui/pages/test_duplicate_guard.py` |
| `src/pages/cars.py`                               | `ui/pages/test_cars_page.py`                              |
| `src/pages/settings.py`                           | `ui/pages/test_settings_page.py`                          |
| `src/pages/labor.py`, `parts.py`, `defects.py`, `employees.py` | `ui/pages/test_duplicate_guard.py`           |
| `src/pages/receipts/receipt_form.py`              | `ui/receipts/test_receipt_form.py`, `test_receipt_form_full.py`, `test_receipt_duplicate_guard.py` |
| `src/pages/receipts/receipt_info.py`              | `ui/receipts/test_receipt_info_widget.py`                 |
| `src/pages/receipts/estimates_section.py`         | `ui/receipts/test_estimates_section.py`                   |
| `src/pages/receipts/defects_section.py`           | `ui/receipts/test_defects_section_widget.py`, `test_section_inline_add_duplicate.py` |
| `src/pages/receipts/parts_section.py`             | `ui/receipts/test_parts_section_widget.py`, `test_section_inline_add_duplicate.py` |
| `src/pages/receipts/labor_section.py`             | `ui/receipts/test_labor_section_widget.py`, `test_section_inline_add_duplicate.py` |
| `src/pages/receipts/billable_parts_section.py`    | `ui/receipts/test_billable_parts_widget.py`, `test_section_inline_add_duplicate.py` |
| `src/pages/receipts/receipts.py`                  | `ui/receipts/test_receipts_list.py`, `test_receipts_sort.py` |
| `src/main.py`                                     | `ui/test_main_window.py`                                  |

---

## 6. Excel layout invariants

`tests/services/excel/test_layout_invariants.py` is the most subtle file in
the suite — it locks down the row positions of every static label in the
generated receipt under section expansion. The relevant geometry:

```
row_offset      = max(5, n_defects, n_parts + 2) - 5
disc_extra_rows = inserts caused by discovered defects (similar formula)
total_offset    = row_offset + disc_extra_rows

grand_total_row =
    total_parts_row + 1               if billable_parts
    43 + len(labor_ids) + total_offset elif labor_ids
    44 + total_offset                  else
```

Any change to row insertion logic in `src/services/excel_export.py` should
re-run that whole file:

```powershell
python -m pytest tests/services/excel/test_layout_invariants.py -v
```

---

## 7. Adding new tests

1. Pick the right folder (mirror `src/`).
2. Create `test_<thing>.py` with one or more `TestXxx` classes.
3. If you need a fresh DB, declare `db` as a fixture parameter and call the
   `create_*_table` functions you need.
4. If you need Qt, declare `qapp` as a fixture parameter (or as a class fixture).
5. Mock anything that would otherwise hit the disk, network, or a real
   modal dialog. The pattern used everywhere is:
   ```python
   with patch("src.pages.cars.add_car") as mock_add:
       ...
   ```
6. Run only your file while iterating:
   ```powershell
   python -m pytest tests/path/to/test_new.py -v
   ```
7. Before opening a PR, run the full suite once:
   ```powershell
   python -m pytest tests -q
   ```
