"""Parts model and database operations."""

from ..connection import DatabaseConnection


def create_parts_table():
    """Create the parts table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_name TEXT NOT NULL
        )
    """)
    db.commit()


def populate_parts_mock_data():
    """Populate parts with mock data."""
    db = DatabaseConnection()

    # Check if data already exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM parts")
    if existing and existing["count"] > 0:
        return  # Data already exists

    # Insert mock parts
    parts_list = [
        ("Brake Pads",),
        ("Oil Filter",),
        ("Air Filter",),
        ("Spark Plugs",),
        ("Battery",),
        ("Wiper Blades",),
        ("Timing Belt",),
        ("Serpentine Belt",),
        ("Coolant",),
        ("Transmission Fluid",),
        ("Brake Fluid",),
        ("Power Steering Fluid",),
        ("Headlight Bulb",),
        ("Tail Light Bulb",),
        ("Cabin Air Filter",),
    ]

    db.executemany("INSERT INTO parts (part_name) VALUES (?)", parts_list)
    db.commit()


def get_all_parts() -> list[dict]:
    """Get all parts."""
    db = DatabaseConnection()
    return db.fetchall("SELECT id, part_name FROM parts ORDER BY part_name")


def get_part_by_id(part_id: int) -> dict | None:
    """Get a part by ID."""
    db = DatabaseConnection()
    return db.fetchone("SELECT id, part_name FROM parts WHERE id = ?", (part_id,))


def add_part(part_name: str) -> int:
    """Add a new part and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute("INSERT INTO parts (part_name) VALUES (?)", (part_name,))
    db.commit()
    return cursor.lastrowid


def get_part_by_name(part_name: str) -> dict | None:
    """Return the part entry with this part_name (case-insensitive), or None."""
    db = DatabaseConnection()
    return db.fetchone(
        "SELECT id, part_name FROM parts WHERE LOWER(part_name) = LOWER(?)",
        (part_name,),
    )


def update_part(part_id: int, part_name: str):
    """Update an existing part."""
    db = DatabaseConnection()
    db.execute("UPDATE parts SET part_name = ? WHERE id = ?", (part_name, part_id))
    db.commit()


def delete_part(part_id: int):
    """Delete a part."""
    db = DatabaseConnection()
    db.execute("DELETE FROM parts WHERE id = ?", (part_id,))
    db.commit()


def get_parts_count() -> int:
    """Get total number of parts."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM parts")
    return result["count"] if result else 0
