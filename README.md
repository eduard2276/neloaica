# Neloaica

**Automotive Service Management System**

A desktop database management application for small to medium automotive service businesses. Built with Python and PySide6 (Qt6), Neloaica provides a user-friendly interface for managing clients, vehicles, services, parts, and defects without complex cloud dependencies.

## Overview

**Purpose**: Track customer information, vehicle records, service catalogs, parts inventory, and vehicle defects in a simple, local database application.

**Technology Stack**:
- Python 3.9+
- PySide6 (Qt6) >= 6.6.0
- SQLite3 (local database)
- Model-View architecture with Singleton pattern

## Database Schema

The application uses SQLite to manage five primary data tables:

### 1. **Clients Table**
Stores customer information.

| Column      | Type    | Constraints           |
|-------------|---------|----------------------|
| id          | INTEGER | PRIMARY KEY, AUTO    |
| first_name  | TEXT    | NOT NULL             |
| last_name   | TEXT    | NOT NULL             |
| address     | TEXT    | -                    |

### 2. **Cars Table**
Tracks vehicles associated with clients.

| Column        | Type    | Constraints                    |
|---------------|---------|-------------------------------|
| id            | INTEGER | PRIMARY KEY, AUTO             |
| client_id     | INTEGER | NOT NULL, FOREIGN KEY         |
| plate_number  | TEXT    | NOT NULL                      |
| vin           | TEXT    | NOT NULL, UNIQUE              |
| model         | TEXT    | NOT NULL                      |
| kilometers    | INTEGER | DEFAULT 0                     |

**Relationships**: 
- Foreign key to `clients(id)` with CASCADE DELETE
- One client can have multiple cars

### 3. **Labor Table**
Maintains available service types.

| Column       | Type    | Constraints           |
|--------------|---------|-----------------------|
| id           | INTEGER | PRIMARY KEY, AUTO     |
| service_name | TEXT    | NOT NULL              |

### 4. **Parts Table**
Inventory of available parts.

| Column     | Type    | Constraints           |
|------------|---------|-----------------------|
| id         | INTEGER | PRIMARY KEY, AUTO     |
| part_name  | TEXT    | NOT NULL              |

### 5. **Defects Table**
Catalog of common vehicle defects.

| Column       | Type    | Constraints           |
|--------------|---------|-----------------------|
| id           | INTEGER | PRIMARY KEY, AUTO     |
| defect_name  | TEXT    | NOT NULL              |

## Application Structure

### Architecture Overview

```
┌─────────────────────────────────────┐
│  Main Window (Qt GUI)               │
│  ├─ Sidebar Navigation              │
│  └─ Page Container                  │
│      ├─ Clients Page                │
│      ├─ Cars Page                   │
│      ├─ Labor Page                  │
│      ├─ Parts Page                  │
│      ├─ Defects Page                │
│      ├─ Dashboard Page              │
│      └─ Settings Page               │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  Database Models Layer              │
│  ├─ clients.py                      │
│  ├─ cars.py                         │
│  ├─ labor.py                        │
│  ├─ parts.py                        │
│  └─ defects.py                      │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  Database Connection (Singleton)    │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  SQLite Database (neloaica.db)      │
└─────────────────────────────────────┘
```

### Project Structure

```
Neloaica/
├── src/
│   ├── main.py                      # Application entry point
│   ├── database/
│   │   ├── connection.py            # Singleton DB connection
│   │   └── models/                  # Data access layer
│   │       ├── clients.py           # Client CRUD operations
│   │       ├── cars.py              # Car CRUD operations
│   │       ├── labor.py             # Labor CRUD operations
│   │       ├── parts.py             # Parts CRUD operations
│   │       └── defects.py           # Defects CRUD operations
│   └── pages/                       # UI components
│       ├── clients.py               # Clients management UI
│       ├── cars.py                  # Cars management UI
│       ├── labor.py                 # Services management UI
│       ├── parts.py                 # Parts management UI
│       ├── defects.py               # Defects management UI
│       ├── dashboard.py             # Statistics overview
│       └── settings.py              # Configuration
├── neloaica.db                      # SQLite database (runtime)
├── requirements.txt                 # Dependencies
└── pyproject.toml                   # Project metadata
```

## Key Features

- **Client Management**: Add, edit, delete, and search customer records
- **Vehicle Tracking**: Manage cars with VIN validation and client association
- **Service Catalog**: Maintain list of available labor/service types
- **Parts Inventory**: Track available automotive parts
- **Defects Registry**: Catalog common vehicle defects
- **Dashboard**: View statistics and overview
- **Real-time Search**: Filter records across all pages
- **Local Storage**: All data stored in local SQLite database

## Setup & Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package installer)

### Installation Steps

1. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**
   ```bash
   python -m src.main
   ```

## Usage

### First Launch
On first launch, the application automatically:
- Creates the SQLite database (`neloaica.db`)
- Initializes all tables
- Populates sample data for testing

### Navigation
Use the sidebar to navigate between:
- 👥 **Clients** - Manage customer information
- 🚗 **Cars** - Track vehicles and their details
- ⚙️ **Labor** - Maintain service catalog
- 🔧 **Parts** - Manage parts inventory
- ⚠️ **Defects** - Track common defects
- 📊 **Dashboard** - View statistics
- ⚙️ **Settings** - Configure application

### CRUD Operations
Each page provides:
- **Search bar** for filtering records
- **Add button** to create new entries
- **Edit button** to modify selected entries
- **Delete button** to remove entries (with confirmation)
- **Double-click** on table rows to edit

## Design Principles

- **Layered Architecture**: Clear separation between UI, data access, and storage
- **Singleton Pattern**: Single database connection managed centrally
- **Consistent UI**: Uniform styling and behavior across all pages
- **Data Validation**: Input validation at dialog level and database constraints
- **Mock Data**: Auto-populated sample data for testing and demonstration

## Development

### Code Structure
- **Models**: Pure data access functions (no UI code)
- **Pages**: UI components with table displays and dialogs
- **Dialogs**: Modal forms for data entry with validation

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

## Database Location

- **Development Mode**: `neloaica.db` in project root
- **Frozen Executable**: `neloaica.db` in executable directory

## Performance Notes

- Optimized for < 10,000 records per table
- All data loaded into memory on page load
- Real-time search with substring matching
- No pagination (suitable for small to medium datasets)

## License

MIT License
