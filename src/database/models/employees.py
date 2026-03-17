"""Employee model and database operations."""

from ..connection import DatabaseConnection


def create_employees_table():
    """Create the employees table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL
        )
    """)
    db.commit()


def get_all_employees() -> list[dict]:
    """Get all employees."""
    db = DatabaseConnection()
    return db.fetchall(
        "SELECT id, first_name, last_name FROM employees ORDER BY last_name, first_name"
    )


def get_employee_by_id(employee_id: int) -> dict | None:
    """Get an employee by ID."""
    db = DatabaseConnection()
    return db.fetchone(
        "SELECT id, first_name, last_name FROM employees WHERE id = ?",
        (employee_id,),
    )


def add_employee(first_name: str, last_name: str) -> int:
    """Add a new employee and return the ID."""
    db = DatabaseConnection()
    cursor = db.execute(
        "INSERT INTO employees (first_name, last_name) VALUES (?, ?)",
        (first_name, last_name),
    )
    db.commit()
    return cursor.lastrowid


def update_employee(employee_id: int, first_name: str, last_name: str):
    """Update an existing employee."""
    db = DatabaseConnection()
    db.execute(
        "UPDATE employees SET first_name = ?, last_name = ? WHERE id = ?",
        (first_name, last_name, employee_id),
    )
    db.commit()


def delete_employee(employee_id: int):
    """Delete an employee."""
    db = DatabaseConnection()
    db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    db.commit()


def get_employees_for_dropdown() -> list[dict]:
    """Get employees for dropdown selection."""
    db = DatabaseConnection()
    return db.fetchall(
        "SELECT id, first_name || ' ' || last_name as name FROM employees ORDER BY last_name, first_name"
    )


def get_employees_count() -> int:
    """Get total number of employees."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM employees")
    return result["count"] if result else 0
