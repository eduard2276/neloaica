"""Defects model and database operations."""

from ..connection import DatabaseConnection


def create_defects_table():
    """Create the defects table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            defect_name TEXT NOT NULL
        )
    """)
    db.commit()


def populate_defects_mock_data():
    """Populate defects with mock data."""
    db = DatabaseConnection()

    # Check if data already exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM defects")
    if existing and existing["count"] > 0:
        return  # Data already exists

    # Insert mock defects
    defects_list = [
        ("Engine misfiring",),
        ("Brake squealing",),
        ("Oil leak",),
        ("Check engine light on",),
        ("Transmission slipping",),
        ("Unusual noise from engine",),
        ("Steering wheel vibration",),
        ("AC not cooling",),
        ("Battery not charging",),
        ("Exhaust smoke",),
        ("Tire wear uneven",),
        ("Suspension noise",),
        ("Windshield wiper not working",),
        ("Headlight not working",),
        ("Dashboard warning light",),
    ]

    db.executemany("INSERT INTO defects (defect_name) VALUES (?)", defects_list)
    db.commit()


def get_all_defects() -> list[dict]:
    """Get all defects."""
    db = DatabaseConnection()
    return db.fetchall("SELECT id, defect_name FROM defects ORDER BY defect_name")


def get_defect_by_id(defect_id: int) -> dict | None:
    """Get a defect by ID."""
    db = DatabaseConnection()
    return db.fetchone("SELECT id, defect_name FROM defects WHERE id = ?", (defect_id,))


def add_defect(defect_name: str) -> int:
    """Add a new defect and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute("INSERT INTO defects (defect_name) VALUES (?)", (defect_name,))
    db.commit()
    return cursor.lastrowid


def get_defect_by_name(defect_name: str) -> dict | None:
    """Return the defect entry with this defect_name (case-insensitive), or None."""
    db = DatabaseConnection()
    return db.fetchone(
        "SELECT id, defect_name FROM defects WHERE LOWER(defect_name) = LOWER(?)",
        (defect_name,),
    )


def update_defect(defect_id: int, defect_name: str):
    """Update an existing defect."""
    db = DatabaseConnection()
    db.execute("UPDATE defects SET defect_name = ? WHERE id = ?", (defect_name, defect_id))
    db.commit()


def delete_defect(defect_id: int):
    """Delete a defect."""
    db = DatabaseConnection()
    db.execute("DELETE FROM defects WHERE id = ?", (defect_id,))
    db.commit()


def get_defects_count() -> int:
    """Get total number of defects."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM defects")
    return result["count"] if result else 0
