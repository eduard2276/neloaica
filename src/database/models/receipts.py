"""Receipt model and database operations."""

import json
from datetime import datetime

from ..connection import DatabaseConnection


def create_receipts_table():
    """Create the receipts table."""
    db = DatabaseConnection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            car_id INTEGER,
            client_name TEXT NOT NULL DEFAULT '',
            car_model TEXT NOT NULL DEFAULT '',
            plate_number TEXT NOT NULL DEFAULT '',
            vin TEXT NOT NULL DEFAULT '',
            kilometers TEXT NOT NULL DEFAULT '',
            executant_name TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL DEFAULT '',
            estimate_cost REAL NOT NULL DEFAULT 0.0,
            estimated_final_date TEXT NOT NULL DEFAULT '',
            defects TEXT NOT NULL DEFAULT '[]',
            discovered_defects TEXT NOT NULL DEFAULT '[]',
            parts TEXT NOT NULL DEFAULT '[]',
            labor TEXT NOT NULL DEFAULT '[]',
            total_labor_cost REAL NOT NULL DEFAULT 0.0,
            billable_parts TEXT NOT NULL DEFAULT '[]',
            total_parts_cost REAL NOT NULL DEFAULT 0.0,
            grand_total REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'Ongoing',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
            FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE SET NULL
        )
    """)
    db.commit()

    # Migration: add executant_name column if missing (existing databases)
    try:
        db.execute("ALTER TABLE receipts ADD COLUMN executant_name TEXT NOT NULL DEFAULT ''")
        db.commit()
    except Exception:
        pass


def get_all_receipts() -> list[dict]:
    """Get all receipts, ordered by most recent first."""
    db = DatabaseConnection()
    rows = db.fetchall("SELECT * FROM receipts ORDER BY updated_at DESC, id DESC")
    for row in rows:
        row["defects"] = json.loads(row.get("defects", "[]"))
        row["discovered_defects"] = json.loads(row.get("discovered_defects", "[]"))
        row["parts"] = json.loads(row.get("parts", "[]"))
        row["labor"] = json.loads(row.get("labor", "[]"))
        row["billable_parts"] = json.loads(row.get("billable_parts", "[]"))
    return rows


def get_receipt_by_id(receipt_id: int) -> dict | None:
    """Get a single receipt by ID."""
    db = DatabaseConnection()
    row = db.fetchone("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
    if row:
        row["defects"] = json.loads(row.get("defects", "[]"))
        row["discovered_defects"] = json.loads(row.get("discovered_defects", "[]"))
        row["parts"] = json.loads(row.get("parts", "[]"))
        row["labor"] = json.loads(row.get("labor", "[]"))
        row["billable_parts"] = json.loads(row.get("billable_parts", "[]"))
    return row


def add_receipt(data: dict) -> int:
    """Add a new receipt and return its ID."""
    db = DatabaseConnection()
    cursor = db.execute(
        """INSERT INTO receipts (
            client_id, car_id, client_name, car_model,
            plate_number, vin, kilometers, executant_name, date,
            estimate_cost, estimated_final_date,
            defects, discovered_defects, parts,
            labor, total_labor_cost,
            billable_parts, total_parts_cost,
            grand_total, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("client_id"),
            data.get("car_id"),
            data.get("client_name", ""),
            data.get("model", ""),
            data.get("plate_number", ""),
            data.get("vin", ""),
            data.get("kilometers", ""),
            data.get("executant_name", ""),
            data.get("date", ""),
            data.get("estimate_cost", 0.0),
            data.get("estimated_final_date", ""),
            json.dumps(data.get("defects", [])),
            json.dumps(data.get("discovered_defects", [])),
            json.dumps(data.get("parts", [])),
            json.dumps(data.get("labor", [])),
            data.get("total_labor_cost", 0.0),
            json.dumps(data.get("billable_parts", [])),
            data.get("total_parts_cost", 0.0),
            data.get("grand_total", 0.0),
            data.get("status", "Ongoing"),
        ),
    )
    db.commit()
    return cursor.lastrowid


def update_receipt(receipt_id: int, data: dict):
    """Update an existing receipt."""
    db = DatabaseConnection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        """UPDATE receipts SET
            client_id = ?, car_id = ?, client_name = ?, car_model = ?,
            plate_number = ?, vin = ?, kilometers = ?, executant_name = ?, date = ?,
            estimate_cost = ?, estimated_final_date = ?,
            defects = ?, discovered_defects = ?, parts = ?,
            labor = ?, total_labor_cost = ?,
            billable_parts = ?, total_parts_cost = ?,
            grand_total = ?, status = ?, updated_at = ?
        WHERE id = ?""",
        (
            data.get("client_id"),
            data.get("car_id"),
            data.get("client_name", ""),
            data.get("model", ""),
            data.get("plate_number", ""),
            data.get("vin", ""),
            data.get("kilometers", ""),
            data.get("executant_name", ""),
            data.get("date", ""),
            data.get("estimate_cost", 0.0),
            data.get("estimated_final_date", ""),
            json.dumps(data.get("defects", [])),
            json.dumps(data.get("discovered_defects", [])),
            json.dumps(data.get("parts", [])),
            json.dumps(data.get("labor", [])),
            data.get("total_labor_cost", 0.0),
            json.dumps(data.get("billable_parts", [])),
            data.get("total_parts_cost", 0.0),
            data.get("grand_total", 0.0),
            data.get("status", "Ongoing"),
            now,
            receipt_id,
        ),
    )
    db.commit()


def update_receipt_status(receipt_id: int, status: str):
    """Update only the status of a receipt."""
    db = DatabaseConnection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE receipts SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, receipt_id),
    )
    db.commit()


def delete_receipt(receipt_id: int):
    """Delete a receipt."""
    db = DatabaseConnection()
    db.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
    db.commit()


def get_receipts_count() -> int:
    """Get total number of receipts."""
    db = DatabaseConnection()
    result = db.fetchone("SELECT COUNT(*) as count FROM receipts")
    return result["count"] if result else 0


def get_receipt_by_plate_and_date(
    plate_number: str, date: str, exclude_id: int | None = None
) -> dict | None:
    """Return a receipt matching plate_number + date, or None.

    The match is case-insensitive on plate_number.  Pass *exclude_id* when
    checking for duplicates during an update so the record being edited is
    not considered a conflict with itself.

    Returns None (no conflict) when either plate_number or date is empty.
    """
    if not plate_number or not date:
        return None
    db = DatabaseConnection()
    if exclude_id is not None:
        row = db.fetchone(
            "SELECT id, client_name, plate_number, date FROM receipts "
            "WHERE LOWER(plate_number) = LOWER(?) AND date = ? AND id != ?",
            (plate_number, date, exclude_id),
        )
    else:
        row = db.fetchone(
            "SELECT id, client_name, plate_number, date FROM receipts "
            "WHERE LOWER(plate_number) = LOWER(?) AND date = ?",
            (plate_number, date),
        )
    return row
