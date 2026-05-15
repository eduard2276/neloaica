"""Settings model and database operations."""

from ..connection import DatabaseConnection


def create_settings_table():
    """Create the settings table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tva REAL NOT NULL DEFAULT 21.0,
            receipt_number INTEGER NOT NULL DEFAULT 1
        )
    """)
    db.commit()

    # Insert default settings if not exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM settings WHERE id = 1")
    if existing and existing["count"] == 0:
        db.execute("INSERT INTO settings (id, tva, receipt_number) VALUES (1, 21.0, 1)")
        db.commit()

    # Migrate existing databases that lack the receipt_number column
    try:
        db.execute("ALTER TABLE settings ADD COLUMN receipt_number INTEGER NOT NULL DEFAULT 1")
        db.commit()
    except Exception:
        # Column already exists — nothing to do
        pass


def get_tva() -> float:
    """Get the TVA value from settings."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT tva FROM settings WHERE id = 1")
    return result["tva"] if result else 21.0


def update_tva(tva_value: float):
    """Update the TVA value in settings."""
    db = DatabaseConnection()
    db.execute("UPDATE settings SET tva = ? WHERE id = 1", (tva_value,))
    db.commit()


def get_receipt_number() -> int:
    """Get the current receipt number from settings."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT receipt_number FROM settings WHERE id = 1")
    return result["receipt_number"] if result else 1


def update_receipt_number(receipt_number: int):
    """Update the receipt number in settings."""
    db = DatabaseConnection()
    db.execute("UPDATE settings SET receipt_number = ? WHERE id = 1", (receipt_number,))
    db.commit()


def get_all_settings() -> dict:
    """Get all settings as a dictionary."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT * FROM settings WHERE id = 1")
    if result:
        return dict(result)
    return {"id": 1, "tva": 21.0, "receipt_number": 1}
