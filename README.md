# Neloaica

**Automotive Service Management System**

A desktop database management application for small to medium automotive service businesses. Built with Python and PySide6 (Qt6), Neloaica provides a user-friendly interface for managing clients, vehicles, services, parts, defects, and generating service receipts with Excel export functionality.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Quick Start](#quick-start)
- [Technology Stack](#technology-stack)
- [Architecture Overview](#architecture-overview)
- [Main Components](#main-components)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Communication Patterns](#communication-patterns)
- [Startup Flow](#startup-flow)
- [Key Features](#key-features)
- [Development Guide](#development-guide)

---

## Project Overview

### Purpose
Track customer information, vehicle records, service catalogs, parts inventory, vehicle defects, and generate professional service receipts with Excel export capability.

### Domain
Automotive service shop management - handling the complete workflow from customer intake to receipt generation.

### Key Responsibilities
- **Client Management**: CRUD operations for customer records with address tracking
- **Vehicle Tracking**: Manage cars with VIN validation and client association
- **Service Catalog**: Maintain available labor/service types
- **Parts Inventory**: Track available automotive parts
- **Defects Registry**: Catalog vehicle defects (client-reported and discovered)
- **Receipt Generation**: Create comprehensive service receipts with Excel export
- **Settings Management**: Configure application settings (TVA/VAT rates)

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
- Initializes all tables
- Populates sample data for testing

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.9+ |
| GUI Framework | PySide6 (Qt6) | >= 6.6.0 |
| Database | SQLite3 | Built-in |
| Excel Export | openpyxl | >= 3.1.0 |

### Design Patterns Used
- **Singleton Pattern**: DatabaseConnection, ThemeManager
- **Model-View Architecture**: Separation of data layer and UI
- **Signal-Slot Pattern**: Qt's event communication system
- **Factory Pattern**: Theme style generators

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
│  │  • Defects  │  │  │ • Receipts Page (Complex)   │    │   │
│  │  • Receipts │  │  │ • Dashboard Page            │    │   │
│  │  • Dashboard│  │  │ • Settings Page             │    │   │
│  │  • Settings │  │  └─────────────────────────────┘    │   │
│  └─────────────┘  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ excel_export.py - Receipt Excel generation             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Database Models Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ clients  │ │   cars   │ │  labor   │ │  parts   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                  │
│  │ defects  │ │ settings │                                  │
│  └──────────┘ └──────────┘                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Database Connection (Singleton)                    │
│  • Thread-safe SQLite connection                             │
│  • Foreign key enforcement                                   │
│  • Row factory for dict results                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              SQLite Database (neloaica.db)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Main Components

### 1. UI Layer (`src/pages/`)

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `ClientsPage` | Customer management | CRUD, search, table view |
| `CarsPage` | Vehicle management | Client association, VIN tracking |
| `LaborPage` | Service catalog | Service type management |
| `PartsPage` | Parts inventory | Parts catalog management |
| `DefectsPage` | Defects registry | Defect tracking |
| `ReceiptsPage` | Receipt creation | Multi-section form, Excel export |
| `DashboardPage` | Statistics overview | Summary data display |
| `SettingsPage` | Configuration | TVA/VAT settings |

### 2. Receipts Subsystem (`src/pages/receipts/`)

The receipts module is the most complex component with multiple sub-widgets:

```
ReceiptsPage
├── ReceiptInfoWidget      - Customer & car selection
├── DefectsSectionWidget   - Client-reported defects (reusable)
├── DefectsSectionWidget   - Discovered defects (reusable)
├── PartsSectionWidget     - Parts received from client
├── LaborSectionWidget     - Labor services with total cost
├── BillablePartsSectionWidget - Parts used with pricing
└── Generate Button        - Excel export trigger
```

### 3. Services Layer (`src/services/`)

| Service | Purpose |
|---------|---------|
| `excel_export.py` | Generate Excel receipts from templates |

### 4. Styling System (`src/styles/`)

| Component | Purpose |
|-----------|---------|
| `theme_manager.py` | Singleton theme manager with 20+ style methods |
| `colors.py` | Color palette definitions (Light/Dark themes) |

### 5. Custom Widgets (`src/widgets/`)

| Widget | Purpose |
|--------|---------|
| `NoScrollComboBox` | ComboBox that prevents scroll wheel hijacking |

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐
│   CLIENTS   │───────│    CARS     │
├─────────────┤  1:N  ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ first_name  │       │ client_id   │──→ FK
│ last_name   │       │ plate_number│
│ address     │       │ vin         │
└─────────────┘       │ model       │
                      │ kilometers  │
                      └─────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    LABOR    │  │    PARTS    │  │   DEFECTS   │
├─────────────┤  ├─────────────┤  ├─────────────┤
│ id (PK)     │  │ id (PK)     │  │ id (PK)     │
│ service_name│  │ part_name   │  │ defect_name │
└─────────────┘  └─────────────┘  └─────────────┘

┌─────────────┐
│  SETTINGS   │
├─────────────┤
│ id (PK)=1   │  ← Singleton row
│ tva         │  ← VAT percentage
└─────────────┘
```

### Table Definitions

#### Clients
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO |
| first_name | TEXT | NOT NULL |
| last_name | TEXT | NOT NULL |
| address | TEXT | - |

#### Cars
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO |
| client_id | INTEGER | NOT NULL, FK → clients(id) CASCADE DELETE |
| plate_number | TEXT | NOT NULL |
| vin | TEXT | NOT NULL, UNIQUE |
| model | TEXT | NOT NULL |
| kilometers | INTEGER | DEFAULT 0 |

#### Labor
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO |
| service_name | TEXT | NOT NULL |

#### Parts
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO |
| part_name | TEXT | NOT NULL |

#### Defects
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTO |
| defect_name | TEXT | NOT NULL |

#### Settings
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, CHECK (id = 1) |
| tva | REAL | NOT NULL, DEFAULT 19.0 |

---

## Project Structure

```
Neloaica/
├── src/
│   ├── __init__.py
│   ├── main.py                      # Application entry point
│   │
│   ├── database/
│   │   ├── __init__.py              # Package exports
│   │   ├── connection.py            # Singleton DB connection
│   │   └── models/
│   │       ├── __init__.py          # Model exports & init_database()
│   │       ├── clients.py           # Client CRUD operations
│   │       ├── cars.py              # Car CRUD operations
│   │       ├── labor.py             # Labor CRUD operations
│   │       ├── parts.py             # Parts CRUD operations
│   │       ├── defects.py           # Defects CRUD operations
│   │       └── settings.py          # Settings (TVA) operations
│   │
│   ├── pages/
│   │   ├── __init__.py              # Page exports
│   │   ├── clients.py               # Clients management UI
│   │   ├── cars.py                  # Cars management UI
│   │   ├── labor.py                 # Services management UI
│   │   ├── parts.py                 # Parts management UI
│   │   ├── defects.py               # Defects management UI
│   │   ├── dashboard.py             # Statistics overview
│   │   ├── settings.py              # TVA configuration UI
│   │   └── receipts/
│   │       ├── __init__.py
│   │       ├── receipts.py          # Main receipts page
│   │       ├── receipt_info.py      # Customer/car selection
│   │       ├── defects_section.py   # Defects list widget
│   │       ├── parts_section.py     # Parts received widget
│   │       ├── labor_section.py     # Labor services widget
│   │       └── billable_parts_section.py  # Parts with pricing
│   │
│   ├── services/
│   │   ├── __init__.py              # Service exports
│   │   └── excel_export.py          # Excel generation logic
│   │
│   ├── styles/
│   │   ├── __init__.py              # Theme exports
│   │   ├── colors.py                # Color palette definitions
│   │   └── theme_manager.py         # Centralized styling (384 lines)
│   │
│   └── widgets/
│       ├── __init__.py              # Widget exports
│       └── combo_box.py             # NoScrollComboBox widget
│
├── templates/
│   └── Template-deviz.xlsx          # Excel receipt template
│
├── exports/
│   └── receipts/                    # Generated Excel receipts
│
├── tests/
│   ├── __init__.py
│   └── test_main.py
│
├── neloaica.db                      # SQLite database (runtime)
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata
└── README.md                        # This file
```

---

## Communication Patterns

### Internal Communication

#### Signal-Slot Pattern (Qt)
The application uses Qt's signal-slot mechanism for component communication:

```python
# Example from ReceiptsPage
self.defects_widget.defects_changed.connect(self.on_defects_changed)
self.labor_widget.labor_changed.connect(self.on_labor_changed)
self.billable_parts_widget.parts_changed.connect(self.on_billable_parts_changed)
```

#### Key Signals

| Component | Signal | Payload |
|-----------|--------|---------|
| `ReceiptInfoWidget` | `data_changed` | `dict` (customer/car info) |
| `DefectsSectionWidget` | `defects_changed` | `list[int]` (defect IDs) |
| `PartsSectionWidget` | `parts_changed` | `list[int]` (part IDs) |
| `LaborSectionWidget` | `labor_changed` | `list[int], float` (IDs, total cost) |
| `BillablePartsSectionWidget` | `parts_changed` | `list[dict], float` (parts data, total) |

### Data Flow

```
User Interaction
       ↓
Widget Signal Emission
       ↓
ReceiptsPage Signal Handler
       ↓
Update receipt_data dict
       ↓
Generate Excel (on button click)
       ↓
excel_export.py processes data
       ↓
Excel file created from template
```

---

## Startup Flow

### Initialization Sequence

```
1. Application Start (main.py)
   └─→ QApplication created
   
2. Database Initialization
   ├─→ init_database() called
   │   ├─→ create_clients_table()
   │   ├─→ create_cars_table()
   │   ├─→ create_labor_table()
   │   ├─→ create_parts_table()
   │   ├─→ create_defects_table()
   │   └─→ create_settings_table()
   │
   └─→ populate_mock_data() called
       ├─→ populate_clients_mock_data()
       ├─→ populate_cars_mock_data()
       ├─→ populate_labor_mock_data()
       ├─→ populate_parts_mock_data()
       └─→ populate_defects_mock_data()

3. Main Window Creation
   ├─→ QStackedWidget (pages container)
   │   ├─→ ClientsPage()
   │   ├─→ CarsPage()
   │   ├─→ LaborPage()
   │   ├─→ PartsPage()
   │   ├─→ DefectsPage()
   │   ├─→ ReceiptsPage()
   │   ├─→ DashboardPage()
   │   └─→ SettingsPage()
   │
   └─→ Sidebar()
       └─→ Navigation list (currentRowChanged signal)

4. Window Display
   └─→ mainWindow.show()
       └─→ app.exec()
```

### Database Connection (Singleton)

```python
class DatabaseConnection:
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

---

## Key Features

### Receipt Generation

The receipt system creates Excel documents from a template with the following data mapping:

| Excel Cell | Data |
|------------|------|
| B10 | Client name |
| D10 | Car model |
| F10 | Kilometers |
| E11 | Plate number |
| E12 | VIN |
| B12 | Client address |
| A14-A18 | Client-reported defects (max 5) |
| A20-A24 | Discovered defects (max 5) |
| C14-C17 | Parts received from client (max 4) |
| B36+ | Labor services (dynamic rows) |
| E(labor end) | Total labor cost |
| F(labor end) | Labor TVA |
| B42+ | Billable parts (dynamic rows) |
| C | Units |
| D | Price per unit |
| E | Part total |
| F | Part TVA |

### TVA Calculation

TVA is extracted from prices that already include tax:

```python
tva = (price * tva_percentage) / (100 + tva_percentage)
```

### Theme System

Centralized styling with 20+ component methods:

```python
theme.page_title()      # Page header styles
theme.combobox()        # Dropdown styles
theme.button("success") # Button variants
theme.groupbox()        # Section containers
theme.table()           # Data tables
# ... and more
```

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

### Adding a New Page

1. Create model in `src/database/models/`
2. Add table creation to `init_database()`
3. Create page UI in `src/pages/`
4. Register in `src/pages/__init__.py`
5. Add to `main.py` pages stack and sidebar

### Adding New Theme Styles

Add methods to `ThemeManager` class in `src/styles/theme_manager.py`:

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

## Performance Notes

- Optimized for < 10,000 records per table
- All data loaded into memory on page load
- Real-time search with substring matching
- No pagination (suitable for small to medium datasets)

---

## Database Location

- **Development Mode**: `neloaica.db` in project root
- **Frozen Executable**: `neloaica.db` in executable directory

---

## License

MIT License

---

## Repository

https://github.com/eduard2276/neloaica.git
