# Neloaica

**Automotive Service Management System**

A desktop database management application for small to medium automotive service businesses. Built with Python and PySide6 (Qt6), Neloaica provides a user-friendly interface for managing clients, vehicles, employees, services, parts, defects, and for generating service receipts with Excel export.

The application ships as a standalone Windows executable with **in-app auto-update**, automatic per-day database backups, rotating log files and a user data directory that survives reinstalls (`%LOCALAPPDATA%\Neloaica`).

Current release: **v1.0.6** ([GitHub Releases](https://github.com/eduard2276/neloaica/releases)).

---

## Table of Contents

- [Quick Start](#quick-start)
- [Technology Stack](#technology-stack)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Application Features](#application-features)
- [Auto-Update](#auto-update)
- [Backups, Logs and User Data](#backups-logs-and-user-data)
- [Build & Release](#build--release)
- [Continuous Integration](#continuous-integration)
- [Communication Patterns](#communication-patterns)
- [Startup Flow](#startup-flow)
- [Design Patterns](#design-patterns)
- [Styling System](#styling-system)
- [Error Handling](#error-handling)
- [Development Guide](#development-guide)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Related Documentation](#related-documentation)

---

## Quick Start

### Prerequisites

- Python 3.9 or higher (the released `.exe` ships its own Python, only required for development)
- pip
- Windows for the auto-update / Scheduled Task flow (development and CI also support Linux/macOS)

### Run from source

```powershell
# 1. Clone the repository
git clone https://github.com/eduard2276/neloaica.git
cd neloaica

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # macOS/Linux

# 3. Install runtime + dev dependencies
pip install -e ".[dev]"

# 4. Run the application
python -m src.main
```

### Run the released executable

1. Download `Neloaica-v<X.Y.Z>-windows.zip` from the [latest GitHub Release](https://github.com/eduard2276/neloaica/releases/latest).
2. Unzip it anywhere writable (the app will create its own data folder under `%LOCALAPPDATA%\Neloaica`).
3. Run `Neloaica.exe`. From the **Settings → Actualizări** section you can check for updates at any time.

### First Launch

On first launch, the application automatically:

- Resolves the user data directory (`%LOCALAPPDATA%\Neloaica` on Windows, the project root in dev mode).
- Sets up rotating log files under `logs/` in that directory.
- Migrates legacy data: if a previous build wrote `neloaica.db` or a `backups/` folder next to the executable, those are moved into the user data dir on first start (one-shot, idempotent).
- Creates the SQLite database (`neloaica.db`) and all tables.
- Populates demo data on a fresh install (10 clients, 11 cars, 12 services, 15 parts, 15 defects, 5 employees).
- Inserts the default settings row (TVA = 21.0%).
- Writes a startup backup and, if missing, a daily backup under `backups/`.

---

## Technology Stack

| Component                | Technology                              | Version                          |
| ------------------------ | --------------------------------------- | -------------------------------- |
| Language                 | Python                                  | 3.9+ (3.12 used by CI / release) |
| GUI Framework            | PySide6 (Qt6)                           | >=6.6.0, <6.11                   |
| Database                 | SQLite3                                 | Built-in                         |
| Excel Export             | openpyxl                                | >=3.1.0                          |
| Imaging (icons, exports) | Pillow                                  | >=10.0.0                         |
| Packaging                | PyInstaller (`onedir`, windowed)        | latest from PyPI                 |
| Build System             | setuptools                              | PEP 621 (`pyproject.toml`)       |
| Dev / QA Tools           | pytest, pytest-qt, black, isort, flake8 | See `[project.optional-dependencies] dev` |
| CI/CD                    | GitHub Actions                          | `ci.yml`, `release.yml`          |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Main Window (Qt GUI)                            │
│  ┌─────────────┐  ┌─────────────────────────────────────────────┐    │
│  │   Sidebar   │  │              Page Container                  │    │
│  │  Navigation │  │  Clients / Cars / Labor / Parts / Defects /  │    │
│  │             │  │  Employees / Receipts / Settings             │    │
│  └─────────────┘  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                          Services Layer                               │
│  excel_export       → Excel receipt generation (openpyxl)             │
│  backup             → Startup / daily / manual DB backups + rotation  │
│  logging_setup      → RotatingFileHandler under user data dir         │
│  updater/           → Version, Schema, Check, Download, Apply,        │
│                       Orchestrator (in-app auto-update pipeline)      │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│              Database Models Layer (per-entity CRUD)                  │
│  clients │ cars │ labor │ parts │ defects │ employees │ settings │   │
│  receipts                                                             │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│            Database Connection (Singleton) → SQLite                   │
│   Thread-safe │ Foreign keys │ Row factory (dict results)             │
└──────────────────────────────────────────────────────────────────────┘

Cross-cutting:
  paths.py     → Single source of truth for app / bundle / user data dirs
  styles/      → ThemeManager singleton: all UI uses theme.<method>() styles
  widgets/     → NoScroll* widgets, UpdateProgressDialog + update workers
```

### Layering Rules

- Pages → Models, Services, Styles, Widgets
- Services → Models, Paths
- Models → DatabaseConnection
- Database layer must not import Pages or Services
- Services must not import Pages
- No circular imports

### Threading Model

The UI runs on the Qt main thread; SQLite operations are synchronous. The only background threads are the **auto-update workers** (`UpdateCheckWorker`, `UpdateDownloadWorker`), implemented as `QThread` subclasses that emit Qt signals back to the UI for progress and completion. `check_same_thread=False` is set on the DB connection for future extensibility.

---

## Project Structure

```
Neloaica/
├── src/
│   ├── __init__.py                       # __version__ — single source of truth for app version
│   ├── main.py                           # Entry point: bootstrap() + MainWindow + Sidebar + main()
│   ├── paths.py                          # App / bundle / user-data dirs + legacy migration helpers
│   ├── utils.py                          # Small shared utilities
│   │
│   ├── database/
│   │   ├── __init__.py                   # Exports: init_database(), populate_mock_data()
│   │   ├── connection.py                 # Singleton DatabaseConnection
│   │   └── models/
│   │       ├── __init__.py               # Aggregates all model functions
│   │       ├── clients.py / cars.py / labor.py / parts.py / defects.py / employees.py
│   │       ├── receipts.py               # Receipt CRUD with JSON-serialised sub-lists
│   │       └── settings.py               # tva (singleton row)
│   │
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── clients.py / cars.py / labor.py / parts.py / defects.py / employees.py
│   │   ├── settings.py                   # TVA management + Auto-update "Check for updates" button
│   │   └── receipts/                     # Receipt builder subpackage
│   │       ├── __init__.py
│   │       ├── receipts.py               # Orchestrator + receipts list
│   │       ├── receipt_form.py           # Single-receipt form window
│   │       ├── receipt_info.py
│   │       ├── defects_section.py
│   │       ├── parts_section.py
│   │       ├── labor_section.py
│   │       ├── billable_parts_section.py
│   │       └── estimates_section.py      # Pre-receipt estimates / discovered work
│   │
│   ├── services/
│   │   ├── __init__.py                   # Facade for excel/backup/logging/updater symbols
│   │   ├── excel_export.py               # Receipt Excel generation
│   │   ├── backup.py                     # create_backup / should_create_daily_backup / rotation
│   │   ├── logging_setup.py              # setup_logging() — rotating file + console handlers
│   │   └── updater/                      # Auto-update pipeline
│   │       ├── __init__.py
│   │       ├── version.py                # Version dataclass + parsing + comparison
│   │       ├── schema.py                 # Manifest schema, UpdateInfo, UpdateChannel, error types
│   │       ├── check.py                  # UpdateChecker + manifest fetch (urllib) + env override
│   │       ├── download.py               # UpdateDownloader (chunked HTTP, sha256, cancel, retry)
│   │       ├── apply.py                  # UpdateApplier (stage, PowerShell helper, Scheduled Task)
│   │       └── orchestrator.py           # UpdateOrchestrator facade (check → download → apply)
│   │
│   ├── styles/
│   │   ├── __init__.py                   # Exports the global `theme` ThemeManager instance
│   │   ├── colors.py
│   │   └── theme_manager.py
│   │
│   └── widgets/
│       ├── __init__.py
│       ├── combo_box.py                  # NoScrollComboBox / NoScrollSpinBox
│       └── update_widgets.py             # UpdateCheckWorker, UpdateDownloadWorker, UpdateProgressDialog
│
├── templates/
│   └── Template-deviz.xlsx               # Excel receipt template
│
├── exports/receipts/                     # Generated Excel receipts (runtime, gitignored)
│
├── .github/workflows/
│   ├── ci.yml                            # Lint + tests on push / PR (Windows + Linux)
│   └── release.yml                       # Build PyInstaller exe, draft release, update manifest
│
├── tests/                                # 1228 tests (pytest)
│   ├── conftest.py
│   ├── database/                         # Model-layer tests (in-memory SQLite)
│   ├── services/                         # Backup, logging, Excel export, updater
│   │   ├── test_backup.py
│   │   ├── test_logging_setup.py
│   │   ├── excel/                        # Receipt Excel export tests (5 files)
│   │   └── updater/                      # Updater unit tests (version, schema, check, download, apply, orchestrator)
│   ├── ui/                               # Page / widget tests (mocked DB)
│   │   ├── pages/                        # Per-page UI tests (settings inc. auto-update flow)
│   │   ├── receipts/                     # Receipt sub-widget tests
│   │   └── test_main_window.py / test_theme.py / test_widgets.py / test_utils.py
│   ├── widgets/                          # QThread workers + UpdateProgressDialog
│   └── unit/                             # Paths, version, PyInstaller spec, release workflow YAML, helper scripts
│
├── scripts/                              # Release helpers used from CI
│   ├── verify_tag_matches_version.py     # Fail-fast if the pushed tag != src.__version__
│   └── update_manifest.py                # Rewrite update-manifest.json on main after a release
│
├── Neloaica.spec                         # PyInstaller spec (onedir, windowed, bundled templates)
├── build.bat                             # Local build helper (cleans build/ + dist/, runs PyInstaller)
├── update-manifest.json                  # Auto-update manifest served from main branch
├── requirements.txt                      # Pinned runtime dependencies for `pip install -r`
├── pyproject.toml                        # Project metadata + dynamic version + dev extras
├── COMMANDS.md                           # Detailed development / build / release commands
└── README.md                             # This file
```

---

## Database Schema

```
┌─────────────┐       ┌─────────────────┐
│   CLIENTS   │───────│      CARS       │
├─────────────┤  1:N  ├─────────────────┤
│ id (PK)     │       │ id (PK)         │
│ first_name  │       │ client_id (FK)  │── ON DELETE CASCADE
│ last_name   │       │ plate_number    │
│ address     │       │ vin (UNIQUE)    │── 17 chars
└─────────────┘       │ model           │
                      │ kilometers      │
                      └─────────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    LABOR    │  │    PARTS    │  │   DEFECTS   │  │  EMPLOYEES  │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ id (PK)     │  │ id (PK)     │  │ id (PK)     │  │ id (PK)     │
│ service_name│  │ part_name   │  │ defect_name │  │ first_name  │
└─────────────┘  └─────────────┘  └─────────────┘  │ last_name   │
                                                    └─────────────┘

┌────────────────────────────────────────────────────┐
│                     RECEIPTS                        │
├────────────────────────────────────────────────────┤
│ id (PK)                                            │
│ client_id (FK clients.id)                          │
│ car_id (FK cars.id)                                │
│ plate_number, vin, model, kilometers (denormalised)│
│ receipt_date, executant_id (FK employees.id)       │
│ defects_client, defects_discovered  (JSON arrays)  │
│ parts_received, billable_parts      (JSON arrays)  │
│ labor                               (JSON arrays)  │
│ grand_total                                        │
│ status (Ongoing / Done)                            │
│ excel_path  (path on disk after Generate & Finish) │
│ created_at, updated_at                             │
└────────────────────────────────────────────────────┘
UNIQUE (plate_number, receipt_date)  → application-layer guard

┌─────────────┐
│  SETTINGS   │
├─────────────┤
│ id=1 (PK)   │  Singleton row enforced via CHECK (id = 1)
│ tva REAL    │  Default 21.0
└─────────────┘
```

Every model module (`clients.py`, `cars.py`, …) provides the same canonical surface: `create_<entity>_table()`, `populate_<entity>_mock_data()`, `get_all_<entity>()`, `get_<entity>_by_id(id)`, `get_<entity>_by_name(name)` (case-insensitive — used for duplicate prevention), `add_<entity>(...)`, `update_<entity>(id, ...)`, `delete_<entity>(id)`, `get_<entity>_count()`. Specialised lookups: `get_clients_for_dropdown()`, `get_employees_for_dropdown()`, `get_employee_by_name(first, last)` (pair uniqueness), `get_receipt_by_plate_and_date(plate, date, exclude_id=None)`, `update_car_kilometers()`.

---

## Application Features

### Catalog Pages

Each CRUD page (Clients, Cars, Labor, Parts, Defects, Employees) follows the same pattern:

- `QTableWidget` with search box and per-row icon buttons (✏️ / 🗑️).
- Dialog-based add/edit forms with field validation.
- Case-insensitive duplicate prevention before insert / update (application layer).
- Soft-confirm before delete.

### Receipts

The most complex screen. Composed of signal-connected sub-widgets:

```
ReceiptsPage (list + filters)
└── ReceiptForm (separate window)
    ├── ReceiptInfoWidget          → Client/car selection, date, editable km
    ├── DefectsSectionWidget ×2    → "Defects reported by client" + "Discovered defects"
    ├── PartsSectionWidget         → Parts received from the client
    ├── LaborSectionWidget         → Labor services + total labour cost
    ├── BillablePartsSectionWidget → Parts used × units × price/unit (with TVA)
    ├── EstimatesSectionWidget     → Pre-receipt estimates / discovered work
    └── Grand Total + Save / Generate Excel & Finish buttons
```

Receipts are persisted to the `receipts` table. `Save Receipt` stores the receipt with status `Ongoing`; `Generate & Finish` exports the Excel file under `exports/receipts/` and marks it `Done`. JSON-serialised sub-lists (defects, parts, labour) are decoded back to Python on read. Duplicate guard: a car cannot have two receipts on the same date.

The Excel file is rendered from `templates/Template-deviz.xlsx`. The export expands rows dynamically for labour and billable parts, copies formatting from the template row, and computes per-line TVA from the inclusive price using:

```python
tva = (price * tva_percentage) / (100 + tva_percentage)
```

Truncation warnings are returned when data exceeds template capacity. Generated files auto-open via `os.startfile()` on Windows.

### Settings

- Edit / Save / Cancel for the TVA percentage (validated, 0–100).
- "Verifică actualizări" button — runs the full check / download / apply auto-update flow in the background (see [Auto-Update](#auto-update)).
- Displays the current application version (`src.__version__`).

### Dashboard

Lightweight statistics page (record counts, etc.) — refreshed on every `showEvent`.

---

## Auto-Update

Neloaica ships an in-app updater that downloads a new build from GitHub Releases, swaps it on top of the running install and relaunches. The pipeline lives in `src/services/updater/` and is intentionally split into small, individually testable stages:

```
src/services/updater/
├── version.py        Version dataclass, parsing, ordering
├── schema.py         Manifest schema + UpdateInfo + UpdateChannel + error types
├── check.py          Fetch update-manifest.json, compare with current version
├── download.py       Chunked HTTP download, sha256 verification, cancel + retry
├── apply.py          Stage archive, write PowerShell helper, spawn via Task Scheduler
└── orchestrator.py   High-level facade: check → download → apply with caching
```

### How a check / install runs in the UI

1. **Settings → Verifică actualizări** spawns an `UpdateCheckWorker` (`QThread`).
2. The worker calls `UpdateOrchestrator.check()` which fetches `update-manifest.json` from the configured URL and returns an `UpdateInfo` (or `None` when up to date). The default manifest URL is `https://raw.githubusercontent.com/eduard2276/neloaica/main/update-manifest.json`. Override at runtime by setting `NELOAICA_UPDATE_MANIFEST_URL` (useful for testing branch-specific manifests).
3. If a newer version is available, an `UpdateProgressDialog` opens and an `UpdateDownloadWorker` streams the release ZIP into `%LOCALAPPDATA%\Neloaica\updates\`, verifying the SHA-256 against the manifest as it goes.
4. On a successful download, `UpdateApplier.apply()` extracts the archive into `updates\staging\Neloaica-v<X.Y.Z>\`, generates a self-contained PowerShell helper (`apply_update.ps1`) and hands it off to spawn.

### Helper spawn strategy (Windows)

A running `.exe` cannot overwrite its own folder, so the swap is delegated to a PowerShell helper that:

1. Waits up to 60 s for the Qt parent process to exit.
2. Renames the install folder to `<install>.old.<timestamp>` (rollback safety net).
3. Moves the staged build into the install location.
4. Re-launches `Neloaica.exe`.
5. Deletes its own Scheduled Task (see below) and writes a structured `apply_update.log` next to itself.

Spawning the helper turned out to be the load-bearing piece. `subprocess.Popen(creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB)` is **not enough** on PyInstaller `runw.exe` builds: the bootloader's Windows Job Object can ignore the breakaway request and kill the helper the moment `QApplication.quit()` is called. The current solution registers a **one-shot Scheduled Task** (`schtasks /Create … /SC ONCE /F` then `schtasks /Run`), which runs the helper from the Task Scheduler service process tree — fully detached from anything our process is in. The detached `Popen` is preserved as a fallback for the rare environments where `schtasks` is unavailable.

### Update artefacts on disk

```
%LOCALAPPDATA%\Neloaica\
└── updates\
    ├── Neloaica-v<X.Y.Z>.zip            # Downloaded release archive
    └── staging\
        ├── Neloaica-v<X.Y.Z>\          # Extracted build
        ├── apply_update.ps1            # Generated helper
        └── apply_update.log            # Append-only structured log
```

Every step writes to `apply_update.log`; this is the first place to look if the update appears to hang. Diagnostic recipes live in `COMMANDS.md` under "Troubleshooting auto-update".

---

## Backups, Logs and User Data

### User Data Directory

Resolved by `src.paths.get_user_data_dir()`:

| Mode               | Location                                             |
| ------------------ | ---------------------------------------------------- |
| Frozen, Windows    | `%LOCALAPPDATA%\Neloaica`                            |
| Frozen, macOS      | `~/Library/Application Support/Neloaica`             |
| Frozen, Linux/Unix | `$XDG_DATA_HOME/Neloaica` (falls back to `~/.local/share/Neloaica`) |
| Dev (not frozen)   | Project root — keeps the workspace layout stable     |

Layout inside the user data dir:

```
Neloaica/
├── neloaica.db
├── logs/
│   └── neloaica.log               # RotatingFileHandler, multiple backups kept
├── backups/
│   └── neloaica_backup_<type>_<YYYY-MM-DD>_<HH-MM-SS>.db
└── updates/                       # See Auto-Update section
```

### Legacy Migration

Older builds wrote `neloaica.db` and `backups/` next to the executable. `bootstrap()` in `src/main.py` runs `migrate_legacy_db()` and `migrate_legacy_dir()` on every startup — they are idempotent and never raise. After a successful migration the legacy files are removed from the install folder.

### Backups

- **Startup backup** on every launch (`backup_type="startup"`).
- **Daily automatic backup** the first time the app starts on a calendar day (`backup_type="auto"`).
- **Manual backup** can be triggered from code via `create_backup("manual")` (no UI button today).
- **Pre-receipt** backups can be added by calling `create_backup("pre-receipt")` before destructive flows.
- **Rolling retention**: a maximum of `MAX_BACKUPS = 7` backups per type are kept on disk; older ones are deleted.

### Logging

`setup_logging()` (`src/services/logging_setup.py`) wires up a `RotatingFileHandler` writing to `logs/neloaica.log` (plus an optional console handler in dev). The handler is configured before any module-level logger is used. All other code calls `logger = logging.getLogger(__name__)` — there is no `print()` in runtime modules.

---

## Build & Release

The release artefact is a single `Neloaica-v<X.Y.Z>-windows.zip` containing a PyInstaller `onedir` (windowed) bundle.

### Build locally

```powershell
.\build.bat
```

`build.bat`:

1. Manually clears `build\` and `dist\` (with a small retry loop because OneDrive and antivirus sometimes lock files in those folders).
2. Runs PyInstaller against `Neloaica.spec` (without `--clean` — the manual cleanup above is more reliable on contributor machines).
3. Leaves the build under `dist\Neloaica\` ready to be zipped.

### Release a new version

The full sequence — bump, tag, push, watch — is documented in `COMMANDS.md`. The short version:

```powershell
# 1. Bump src/__init__.py __version__ to the new X.Y.Z.
# 2. Commit on main.
git push origin main

# 3. Tag and push.
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Pushing a tag named `v*.*.*` triggers `.github/workflows/release.yml`, which:

1. Builds the Windows artefact via PyInstaller on a `windows-latest` runner.
2. Verifies the embedded version matches the tag (`scripts/verify_tag_matches_version.py`).
3. Zips `dist\Neloaica\` as `Neloaica-v<X.Y.Z>-windows.zip` and uploads it to the GitHub Release as an asset.
4. Computes the SHA-256 and rewrites `update-manifest.json` on `main` (`scripts/update_manifest.py`), then commits & pushes with `[skip ci]` — so the next time any installed copy checks, it gets the new manifest.

---

## Continuous Integration

`.github/workflows/ci.yml` runs on every push and pull request:

- Installs the project with `pip install -e ".[dev]"`.
- Black + isort + flake8 (lint must be clean — no informational mode).
- `pytest` — currently **1228 tests, 2 skipped**, on both `ubuntu-latest` and `windows-latest`, with `QT_QPA_PLATFORM=offscreen` for headless Qt.

`.github/workflows/release.yml` runs only on `v*.*.*` tag pushes (see above).

The workflows themselves are covered by tests (`tests/unit/test_release_workflow.py`, `tests/unit/test_update_manifest_script.py`, `tests/unit/test_verify_tag_script.py`, `tests/unit/test_update_manifest_file.py`, `tests/unit/test_pyinstaller_spec.py`, `tests/unit/test_spec_smoke.py`) so accidental drift breaks CI early.

---

## Communication Patterns

### UI → Data Layer

Direct function calls. Pages import model functions and call them synchronously:

```python
from src.database.models import get_all_clients

clients = get_all_clients()  # list[dict]
```

### Navigation (Signal/Slot)

`Sidebar.nav_list.currentRowChanged` → `MainWindow.change_page` → `QStackedWidget.setCurrentIndex`.

### Receipt Sections (Observer)

Each receipt sub-widget emits a Qt signal when its data changes; `ReceiptForm` aggregates everything into a single `receipt_data` dict:

| Widget                       | Signal           | Payload                                 |
| ---------------------------- | ---------------- | --------------------------------------- |
| `ReceiptInfoWidget`          | `data_changed`   | `dict` (client, car, date)              |
| `DefectsSectionWidget`       | `defects_changed`| `list[int]`                             |
| `PartsSectionWidget`         | `parts_changed`  | `list[int]`                             |
| `LaborSectionWidget`         | `labor_changed`  | `list[int], float` (IDs + labour total) |
| `BillablePartsSectionWidget` | `parts_changed`  | `list[dict], float`                     |
| `EstimatesSectionWidget`     | `estimates_changed` | `list[dict]`                        |

### Async work (auto-update)

Long-running work runs in `QThread` subclasses that emit signals back to the UI:

- `UpdateCheckWorker.finished_ok(UpdateInfo|None)` / `failed(str)`
- `UpdateDownloadWorker.progress(int, int)` / `finished_ok(DownloadResult)` / `failed(str)`

`SettingsPage` connects to these signals to update the status label and progress dialog.

### Theming

```python
from src.styles import theme

button.setStyleSheet(theme.button("success"))
table.setStyleSheet(theme.table())
```

---

## Startup Flow

```
1. python -m src.main → main() called
2. QApplication created (name="Neloaica", org="Neloaica Project", version=__version__)
3. bootstrap()
   ├── setup_logging()                 → logs/neloaica.log ready
   ├── migrate_legacy_db()              → move pre-1.0.0 db, if any
   ├── migrate_legacy_dir(backups/)     → move pre-1.0.0 backups, if any
   ├── init_database()                  → CREATE TABLE IF NOT EXISTS for all tables
   ├── create_backup("startup")
   └── create_backup("auto") if no daily backup exists yet
4. ThemeManager singleton already initialised on first import (defaults to light theme)
5. MainWindow constructed with all pages + Sidebar
6. window.show() → app.exec() — Qt event loop blocks until quit
```

`bootstrap()` is exposed as a standalone function so unit tests in `tests/unit/test_main_bootstrap.py` can exercise the startup sequence without a real `QApplication`.

---

## Design Patterns

| Pattern              | Where Used                                           | Purpose                                                   |
| -------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| **Singleton**        | `DatabaseConnection`, `ThemeManager`                 | One DB connection, one theme source of truth              |
| **Facade**           | `models/__init__.py`, `services/__init__.py`, `updater/__init__.py`, `UpdateOrchestrator` | Single import surface per layer / pipeline                |
| **Observer**         | Receipt section signals, update worker signals       | Loose coupling between widgets and background work        |
| **Modal Dialog**     | All CRUD pages (`*Dialog` classes), `UpdateProgressDialog` | Consistent add/edit forms + cancellable progress UI       |
| **Table-View**       | All CRUD pages                                       | `QTableWidget` with search, row actions, consistent styling |
| **State Preservation** | Receipt sections                                   | Save / restore form state across page navigations         |
| **Strategy + Fallback** | `UpdateApplier._spawn_helper`                     | Try Scheduled Task first, fall back to detached `Popen`    |
| **Dataclass Plan**   | `ApplyPlan`                                          | Compute everything up front, fail before side effects     |

---

## Styling System

Centralised `ThemeManager` singleton with 20+ style generator methods. No inline stylesheets in production code — all styling goes through `theme.<method>()`.

| Theme   | Key Colors                                                                                              |
| ------- | ------------------------------------------------------------------------------------------------------- |
| Light (default) | Primary `#3498db`, Success `#2ecc71`, Danger `#e74c3c`, Sidebar `#2c3e50`, Background `#ecf0f1` |
| Dark            | Primary `#3498db`, Backgrounds `#1a1a2e` / `#16213e`, Text `#ecf0f1`, Sidebar `#0f0f1a`         |

Switch via `theme.set_theme("dark")`. Custom themes can be registered by appending to `THEMES` in `src/styles/colors.py`.

### Adding a new theme style

```python
def my_component(self) -> str:
    return f"""
        QWidget {{
            background-color: {self._colors['bg_primary']};
            color: {self._colors['text_primary']};
        }}
    """
```

---

## Error Handling

- **Validation** — Dialog-level required-field checks, VIN length (17), TVA range (0–100), kilometres digit-only.
- **Duplicate detection** — Case-insensitive `get_X_by_name()` lookups before any insert or update, on all catalog pages and all receipt section inline-add buttons; `get_receipt_by_plate_and_date()` before any receipt save (with `exclude_id` on edit). Conflicts surface as a styled `QMessageBox` warning, never as a SQLite traceback.
- **Database constraints** act as a safety net (`NOT NULL`, `UNIQUE`, `FOREIGN KEY`). Unique VIN violations are caught and shown to the user.
- **Excel export** — Template existence check, client selection guard, try/catch with `QMessageBox.critical()`, truncation warnings when data exceeds template limits.
- **Auto-update** — Every stage raises a typed error (`UpdateCheckError`, `UpdateDownloadError`, `UpdateApplyError`, `ManifestSchemaError`, etc.). The UI converts them to friendly status messages without exposing tracebacks.

---

## Development Guide

### Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

### Tests

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest -q
```

The full suite currently runs in ~50 s on a developer machine.

### Format + lint

```powershell
black src tests
isort src tests
flake8 src tests
```

`black` and `flake8` must both be clean — CI does not run in "informational" mode.

### Naming conventions

| Element     | Convention                       | Example                          |
| ----------- | -------------------------------- | -------------------------------- |
| Modules     | `lowercase_with_underscores`     | `excel_export.py`                |
| Classes     | `PascalCase`                     | `ClientsPage`, `ThemeManager`    |
| Functions   | `lowercase_with_underscores`     | `get_all_clients()`              |
| Constants   | `UPPER_CASE`                     | `LIGHT_THEME`, `TEMPLATES_DIR`   |
| Signals     | `lowercase_with_underscores`     | `data_changed`, `defects_changed`|

### Adding a new entity

1. Create `src/database/models/<entity>.py` with the canonical CRUD surface.
2. Register it in `src/database/models/__init__.py` (`init_database()` + `populate_mock_data()`).
3. Create `src/pages/<entity>.py` with `<Entity>Page` + `<Entity>Dialog`.
4. Register in `src/pages/__init__.py`.
5. Add the page to `MainWindow.pages` and the sidebar in `src/main.py`.
6. Add tests under `tests/database/test_<entity>_model.py` and `tests/ui/pages/test_<entity>_page.py`.

### Adding a new receipt section

1. Create the widget in `src/pages/receipts/` with a signal for data changes.
2. Instantiate in `ReceiptForm.setup_ui()` and connect the signal to a handler.
3. Update the `receipt_data` dict in the handler.
4. Update `excel_export.py` to write the new section into the template.
5. Add UI tests under `tests/ui/receipts/`.

---

## Testing

- **1228 tests / 2 skipped** at the time of this writing.
- Database tests run against an in-memory SQLite via the shared `tests/conftest.py` fixture.
- UI tests use `pytest-qt` with `QT_QPA_PLATFORM=offscreen`.
- Updater tests inject fakes via the seams `_run_schtasks` / `_popen` / fake `ManifestFetcher` / fake HTTP client — no real subprocesses or network access.
- The auto-update UI tests stub the QThread workers with synchronous equivalents to avoid Windows-specific `pytest-qt` race conditions while still asserting on the full happy/error paths.
- The Excel export tests cover layout invariants and section expansion: every code change that touches `excel_export.py` runs against ~1100 generated cells and asserts column alignment, total rows and TVA per line.

---

## Known Limitations

1. **Limited data validation** — VIN length is checked but not format; plate number is not enforced; no email / phone fields on clients.
2. **No undo / redo** — Destructive operations are immediate and permanent.
3. **Excel template constraints** — Max 5 defects per category, max 4 parts received; cell positions are hard-coded.
4. **Single-user, no authentication** — No access control.
5. **Simple search only** — Substring matching, no fuzzy search or advanced filtering.
6. **Single database file** — No support for multiple databases or profiles.
7. **No audit trail** — No change history for records.
8. **Windows-only auto-open** — `os.startfile()` for generated Excel files is Windows-specific.
9. **Windows-only auto-update** — The Scheduled Task / PowerShell helper path is Windows-only. The macOS / Linux pipeline currently stops at "downloaded" — the install swap is not implemented.
10. **Eager loading** — All pages load their data at startup; no pagination. Comfortable for up to ~10 000 records per table.

---

## Related Documentation

- [`COMMANDS.md`](./COMMANDS.md) — Day-to-day commands: setup, run, test, build, release, troubleshooting (including auto-update diagnostics).
- [`update-manifest.json`](./update-manifest.json) — Live auto-update manifest consumed by every installed copy.

---

## License

MIT License — see [`pyproject.toml`](./pyproject.toml).

## Repository

[https://github.com/eduard2276/neloaica](https://github.com/eduard2276/neloaica)
