"""Labor/Service model and database operations."""

from ..connection import DatabaseConnection


def create_labor_table():
    """Create the labor table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS labor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL
        )
    """)
    db.commit()


def populate_labor_mock_data():
    """Populate labor with mock data."""
    db = DatabaseConnection()
    
    # Check if data already exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM labor")
    if existing and existing["count"] > 0:
        return  # Data already exists
    
    # Insert mock labor services
    services = [
        ("Oil Change",),
        ("Brake Pad Replacement",),
        ("Tire Rotation",),
        ("Wheel Alignment",),
        ("Battery Replacement",),
        ("Air Filter Replacement",),
        ("Spark Plug Replacement",),
        ("Transmission Fluid Change",),
        ("Coolant Flush",),
        ("Engine Diagnostic",),
        ("AC Recharge",),
        ("Timing Belt Replacement",),
    ]
    
    db.executemany(
        "INSERT INTO labor (service_name) VALUES (?)",
        services
    )
    db.commit()


def get_all_labor() -> list[dict]:
    """Get all labor services."""
    db = DatabaseConnection()
    return db.fetchall("SELECT id, service_name FROM labor ORDER BY service_name")


def get_labor_by_id(labor_id: int) -> dict | None:
    """Get a labor service by ID."""
    db = DatabaseConnection()
    return db.fetchone("SELECT id, service_name FROM labor WHERE id = ?", (labor_id,))


def add_labor(service_name: str) -> int:
    """Add a new labor service and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute(
        "INSERT INTO labor (service_name) VALUES (?)",
        (service_name,)
    )
    db.commit()
    return cursor.lastrowid


def get_labor_by_name(service_name: str) -> dict | None:
    """Return the labor entry with this service_name (case-insensitive), or None."""
    db = DatabaseConnection()
    return db.fetchone(
        "SELECT id, service_name FROM labor WHERE LOWER(service_name) = LOWER(?)",
        (service_name,),
    )


def update_labor(labor_id: int, service_name: str):
    """Update an existing labor service."""
    db = DatabaseConnection()
    db.execute(
        "UPDATE labor SET service_name = ? WHERE id = ?",
        (service_name, labor_id)
    )
    db.commit()


def delete_labor(labor_id: int):
    """Delete a labor service."""
    db = DatabaseConnection()
    db.execute("DELETE FROM labor WHERE id = ?", (labor_id,))
    db.commit()


def get_labor_count() -> int:
    """Get total number of labor services."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM labor")
    return result["count"] if result else 0
