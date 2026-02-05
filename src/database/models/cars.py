"""Car model and database operations."""

from ..connection import DatabaseConnection


def create_cars_table():
    """Create the cars table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            plate_number TEXT NOT NULL,
            vin TEXT NOT NULL UNIQUE,
            model TEXT NOT NULL,
            kilometers INTEGER DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    """)
    db.commit()


def populate_cars_mock_data():
    """Populate cars with mock data."""
    db = DatabaseConnection()
    
    # Check if data already exists
    existing = db.fetchone("SELECT COUNT(*) as count FROM cars")
    if existing and existing["count"] > 0:
        return  # Data already exists
    
    # Insert mock cars
    cars = [
        (1, "ABC-1234", "WVWZZZ3CZWE123456", "Audi A4", 45000),
        (1, "XYZ-5678", "WBAPH5C55BA123456", "BMW 320i", 32000),
        (2, "DEF-9012", "WAUZZZ8V5KA123456", "Audi Q5", 28000),
        (3, "GHI-3456", "WDB2030411A123456", "Mercedes C200", 55000),
        (4, "JKL-7890", "WVWZZZ1JZYW123456", "Volkswagen Golf", 67000),
        (5, "MNO-1122", "TMBJG7NE1J0123456", "Skoda Octavia", 42000),
        (6, "PQR-3344", "WBAPH5G51BA123456", "BMW 520d", 38000),
        (7, "STU-5566", "WAUZZZ4G6EN123456", "Audi A6", 51000),
        (8, "VWX-7788", "WDD2050091R123456", "Mercedes E220", 29000),
        (9, "YZA-9900", "3VW447AU5JM123456", "Volkswagen Passat", 73000),
        (10, "BCD-2233", "TMBAH7NE8J0123456", "Skoda Superb", 44000),
    ]
    
    db.executemany(
        "INSERT INTO cars (client_id, plate_number, vin, model, kilometers) VALUES (?, ?, ?, ?, ?)",
        cars
    )
    db.commit()


def get_all_cars() -> list[dict]:
    """Get all cars with client info."""
    db = DatabaseConnection()
    return db.fetchall("""
        SELECT c.id, c.client_id, c.plate_number, c.vin, c.model, c.kilometers,
               cl.first_name || ' ' || cl.last_name as client_name
        FROM cars c
        LEFT JOIN clients cl ON c.client_id = cl.id
        ORDER BY c.model, c.plate_number
    """)


def get_car_by_id(car_id: int) -> dict | None:
    """Get a car by ID."""
    db = DatabaseConnection()
    return db.fetchone("""
        SELECT c.id, c.client_id, c.plate_number, c.vin, c.model, c.kilometers,
               cl.first_name || ' ' || cl.last_name as client_name
        FROM cars c
        LEFT JOIN clients cl ON c.client_id = cl.id
        WHERE c.id = ?
    """, (car_id,))


def add_car(client_id: int, plate_number: str, vin: str, model: str, kilometers: int = 0) -> int:
    """Add a new car and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute(
        "INSERT INTO cars (client_id, plate_number, vin, model, kilometers) VALUES (?, ?, ?, ?, ?)",
        (client_id, plate_number, vin, model, kilometers)
    )
    db.commit()
    return cursor.lastrowid


def update_car(car_id: int, client_id: int, plate_number: str, vin: str, model: str, kilometers: int = 0):
    """Update an existing car."""
    db = DatabaseConnection()
    db.execute(
        "UPDATE cars SET client_id = ?, plate_number = ?, vin = ?, model = ?, kilometers = ? WHERE id = ?",
        (client_id, plate_number, vin, model, kilometers, car_id)
    )
    db.commit()


def delete_car(car_id: int):
    """Delete a car."""
    db = DatabaseConnection()
    db.execute("DELETE FROM cars WHERE id = ?", (car_id,))
    db.commit()


def get_cars_count() -> int:
    """Get total number of cars."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM cars")
    return result["count"] if result else 0
