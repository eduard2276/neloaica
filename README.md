# Neloaica

**Automotive Service Management System**

A desktop database management application for small to medium automotive service businesses. Built with Python and PySide6 (Qt6), Neloaica provides a user-friendly interface for managing clients, vehicles, employees, services, parts, defects, and generating service receipts with Excel export.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Technology Stack](#technology-stack)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Key Features](#key-features)
- [Communication Patterns](#communication-patterns)
- [Startup Flow](#startup-flow)
- [Design Patterns](#design-patterns)
- [Styling System](#styling-system)
- [Error Handling](#error-handling)
- [Development Guide](#development-guide)
- [Known Limitations](#known-limitations)
- [AI Context Summary](#ai-context-summary)

---

## Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package installer)

### Installation & Running

```bash
# 1. Clone the repository
git clone https://github.com/eduard2276/neloaica.git
cd neloaica

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python -m src.main
```

### First Launch
On first launch, the application automatically:
- Creates the SQLite database (`neloaica.db`)
- Initializes all 6 tables (clients, cars, labor, parts, defects, settings)
- Populates sample data for testing (10 clients, 11 cars, 12 services, 15 parts, 15 defects)
- Inserts default settings row (TVA = 21.0%)

### Database Location
- **Development mode**: `neloaica.db` in project root
- **Frozen executable** (PyInstaller/cx_Freeze): `neloaica.db` in executable directory

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.9+ |
| GUI Framework | PySide6 (Qt6) | >= 6.6.0 |
| Database | SQLite3 | Built-in |
| Excel Export | openpyxl | >= 3.1.0 |
| Build System | setuptools | pyproject.toml (PEP 621) |
| Dev Tools | pytest, pytest-qt, black, isort, flake8 | See pyproject.toml |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Window (Qt GUI)                      │
│  ┌─────────────┐  ┌─────────────────────────────────────┐   │
│  │   Sidebar   │  │         Page Container              │   │
│  │  Navigation │  │  ┌─────────────────────────────┐    │   │
│  │             │  │  │ • Clients Page              │    │   │
│  │  • Clients  │  │  │ • Cars Page                 │    │   │
│  │  • Cars     │  │  │ • Labor Page                │    │   │
│  │  • Labor    │  │  │ • Parts Page                │    │   │
│  │  • Parts    │  │  │ • Defects Page              │    │   │
│  │  • Defects  │  │  │ • Employees Page            │    │   │
│  │  • Employees│  │  │ • Receipts Page (Complex)   │    │   │
│  │  • Receipts │  │  │ • Dashboard Page            │    │   │
│  │  • Dashboard│  │  │ • Settings Page             │    │   │
│  │  • Settings │  │  └─────────────────────────────┘    │   │
│  └─────────────┘  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│  └── excel_export.py - Receipt Excel generation             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Database Models Layer (per-entity CRUD)         │
│  clients │ cars │ labor │ parts │ defects │ employees │      │
│  settings │ receipts                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│         Database Connection (Singleton) → SQLite            │
│  • Thread-safe │ Foreign keys │ Row factory (dict results)  │
└─────────────────────────────────────────────────────────────┘

Cross-cutting:
  Styles Layer  → ThemeManager singleton provides styles to all UI
  Widgets Layer → NoScroll* widgets used in scrollable forms
```

### Layering Rules
- ✅ Pages → Models, Styles, Widgets
- ✅ Services → Models
- ✅ Models → DatabaseConnection
- ❌ Database layer → Pages, Services, or Styles
- ❌ Services → Pages
- ❌ No circular imports

### Threading Model
Single-threaded. The Qt event loop handles all UI and database operations on the main thread. SQLite performs well for this scale. `check_same_thread=False` is set on the connection for future extensibility.

---

## Project Structure

```
Neloaica/
├── src/
│   ├── __init__.py
│   ├── main.py                      # Entry point: MainWindow, Sidebar, main()
│   │
│   ├── database/
│   │   ├── __init__.py              # Exports: init_database(), populate_mock_data()
│   │   ├── connection.py            # Singleton DatabaseConnection
│   │   └── models/
│   │       ├── __init__.py          # Aggregates all model functions
│   │       ├── clients.py           # Client CRUD (id, first_name, last_name, address)
│   │       ├── cars.py              # Car CRUD (id, client_id FK, plate, vin, model, km)
│   │       ├── labor.py             # Labor CRUD (id, service_name)
│   │       ├── parts.py             # Parts CRUD (id, part_name)
│   │       ├── defects.py           # Defects CRUD (id, defect_name)
│   │       ├── employees.py         # Employee CRUD (id, first_name, last_name)
│   │       ├── receipts.py          # Receipt CRUD (full receipt data, JSON fields)
│   │       └── settings.py          # Settings: get_tva(), update_tva(), get_all_settings()
│   │
│   ├── pages/
│   │   ├── __init__.py              # Exports all Page classes
│   │   ├── clients.py               # ClientsPage + ClientDialog
│   │   ├── cars.py                  # CarsPage + CarDialog (VIN validation)
│   │   ├── labor.py                 # LaborPage + LaborDialog
│   │   ├── parts.py                 # PartsPage + PartDialog
│   │   ├── defects.py               # DefectsPage + DefectDialog
│   │   ├── employees.py             # EmployeesPage + EmployeeDialog
│   │   ├── dashboard.py             # DashboardPage + StatCard
│   │   ├── settings.py              # SettingsPage (TVA management)
│   │   └── receipts/                # Receipt builder subpackage
│   │       ├── __init__.py          # Exports: ReceiptsPage
│   │       ├── receipts.py          # Orchestrator: aggregates sections, grand total, Excel export
│   │       ├── receipt_info.py      # Client/car dropdowns, date picker, km formatting
│   │       ├── defects_section.py   # Reusable defect list (used ×2: client + discovered)
│   │       ├── parts_section.py     # Parts received from client
│   │       ├── labor_section.py     # Labor services with total cost
│   │       └── billable_parts_section.py  # Parts used with units × price/unit
│   │
│   ├── services/
│   │   ├── __init__.py              # Exports: generate_receipt_excel, template_exists
│   │   └── excel_export.py          # Excel generation from template (openpyxl)
│   │
│   ├── styles/
│   │   ├── __init__.py              # Exports: theme (global ThemeManager instance)
│   │   ├── colors.py                # LIGHT_THEME / DARK_THEME color dictionaries
│   │   └── theme_manager.py         # Singleton with 20+ style generator methods
│   │
│   └── widgets/
│       ├── __init__.py              # Exports: NoScrollComboBox, NoScrollSpinBox, etc.
│       └── combo_box.py             # Scroll-safe combo boxes and spin boxes
│
├── templates/
│   └── Template-deviz.xlsx          # Excel receipt template
│
├── exports/receipts/                # Generated Excel receipts (runtime, git-ignored)
├── tests/
│   ├── __init__.py
│   ├── db/                          # Model-layer tests (real in-memory SQLite)
│   │   ├── __init__.py
│   │   ├── conftest.py              # Shared in-memory DB fixture
│   │   ├── test_labor_model.py
│   │   ├── test_parts_model.py
│   │   ├── test_defects_model.py
│   │   ├── test_employees_model.py
│   │   └── test_receipts_model.py
│   ├── excel/                       # Excel export tests
│   │   ├── test_export.py
│   │   ├── test_section_expansion.py
│   │   ├── test_combinations.py
│   │   ├── test_layout_invariants.py
│   │   └── test_disc_section_expansion.py
│   ├── ui/                          # Page/widget-layer tests (mocked DB)
│   │   ├── test_main_window.py
│   │   ├── test_receipt_form.py
│   │   ├── test_receipts_list.py
│   │   ├── test_receipts_sort.py
│   │   ├── test_duplicate_guard.py          # CRUD page duplicate prevention
│   │   ├── test_receipt_duplicate_guard.py  # Receipt form duplicate prevention
│   │   └── test_section_inline_add_duplicate.py  # Receipt section ➕ button guards
│   └── test_main.py
│
├── neloaica.db                      # SQLite database (runtime, git-ignored)
├── requirements.txt                 # PySide6>=6.6.0, openpyxl>=3.1.0
├── pyproject.toml                   # Project metadata (PEP 621)
└── README.md                        # This file
```

### Main Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `ClientsPage` | Customer management | CRUD, search, table view |
| `CarsPage` | Vehicle management | Client association, VIN validation (17 chars) |
| `LaborPage` | Service catalog | Service type management |
| `PartsPage` | Parts inventory | Parts catalog management |
| `DefectsPage` | Defects registry | Defect description tracking |
| `EmployeesPage` | Employee management | CRUD, search, executant assignment |
| `ReceiptsPage` | Receipt creation | Multi-section form, grand total, Excel export, DB persistence |
| `DashboardPage` | Statistics overview | Summary cards, auto-reload on show |
| `SettingsPage` | Configuration | TVA/VAT % with validation (0-100) |

Each CRUD page follows a consistent pattern: table widget with search, add/edit/delete buttons, emoji icon buttons per row (✏️/🗑️), dialog-based forms, and styled confirmation dialogs.

### Receipts Subsystem

The most complex component, composed of signal-connected sub-widgets:

```
ReceiptsPage (orchestrator)
├── ReceiptInfoWidget         → Client/car selection, date picker, editable km
├── DefectsSectionWidget ×2   → "Defects by Client" + "Discovered Defects"
├── PartsSectionWidget        → Parts received from client
├── LaborSectionWidget        → Labor services + total labor cost
├── BillablePartsSectionWidget → Parts used with units × price, subtotals
├── Grand Total display       → Labor + Parts
└── Generate Receipt button   → Excel export trigger
```

### Model Functions (per entity)

Each model module (`clients.py`, `cars.py`, `labor.py`, `parts.py`, `defects.py`, `employees.py`) provides:
- `create_<entity>_table()` — DDL via `CREATE TABLE IF NOT EXISTS`
- `populate_<entity>_mock_data()` — Insert demo data (checks if empty first)
- `get_all_<entity>()` — Read all records (returns `list[dict]`)
- `get_<entity>_by_id(id)` — Read single record
- `get_<entity>_by_name(name)` — Case-insensitive lookup; used for **duplicate prevention** before add/update
- `add_<entity>(...)` — Insert, returns new ID
- `update_<entity>(id, ...)` — Modify existing record
- `delete_<entity>(id)` — Remove record
- `get_<entity>_count()` — Aggregate count

Special functions: `get_clients_for_dropdown()`, `update_car_kilometers()`, `get_employees_for_dropdown()`, `get_employee_by_name(first_name, last_name)` (pair uniqueness), `get_receipt_by_plate_and_date(plate, date, exclude_id)`, `get_tva()`, `update_tva()`.

---

## Database Schema

### Entity Relationships

```
┌─────────────┐       ┌─────────────┐
│   CLIENTS   │───────│    CARS     │
├─────────────┤  1:N  ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ first_name  │       │ client_id   │──→ FK (CASCADE DELETE)
│ last_name   │       │ plate_number│
│ address     │       │ vin (UNIQUE)│
└─────────────┘       │ model       │
                      │ kilometers  │
                      └─────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    LABOR    │  │    PARTS    │  │   DEFECTS   │  │  EMPLOYEES  │  │  SETTINGS   │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ id (PK)     │  │ id (PK)     │  │ id (PK)     │  │ id (PK)     │  │ id=1 (PK)   │
│ service_name│  │ part_name   │  │ defect_name │  │ first_name  │  │ tva (21.0%) │
└─────────────┘  └─────────────┘  └─────────────┘  │ last_name   │  └─────────────┘
                                                    └─────────────┘
```

### Table Definitions

<details>
<summary>Click to expand SQL definitions</summary>

```sql
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    address TEXT
);
-- 10 mock records on first run

CREATE TABLE cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plate_number TEXT NOT NULL,
    vin TEXT NOT NULL UNIQUE,           -- 17-character VIN
    model TEXT NOT NULL,
    kilometers INTEGER DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);
-- 11 mock records on first run

CREATE TABLE labor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL
);
-- 12 mock records on first run

CREATE TABLE parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_name TEXT NOT NULL
);
-- 15 mock records on first run

CREATE TABLE defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_name TEXT NOT NULL
);
-- 15 mock records on first run

CREATE TABLE settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton row
    tva REAL NOT NULL DEFAULT 21.0          -- VAT percentage
);
-- Default row auto-inserted if empty
```

</details>

---

## Key Features

### Duplicate Prevention

All catalog entities (Labor, Parts, Defects, Employees) enforce uniqueness at the **application layer** using case-insensitive name lookups before any insert or update:

- **Add**: `get_X_by_name()` called first; if a match is found a `"Duplicate Entry"` warning is shown and the insert is aborted.
- **Edit**: same check, but the record's own ID is excluded so a no-op rename is allowed.
- **Employees**: uniqueness is on the `(first_name, last_name)` **pair** — two people can share a first or last name.
- **Receipts**: uniqueness is on `(plate_number, date)` — the same car cannot have two receipts on the same day. Enforced in both `Save Receipt` and `Generate & Finish` paths, including `exclude_id` support when editing.
- **Receipt section ➕ buttons**: inline add dialogs (Defects, Parts, Labor, Billable Parts sections) apply the same duplicate check before inserting into the catalog.

### Receipt Persistence

Receipts are **saved to the `receipts` table** in the SQLite database. The `Save Receipt` button persists a receipt with status `Ongoing`; `Generate & Finish` generates the Excel file and marks status as `Done`. JSON-serialized fields (defects, parts, labor, billable_parts) are decoded back to Python lists on read.

Receipts are generated from `templates/Template-deviz.xlsx` into `exports/receipts/Deviz_<Client>_<Timestamp>.xlsx`.

**Cell mapping:**

| Excel Cell(s) | Data |
|----------------|------|
| B10 | Client name |
| B12 | Client address |
| D10 | Car model |
| F10 | Kilometers |
| E11 | Plate number |
| E12 | VIN |
| A14–A18 | Client-reported defects (max 5) |
| A20–A24 | Discovered defects (max 5) |
| C14–C17 | Parts received from client (max 4) |
| B36+ | Labor services (dynamic rows, formatting copied) |
| E(labor end) | Total labor cost |
| B42+ (offset) | Billable parts: name (B), units (C), price/unit (D), total (E), TVA (F) |
| F(grand total) | Grand total (labor + parts) |

**TVA calculation** (extracted from prices that already include tax):
```python
tva = (price * tva_percentage) / (100 + tva_percentage)
```

Truncation warnings are returned when data exceeds template capacity. Generated files auto-open via `os.startfile()`.

### Settings Management

Single-row `settings` table with TVA (VAT) percentage. The `SettingsPage` provides edit/save/cancel with validation (0–100%) and read-only mode.

---

## Communication Patterns

### UI → Data Layer
Direct function calls: pages import model functions and call them synchronously.

```python
from src.database.models import get_all_clients
clients = get_all_clients()  # Returns list[dict]
```

### Navigation (Signal/Slot)
Sidebar `QListWidget.currentRowChanged` → `MainWindow.change_page()` → `QStackedWidget.setCurrentIndex()`.

### Receipt Sections (Observer Pattern)
Each receipt section emits Qt Signals when data changes. `ReceiptsPage` connects to all and aggregates into `receipt_data`:

| Widget | Signal | Payload |
|--------|--------|---------|
| `ReceiptInfoWidget` | `data_changed` | `dict` (client, car, date info) |
| `DefectsSectionWidget` | `defects_changed` | `list[int]` (defect IDs) |
| `PartsSectionWidget` | `parts_changed` | `list[int]` (part IDs) |
| `LaborSectionWidget` | `labor_changed` | `list[int], float` (IDs + total cost) |
| `BillablePartsSectionWidget` | `parts_changed` | `list[dict], float` (parts data + total) |

### CRUD Dialog Pattern
1. Page creates `<Entity>Dialog(parent, optional_data)`.
2. Dialog displays form, `exec()` blocks.
3. User submits → dialog validates → page calls `dialog.get_data()` → page calls model function → page reloads.

### State Restoration
Receipt sections save/restore user selections on page transitions (`showEvent`). Dropdowns reload from database while preserving in-progress selections via `save_form_state()` / `restore_form_state()`.

### Theming
All UI components import the global `theme` singleton and call style generators:
```python
from src.styles import theme
button.setStyleSheet(theme.button("success"))
table.setStyleSheet(theme.table())
```

---

## Startup Flow

```
1. python -m src.main → main() called
2. QApplication created (name="Neloaica", org="Neloaica Project", version="1.0.0")
3. init_database() → CREATE TABLE IF NOT EXISTS for all 6 tables
   └── Settings table auto-inserts default row (tva=21.0) if empty
4. populate_mock_data() → inserts demo data into 5 tables (if empty)
5. ThemeManager singleton initialized (defaults to "light" theme)
6. MainWindow constructed:
   ├── QStackedWidget with all 8 pages (each loads data in __init__)
   │   └── ReceiptsPage creates 6 section widgets, each loading their data
   └── Sidebar with 8 navigation items
7. window.show() → app.exec() → Qt event loop (blocks until quit)
```

All pages load data at startup (eager loading). Receipt sections also reload data on every `showEvent` to reflect changes from other pages.

---

## Design Patterns

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Singleton** | `DatabaseConnection`, `ThemeManager` | Single DB connection, single theme source of truth |
| **Observer** | Receipt section signals | Loose coupling between receipt widgets |
| **Facade** | `models/__init__.py`, `services/__init__.py`, `styles/__init__.py` | Single import point per layer |
| **Modal Dialog** | All CRUD pages (`*Dialog` classes) | Consistent add/edit forms with validation |
| **Table-View** | All CRUD pages | QTableWidget with search, row actions, consistent styling |
| **State Preservation** | Receipt sections | Save/restore form state across page navigations |

---

## Styling System

Centralized `ThemeManager` singleton with 20+ style generator methods. No inline stylesheets — all styling goes through `theme.<method>()`.

### Available Themes

| Theme | Key Colors |
|-------|-----------|
| **Light** (default) | Primary `#3498db`, Success `#2ecc71`, Danger `#e74c3c`, Sidebar `#2c3e50`, Background `#ecf0f1` |
| **Dark** | Primary `#3498db`, Backgrounds `#1a1a2e`/`#16213e`, Text `#ecf0f1`, Sidebar `#0f0f1a` |

Switch via: `theme.set_theme("dark")`

### Style Methods

| Category | Methods |
|----------|---------|
| Components | `page_title()`, `combobox()`, `line_edit()`, `line_edit_dialog()`, `line_edit_readonly()`, `search_input()`, `groupbox()`, `table()`, `dialog()`, `list_widget()`, `list_widget_with_items()`, `form_label()`, `label_item()` |
| Buttons | `button(variant)` (primary/success/danger/gray/cancel), `button_icon(variant)`, `button_add()`, `button_remove()` |
| Layout | `sidebar()`, `sidebar_title()`, `sidebar_button()`, `content_area()`, `scroll_area()` |
| Special | `message_box_confirm()` |

### Visual Conventions
- 6–8px border radius
- Emoji icons in sidebar (👥 🚗 ⚙️ 🔧 ⚠️ 🧾 📊)
- 28px bold page titles
- 15–20px form spacing, 30px content margins
- Variant-based button colors (success=green, danger=red, primary=blue, gray=neutral)

---

## Error Handling

**Validation**: Dialog-level required field checks, VIN length (17 chars), TVA range (0–100%), kilometers digit-only filtering.

**Duplicate detection**: Before any catalog insert or receipt save, a case-insensitive lookup (`get_X_by_name()` / `get_receipt_by_plate_and_date()`) is performed. Conflicts are shown as a `"Duplicate Entry"` or `"Duplicate Receipt"` warning dialog and the write is aborted. This applies on all four catalog pages, all four receipt section inline-add buttons, and both receipt save paths.

**Database**: SQLite constraints (`NOT NULL`, `UNIQUE`, `FOREIGN KEY`) act as safety net. Unique VIN violations caught and shown to user.

**Excel Export**: Template existence check, client selection validation, try/catch with `QMessageBox.critical()`, truncation warnings when data exceeds template limits.

---

## Development Guide

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
isort src/
```

### Linting
```bash
flake8 src/
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | `lowercase_with_underscores` | `excel_export.py` |
| Classes | `PascalCase` | `ClientsPage`, `ThemeManager` |
| Functions | `lowercase_with_underscores` | `get_all_clients()` |
| Constants | `UPPER_CASE` | `LIGHT_THEME`, `TEMPLATES_DIR` |
| Signals | `lowercase_with_underscores` | `data_changed`, `defects_changed` |

### Adding a New Entity

1. Create `src/database/models/<entity>.py` with CRUD functions
2. Import and register in `src/database/models/__init__.py` (add to `init_database()` and `populate_mock_data()`)
3. Create `src/pages/<entity>.py` with `<Entity>Page` + `<Entity>Dialog`
4. Register in `src/pages/__init__.py`
5. Add page to `MainWindow.pages` stack and `Sidebar.nav_list` in `src/main.py`

### Adding a New Receipt Section

1. Create section widget in `src/pages/receipts/` with a Signal for data changes
2. Instantiate in `ReceiptsPage.setup_ui()` and connect signal to handler
3. Update `receipt_data` dict in the handler
4. Update `excel_export.py` to write the new section data into the template

### Adding New Theme Styles

Add a method to `ThemeManager` in `src/styles/theme_manager.py`:

```python
def my_component(self) -> str:
    return f"""
        QWidget {{
            background-color: {self._colors['bg_primary']};
            color: {self._colors['text_primary']};
        }}
    """
```

### Adding a New Theme

Add a color dictionary to `src/styles/colors.py` and register it in the `THEMES` dict:

```python
MY_THEME = { "primary": "#...", "success": "#...", ... }
THEMES = { "light": LIGHT_THEME, "dark": DARK_THEME, "my_theme": MY_THEME }
```

---

## Known Limitations

1. **Limited data validation** — VIN length checked but not format; plate number format not enforced; no email/phone for clients
2. **No undo/redo** — Destructive operations are immediate and permanent
3. **Excel template constraints** — Max 5 defects per category, max 4 parts received; cell positions hardcoded
4. **No user authentication** — Single-user, no access control
5. **No data backup** — No automated backup mechanism
6. **Simple search only** — Substring matching, no fuzzy search or advanced filtering
7. **Single database file** — No support for multiple databases or profiles
8. **No audit trail** — No change history for records
9. **Windows-only auto-open** — `os.startfile()` for generated files is Windows-specific
10. **Missing pyproject.toml dependency** — `openpyxl` is in `requirements.txt` but not in `pyproject.toml`
11. **Debug print statements** — `excel_export.py` contains `print()` debug logging (should use `logging` module)
12. **Eager loading** — All pages load data at startup; no pagination; suitable for <10,000 records per table

---

## AI Context Summary

This is a **single-threaded desktop database management tool** built with **Python 3.9+ and PySide6 (Qt6)**. Layered architecture: UI (pages) → Services (Excel export) → Models (CRUD) → DatabaseConnection (singleton) → SQLite.

**Key architectural decisions**: Singleton DB connection + theme manager, per-entity model modules, signal-based receipt sections, centralized ThemeManager with light/dark support, template-based Excel export, mock data auto-population, application-layer duplicate prevention (case-insensitive `get_X_by_name()` lookups) for all catalog entities and receipts.

**Primary use cases**: Managing clients, tracking vehicles per client, managing employees/executants, maintaining service/parts/defect catalogs, building and exporting service receipts (persisted to DB), configuring TVA/VAT.

**Code generation guidelines**:
- Use type hints for function signatures
- Keep model functions pure (no UI code)
- Use `theme.<method>()` for all styling (no inline stylesheets)
- Use `NoScrollComboBox` for combo boxes in scrollable areas
- Emit signals from receipt section widgets when data changes
- Include docstrings for public functions
- Validate user input in dialogs before accepting
- Follow naming conventions (see Development Guide)

---

## License

MIT License

## Repository

https://github.com/eduard2276/neloaica.git
