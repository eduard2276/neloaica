# Neloaica - Project Summary

## 1. Project Overview

### Purpose
Neloaica is a desktop database management application designed for managing automotive service-related data. It provides a user-friendly graphical interface for tracking clients, their vehicles (cars), and labor/service offerings.

### Domain
**Business Domain**: Automotive Service Management  
**Problem Space**: Small to medium automotive service businesses need a simple, local database application to manage customer information, vehicle records, and service catalogs without complex cloud dependencies.

### Key Responsibilities
- **Client Management**: Store and manage customer information (names, addresses)
- **Vehicle Management**: Track vehicles associated with clients (plate numbers, VINs, models, mileage)
- **Service Catalog**: Maintain a catalog of available labor/service types
- **Data Persistence**: Local SQLite database for reliable data storage
- **User Interface**: Intuitive GUI for CRUD operations and data visualization

### Technology Stack
- **Language**: Python 3.9+
- **GUI Framework**: PySide6 (Qt6) >= 6.6.0
- **Database**: SQLite3 (built-in Python module)
- **Architecture Pattern**: Model-View pattern with Singleton database connection
- **Build System**: setuptools with pyproject.toml configuration
- **Development Tools**: pytest, black, isort, flake8

---

## 2. Main Components

### Component List

```
Neloaica/
├── src/
│   ├── __init__.py                          # Marks src as Python package
│   ├── main.py                              # Application entry point
│   │                                        # Contains: MainWindow, Sidebar, main()
│   │
│   ├── database/                            # Data access layer
│   │   ├── __init__.py                      # Exports: init_database, populate_mock_data
│   │   ├── connection.py                    # Singleton DatabaseConnection class
│   │   │
│   │   └── models/                          # Domain models (per-table modules)
│   │       ├── __init__.py                  # Aggregates all model functions
│   │       ├── clients.py                   # Client CRUD + table creation
│   │       ├── cars.py                      # Car CRUD + table creation
│   │       └── labor.py                     # Labor CRUD + table creation
│   │
│   └── pages/                               # UI components (one file per page)
│       ├── __init__.py                      # Exports: all Page classes
│       ├── clients.py                       # ClientsPage + ClientDialog
│       ├── cars.py                          # CarsPage + CarDialog
│       ├── labor.py                         # LaborPage + LaborDialog
│       ├── dashboard.py                     # DashboardPage + StatCard
│       └── settings.py                      # SettingsPage
│
├── venv/                                    # Virtual environment (git-ignored)
├── neloaica.db                              # SQLite database (runtime, git-ignored)
├── requirements.txt                         # Production dependencies
├── pyproject.toml                           # Project metadata
├── README.md                                # Setup & usage documentation
└── NELOAICA.md                              # This file
```

### Component Purposes

#### **Main Application (`src/main.py`)**
- **MainWindow**: Primary application window managing layout and navigation
- **Sidebar**: Navigation component with page selection
- **Application Bootstrap**: Database initialization and window setup

#### **Database Layer (`src/database/`)**
- **DatabaseConnection** (`connection.py`): Singleton pattern connection manager
  - Manages SQLite connection lifecycle
  - Provides query execution methods
  - Handles row-to-dictionary conversion
  - Enforces foreign key constraints
  
- **Models** (`models/`): Data access layer with separate model files
  - **clients.py**: Client entity (id, first_name, last_name, address)
  - **cars.py**: Car entity (id, client_id FK, plate_number, vin, model, kilometers)
  - **labor.py**: Service entity (id, service_name)
  - **__init__.py**: Aggregates all models and provides `init_database()` and `populate_mock_data()`

#### **UI Layer (`src/pages/`)**
- **ClientsPage**: Full CRUD interface for clients with search functionality
- **CarsPage**: Full CRUD interface for cars with client dropdown and VIN validation
- **LaborPage**: Full CRUD interface for services with search
- **DashboardPage**: Statistics overview (card-based metrics display)
- **SettingsPage**: Configuration placeholder (mock implementation)

Each page follows a consistent pattern:
- Table widget for data display
- Search bar with real-time filtering
- CRUD action buttons (Add/Edit/Delete)
- Dialog-based forms for data entry/editing
- Styled confirmation dialogs for destructive actions

### Component Hierarchy

```
Application Layer (main.py)
    ↓
┌──────────────────────────────────────────┐
│   MainWindow (QMainWindow)               │
│   ├── Sidebar (Navigation)               │
│   └── QStackedWidget (Page Container)    │
│       ├── ClientsPage                     │
│       ├── CarsPage                        │
│       ├── LaborPage                       │
│       ├── DashboardPage                   │
│       └── SettingsPage                    │
└──────────────────────────────────────────┘
    ↓ (calls)
Data Access Layer (database/models/)
    ├── clients module
    ├── cars module
    └── labor module
    ↓ (uses)
Database Connection Layer (database/connection.py)
    ↓ (manages)
SQLite Database (neloaica.db)
```

**Layering Rules**:
- UI pages depend on models (data access functions)
- Models depend on DatabaseConnection singleton
- DatabaseConnection manages SQLite connection
- No circular dependencies
- Clear separation of concerns

---

## 3. Communication Patterns

### Internal Communication

#### **UI to Data Layer**
- **Pattern**: Direct function calls to model modules
- **Example**: `ClientsPage` calls `get_all_clients()`, `add_client()`, `update_client()`, `delete_client()`
- **Data Flow**: UI → Model Function → DatabaseConnection → SQLite

```python
# Example: ClientsPage loading data
from src.database.models import get_all_clients

class ClientsPage:
    def load_data(self):
        self.all_clients = get_all_clients()  # Direct function call
        self.display_clients(self.all_clients)
```

#### **Navigation Pattern**
- **Pattern**: Signal/Slot mechanism (Qt)
- **Implementation**: Sidebar's `QListWidget.currentRowChanged` signal connects to `MainWindow.change_page()` slot
- **Purpose**: Decouples navigation UI from page switching logic

```python
self.nav_list.currentRowChanged.connect(self.on_page_changed)
```

#### **Database Access Pattern**
- **Pattern**: Singleton with method-based API
- **Thread Safety**: `check_same_thread=False` for SQLite connection
- **API Methods**:
  - `execute()`: Single query execution
  - `executemany()`: Batch operations
  - `fetchall()`: Returns list of dictionaries
  - `fetchone()`: Returns single dictionary
  - `commit()`: Explicit transaction commit

#### **Dialog Pattern**
- **Pattern**: Modal dialog with validation
- **Flow**: 
  1. Page creates dialog instance with optional data
  2. Dialog displays form (`exec()` blocks)
  3. User submits or cancels
  4. Dialog validates input
  5. Page retrieves data via `get_data()` method
  6. Page calls model CRUD function

```python
dialog = ClientDialog(self, client_data)
if dialog.exec() == QDialog.DialogCode.Accepted:
    data = dialog.get_data()
    update_client(client_id, **data)
    self.load_data()  # Refresh display
```

### External Communication

**Note**: This application is fully self-contained with no external communication.

- **No Network APIs**: Application operates entirely locally
- **No External Services**: All data stored in local SQLite database
- **No IPC**: Single-process application
- **Database File**: Only external artifact is `neloaica.db` file

**Future Extension Points**:
- Could add REST API client for cloud synchronization
- Could implement export/import (CSV, JSON) functionality
- Could add backup to external storage

---

## 4. Thread Usage & Concurrency

### Threading Model
**Single-Threaded Application**

- **Main Thread**: Qt event loop handles all UI and database operations
- **Rationale**: 
  - SQLite performs well for small-scale desktop applications
  - UI operations are non-blocking for this use case
  - Avoids complexity of thread synchronization

### Concurrency Primitives
- **None explicitly used** in application code
- **SQLite Locking**: Database-level locking handled by SQLite engine
- **Qt Event Loop**: Handles asynchronous UI events (button clicks, text changes)

### Database Connection Thread Safety
```python
self._connection = sqlite3.connect(
    str(self._db_path),
    check_same_thread=False  # Allow connection sharing
)
```

**Note**: `check_same_thread=False` is set, but application currently uses only main thread. This setting allows for future multi-threaded access if needed.

### Future Concurrency Considerations

If application scales to handle long-running operations:

**Recommended Pattern**: QThread for database operations
```python
# Future pattern (not implemented)
class DatabaseWorker(QThread):
    def run(self):
        # Perform database query in background
        results = get_all_clients()
        self.finished.emit(results)
```

**When to Consider Threading**:
- Large dataset queries (>10,000 records)
- Export/import operations
- Database backup/restore
- Network synchronization

---

## 5. Architecture Variants

### Current Architecture
**Single-Variant Desktop Application**

This application currently has **no architecture variants**. It runs identically across all platforms.

### Deployment Environment
- **Local Desktop**: Windows, macOS, Linux
- **Database Location**: Same directory as application executable/script
- **Configuration**: Hardcoded in source (no variant-specific config files)

### Platform-Specific Behavior

The only variant behavior is **database path resolution**:

```python
def _get_db_path(self) -> Path:
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller, cx_Freeze)
        app_dir = Path(sys.executable).parent
    else:
        # Running as Python script
        app_dir = Path(__file__).parent.parent.parent
    return app_dir / "neloaica.db"
```

**Variants**:
- **Development Mode** (`python -m src.main`): Database in project root
- **Frozen Executable** (compiled): Database in executable directory

### Future Architecture Extensions

**Potential Variants**:
1. **Server-Client Mode**: Central database server with multiple client instances
2. **Cloud-Synced Mode**: Local database with cloud backup/sync
3. **Multi-Tenant Mode**: Separate database per business/location
4. **Read-Only Mode**: For reporting/viewing without edit permissions

**Configuration Strategy for Variants**:
- Create `config/` directory with variant-specific settings
- Use environment variables for deployment configuration
- Implement configuration loader in database connection

---

## 6. Startup Flow

### Initialization Sequence

```
1. Python Interpreter Launches
   ↓
2. main.py: __main__ block executes
   ↓
3. main() function called
   ↓
4. QApplication instance created
   ├── Sets application metadata (name, org, version)
   └── Initializes Qt framework
   ↓
5. Database Initialization
   ├── init_database() called
   │   ├── create_clients_table()
   │   ├── create_cars_table()
   │   └── create_labor_table()
   └── populate_mock_data() called
       ├── populate_clients_mock_data() (10 mock clients)
       ├── populate_cars_mock_data() (11 mock cars)
       └── populate_labor_mock_data() (12 mock services)
   ↓
6. MainWindow Construction
   ├── Create QStackedWidget
   ├── Instantiate all pages
   │   ├── ClientsPage()
   │   │   └── load_data() → fetch all clients
   │   ├── CarsPage()
   │   │   └── load_data() → fetch all cars
   │   ├── LaborPage()
   │   │   └── load_data() → fetch all services
   │   ├── DashboardPage()
   │   │   └── load_data() → fetch statistics
   │   └── SettingsPage()
   ├── Create Sidebar
   │   └── Connect navigation signals
   └── Setup layout (sidebar + content area)
   ↓
7. window.show() - Display main window
   ↓
8. app.exec() - Enter Qt event loop
   ↓
9. Application Running (event-driven)
   └── Wait for user interactions
```

### Detailed Startup Steps

#### Step 1-3: Python Bootstrap
```python
if __name__ == "__main__":
    main()
```
- Script entry point
- Ensures `main()` only runs when script executed directly

#### Step 4: Qt Application Setup
```python
app = QApplication(sys.argv)
app.setApplicationName("Neloaica")
app.setOrganizationName("Nokia")
app.setApplicationVersion("1.0.0")
```
- Creates Qt application instance
- Sets metadata for platform integration
- Initializes Qt's internal state

#### Step 5: Database Bootstrap
```python
init_database()      # Creates tables if not exist
populate_mock_data() # Adds data only if tables empty
```

**Key Behavior**:
- **Idempotent**: Safe to run multiple times
- **Schema Creation**: Uses `CREATE TABLE IF NOT EXISTS`
- **Data Population**: Checks row count before inserting mock data
- **Database Connection**: Singleton instance created on first use

#### Step 6: UI Construction
```python
window = MainWindow()
```
- MainWindow `__init__` creates all pages immediately
- Each page loads its data during construction
- Pages query database during `__init__` → `load_data()`

**Performance Note**: All pages load data at startup, even non-visible ones. For large datasets, consider lazy loading.

#### Step 7-8: Event Loop
```python
window.show()        # Make window visible
sys.exit(app.exec()) # Block until app closes
```
- `show()` triggers paint events
- `exec()` enters Qt's event loop (blocks until quit)
- Returns exit code to operating system

### Ready State
**Application is ready when**:
- MainWindow is visible on screen
- All pages have loaded initial data
- Sidebar shows "Clients" page selected (index 0)
- User can interact with UI

**No explicit "ready" signal** - application is immediately interactive after `show()`.

---

## 7. File Relationship & Folder Structure

### Directory Layout

```
Neloaica/                                    # Project root
│
├── src/                                     # Source code package
│   ├── __init__.py                          # Marks src as Python package
│   ├── main.py                              # Application entry point
│   │                                        # Contains: MainWindow, Sidebar, main()
│   │
│   ├── database/                            # Data access layer
│   │   ├── __init__.py                      # Exports: init_database, populate_mock_data
│   │   ├── connection.py                    # Singleton DatabaseConnection class
│   │   │
│   │   └── models/                          # Domain models (per-table modules)
│   │       ├── __init__.py                  # Aggregates all model functions
│   │       ├── clients.py                   # Client CRUD + table creation
│   │       ├── cars.py                      # Car CRUD + table creation
│   │       └── labor.py                     # Labor CRUD + table creation
│   │
│   └── pages/                               # UI components (one file per page)
│       ├── __init__.py                      # Exports: all Page classes
│       ├── clients.py                       # ClientsPage + ClientDialog
│       ├── cars.py                          # CarsPage + CarDialog
│       ├── labor.py                         # LaborPage + LaborDialog
│       ├── dashboard.py                     # DashboardPage + StatCard
│       └── settings.py                      # SettingsPage
│
├── venv/                                    # Virtual environment (git-ignored)
│   └── ...                                  # Python packages installed here
│
├── neloaica.db                              # SQLite database (runtime, git-ignored)
│
├── requirements.txt                         # Production dependencies (pip)
├── pyproject.toml                           # Project metadata (PEP 621)
├── README.md                                # Setup & usage documentation
├── .gitignore                               # Git exclusions (venv/, *.db, __pycache__)
└── NELOAICA.md                              # This file
```

### Module Organization Principles

#### **Package Structure**
- **Flat within categories**: Each category (`database/`, `pages/`) contains modules directly
- **No deep nesting**: Maximum 3 levels deep (`src/database/models/clients.py`)
- **Clear separation**: Database logic never imports UI, UI imports database

#### **Naming Conventions**
- **Modules**: lowercase_with_underscores (e.g., `connection.py`)
- **Classes**: PascalCase (e.g., `ClientsPage`, `DatabaseConnection`)
- **Functions**: lowercase_with_underscores (e.g., `get_all_clients()`)
- **Constants**: UPPER_CASE (not currently used in project)

### Key Files & Their Purposes

#### **src/main.py** (153 lines)
- **Purpose**: Application entry point
- **Key Classes**:
  - `MainWindow(QMainWindow)`: Top-level window with sidebar and page container
  - `Sidebar(QWidget)`: Navigation component
- **Key Function**: `main()` - bootstrap sequence
- **Dependencies**: All page classes, database initialization

#### **src/database/connection.py** (87 lines)
- **Purpose**: Singleton database connection manager
- **Key Class**: `DatabaseConnection`
- **Pattern**: Singleton via `__new__` override
- **Features**: 
  - Row factory for dict results
  - Foreign key enforcement
  - Path resolution for dev/frozen modes

#### **src/database/models/*.py** (70-120 lines each)
- **Purpose**: Data access layer per entity
- **Functions per model**:
  - `create_<entity>_table()`: DDL for schema creation
  - `populate_<entity>_mock_data()`: Insert demo data
  - `get_all_<entity>()`: Read all records
  - `get_<entity>_by_id()`: Read single record
  - `add_<entity>()`: Insert new record
  - `update_<entity>()`: Modify existing record
  - `delete_<entity>()`: Remove record
  - `get_<entity>_count()`: Aggregate query

#### **src/pages/*.py** (400-600 lines each for CRUD pages)
- **Purpose**: UI implementation per page
- **Key Classes**:
  - `<Entity>Page(QWidget)`: Main page widget with table and toolbar
  - `<Entity>Dialog(QDialog)`: Form for add/edit operations
- **Pattern**: Each page self-contained with its own dialog

### Import Relationships

```
main.py
  ↓ imports
  ├── pages/__init__.py → (ClientsPage, CarsPage, LaborPage, DashboardPage, SettingsPage)
  └── database/__init__.py → (init_database, populate_mock_data)

pages/clients.py
  ↓ imports
  └── database/models/__init__.py → (get_all_clients, add_client, update_client, delete_client)

database/models/__init__.py
  ↓ imports
  ├── models/clients.py → (create_clients_table, populate_clients_mock_data, get_all_clients, ...)
  ├── models/cars.py → (create_cars_table, populate_cars_mock_data, get_all_cars, ...)
  └── models/labor.py → (create_labor_table, populate_labor_mock_data, get_all_labor, ...)

database/models/clients.py
  ↓ imports
  └── database/connection.py → (DatabaseConnection)
```

**Dependency Rules**:
- ✅ Pages may import models
- ✅ Models may import DatabaseConnection
- ❌ Database layer may NOT import pages
- ❌ No circular imports

### Configuration Files

#### **requirements.txt**
```txt
PySide6>=6.6.0
```
- Minimal production dependencies
- Used with: `pip install -r requirements.txt`

#### **pyproject.toml**
- **Standard**: PEP 621 (modern Python packaging)
- **Sections**:
  - `[build-system]`: setuptools configuration
  - `[project]`: Metadata (name, version, description, dependencies)
  - `[project.optional-dependencies]`: Dev tools (pytest, black, isort, flake8)
  - `[project.scripts]`: Entry point (`neloaica` command)
  - `[tool.*]`: Tool-specific config (black, isort, pytest)

### Build Artifacts & Runtime Files

**Generated at Runtime**:
- `neloaica.db`: SQLite database file (created in project root or executable dir)
- `__pycache__/`: Compiled Python bytecode (`.pyc` files)

**Git Ignored** (via `.gitignore`):
- `venv/`: Virtual environment
- `*.db`: Database files
- `__pycache__/`: Bytecode cache
- `*.pyc`, `*.pyo`: Compiled Python files
- `.pytest_cache/`: Test cache

---

## 8. Additional Context

### Design Patterns

#### **Singleton Pattern** (DatabaseConnection)
```python
class DatabaseConnection:
    _instance: Optional["DatabaseConnection"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
- **Purpose**: Ensure single database connection across application
- **Benefit**: Connection pooling not needed; simple lifecycle management

#### **Dialog Pattern** (CRUD Forms)
- Each entity has a dedicated dialog class
- Dialog validates input before accepting
- Parent page retrieves data via `get_data()` method
- Consistent styling and behavior across all dialogs

#### **Table-View Pattern** (Data Display)
- QTableWidget displays records
- Real-time search filtering
- Row selection for edit/delete operations
- Consistent row styling

#### **Facade Pattern** (models/__init__.py)
```python
# models/__init__.py aggregates all models
from .clients import get_all_clients, add_client, ...
from .cars import get_all_cars, add_car, ...
from .labor import get_all_labor, add_labor, ...
```
- **Purpose**: Single import point for all data access functions
- **Benefit**: UI pages don't need to know individual model file locations

### Database Schema

#### **Clients Table**
```sql
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    address TEXT
)
```
- 10 mock records on first run

#### **Cars Table**
```sql
CREATE TABLE cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plate_number TEXT NOT NULL,
    vin TEXT NOT NULL UNIQUE,           -- 17-character VIN
    model TEXT NOT NULL,
    kilometers INTEGER DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
)
```
- 11 mock records on first run
- Cascade delete: removing client removes their cars

#### **Labor Table**
```sql
CREATE TABLE labor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL
)
```
- 12 mock service records on first run

### UI Styling Approach

**Color Scheme** (Flat Design):
- **Primary**: `#3498db` (blue) - accents, selected states
- **Success**: `#2ecc71` (green) - Add buttons
- **Danger**: `#e74c3c` (red) - Delete buttons
- **Dark**: `#2c3e50` (dark blue-gray) - sidebar, headers
- **Light**: `#ecf0f1` (very light gray) - content background
- **White**: `#ffffff` - cards, tables, inputs

**Styling Method**: Inline Qt stylesheets (CSS-like syntax)
```python
widget.setStyleSheet("""
    QWidget {
        background-color: #ecf0f1;
        border-radius: 8px;
    }
""")
```

**Consistency**: All pages follow same visual design language:
- 8px border radius for modern look
- Emoji icons for visual navigation
- Bold headers with large font
- Consistent spacing (15-20px)

### Error Handling Strategy

**Current Approach**: Minimal explicit error handling

**Validation**:
- Dialog-level validation for required fields
- Database constraints (NOT NULL, UNIQUE, FOREIGN KEY)
- User-facing error messages via `QMessageBox.warning()`

**Database Errors**:
- SQLite exceptions propagate to caller
- UNIQUE constraint violations caught in some CRUD operations (VIN uniqueness)

**Recommended Enhancements**:
```python
# Future pattern
try:
    add_car(client_id, plate, vin, model, km)
except sqlite3.IntegrityError as e:
    if "UNIQUE constraint failed" in str(e):
        QMessageBox.warning(self, "Error", "VIN already exists")
    elif "FOREIGN KEY constraint failed" in str(e):
        QMessageBox.warning(self, "Error", "Invalid client selected")
```

### Logging

**Current State**: No logging framework implemented

**Future Logging Strategy**:
```python
import logging

# Configure in main()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neloaica.log'),
        logging.StreamHandler()
    ]
)

# Use in modules
logger = logging.getLogger(__name__)
logger.info("Database initialized")
logger.error("Failed to load clients", exc_info=True)
```

### Performance Considerations

**Current Performance**:
- **Suitable for**: < 10,000 records per table
- **Bottlenecks**: 
  - Loading all data into memory (no pagination)
  - Re-querying database on every `load_data()` call
  - No caching of static data (client dropdown in car form)

**Optimization Opportunities**:
1. **Pagination**: Implement page-based loading for large tables
2. **Lazy Loading**: Load page data only when page is shown
3. **Caching**: Cache dropdown options and invalidate on changes
4. **Indexing**: Add database indexes for search fields
```sql
CREATE INDEX idx_clients_name ON clients(last_name, first_name);
CREATE INDEX idx_cars_vin ON cars(vin);
```

### Known Limitations

1. **No Data Validation**:
   - VIN format not validated (should be 17 characters)
   - Plate number format not enforced
   - No email/phone validation for clients

2. **No Undo/Redo**: Destructive operations are immediate and permanent

3. **No Data Export**: No CSV/Excel export functionality

4. **No User Authentication**: Single-user application with no access control

5. **No Data Backup**: No automated backup mechanism

6. **Search Limitations**:
   - Simple substring matching only
   - No fuzzy search or advanced filtering

7. **Single Database File**: No support for multiple databases or profiles

8. **No Audit Trail**: No history of changes to records

### Testing Strategy (Future)

**Recommended Test Structure**:
```
tests/
├── __init__.py
├── test_database/
│   ├── test_connection.py
│   ├── test_clients_model.py
│   ├── test_cars_model.py
│   └── test_labor_model.py
├── test_pages/
│   ├── test_clients_page.py
│   ├── test_cars_page.py
│   └── test_labor_page.py
└── fixtures/
    └── conftest.py
```

**Test Categories**:
- **Unit Tests**: Model CRUD functions with in-memory database
- **Integration Tests**: Full database operations with temporary file
- **UI Tests**: pytest-qt for widget interactions
- **End-to-End Tests**: Full workflow tests (add client → add car → verify)

---

## Summary for AI Context

This application is a **single-threaded, desktop database management tool** built with Python and Qt6. It follows a **layered architecture** with clear separation between UI (pages), data access (models), and storage (SQLite).

**Key architectural decisions**:
- Singleton database connection for simplicity
- Per-entity model modules for scalability
- Consistent dialog-based forms across all CRUD operations
- Inline stylesheets for visual consistency
- Mock data auto-population for easy testing

**Primary use cases**:
1. Managing client records
2. Tracking vehicles per client
3. Maintaining service catalog

**Extension points**:
- Add new entity: Create model file + page file + add to navigation
- Add new field: Modify table creation + dialog form + table display
- Add export: Implement CSV writer in model layer
- Add authentication: Wrap main window in login dialog

**Code generation guidelines**:
- Follow existing naming conventions (lowercase_with_underscores)
- Use type hints for function signatures
- Keep model functions pure (no UI code)
- Maintain consistent styling patterns
- Include docstrings for public functions
- Use Qt's signal/slot for event handling
- Validate user input in dialogs before accepting
