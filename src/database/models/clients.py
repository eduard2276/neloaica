"""Client model and database operations."""

from ..connection import DatabaseConnection


def create_clients_table():
    """Create the clients table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            address TEXT
        )
    """)
    db.commit()


def populate_clients_mock_data():
    """Populate clients with mock data."""
    db = DatabaseConnection()
    
    # Check if data already exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM clients")
    if existing and existing["count"] > 0:
        return  # Data already exists
    
    # Insert mock clients
    clients = [
        ("John", "Smith", "123 Main St, New York, NY 10001"),
        ("Emma", "Johnson", "456 Oak Ave, Los Angeles, CA 90012"),
        ("Michael", "Williams", "789 Pine Rd, Chicago, IL 60601"),
        ("Sarah", "Brown", "321 Elm St, Houston, TX 77001"),
        ("David", "Jones", "654 Maple Dr, Phoenix, AZ 85001"),
        ("Lisa", "Garcia", "987 Cedar Ln, Philadelphia, PA 19101"),
        ("James", "Miller", "147 Birch Ct, San Antonio, TX 78201"),
        ("Jennifer", "Davis", "258 Walnut St, San Diego, CA 92101"),
        ("Robert", "Martinez", "369 Spruce Ave, Dallas, TX 75201"),
        ("Maria", "Anderson", "741 Ash Blvd, San Jose, CA 95101"),
    ]
    
    db.executemany(
        "INSERT INTO clients (first_name, last_name, address) VALUES (?, ?, ?)",
        clients
    )
    db.commit()


def get_all_clients() -> list[dict]:
    """Get all clients."""
    db = DatabaseConnection()
    return db.fetchall("SELECT id, first_name, last_name, address FROM clients ORDER BY last_name, first_name")


def get_client_by_id(client_id: int) -> dict | None:
    """Get a client by ID."""
    db = DatabaseConnection()
    return db.fetchone("SELECT id, first_name, last_name, address FROM clients WHERE id = ?", (client_id,))


def add_client(first_name: str, last_name: str, address: str = "") -> int:
    """Add a new client and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute(
        "INSERT INTO clients (first_name, last_name, address) VALUES (?, ?, ?)",
        (first_name, last_name, address)
    )
    db.commit()
    return cursor.lastrowid


def update_client(client_id: int, first_name: str, last_name: str, address: str = ""):
    """Update an existing client."""
    db = DatabaseConnection()
    db.execute(
        "UPDATE clients SET first_name = ?, last_name = ?, address = ? WHERE id = ?",
        (first_name, last_name, address, client_id)
    )
    db.commit()


def delete_client(client_id: int):
    """Delete a client."""
    db = DatabaseConnection()
    db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    db.commit()


def get_clients_count() -> int:
    """Get total number of clients."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM clients")
    return result["count"] if result else 0


def get_clients_for_dropdown() -> list[dict]:
    """Get clients for dropdown selection."""
    db = DatabaseConnection()
    return db.fetchall("SELECT id, first_name || ' ' || last_name as name FROM clients ORDER BY last_name, first_name")
