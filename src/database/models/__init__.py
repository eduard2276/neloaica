"""Database models package."""

# Import all client functions
# Import all car functions
from .cars import (
    add_car,
    create_cars_table,
    delete_car,
    get_all_cars,
    get_car_by_id,
    get_cars_count,
    update_car,
    update_car_kilometers,
)
from .clients import (
    add_client,
    create_clients_table,
    delete_client,
    get_all_clients,
    get_client_by_id,
    get_clients_count,
    get_clients_for_dropdown,
    update_client,
)

# Import all defects functions
from .defects import (
    add_defect,
    create_defects_table,
    delete_defect,
    get_all_defects,
    get_defect_by_id,
    get_defect_by_name,
    get_defects_count,
    update_defect,
)

# Import all employee functions
from .employees import (
    add_employee,
    create_employees_table,
    delete_employee,
    get_all_employees,
    get_employee_by_id,
    get_employee_by_name,
    get_employees_count,
    get_employees_for_dropdown,
    update_employee,
)

# Import all labor functions
from .labor import (
    add_labor,
    create_labor_table,
    delete_labor,
    get_all_labor,
    get_labor_by_id,
    get_labor_by_name,
    get_labor_count,
    update_labor,
)

# Import all parts functions
from .parts import (
    add_part,
    create_parts_table,
    delete_part,
    get_all_parts,
    get_part_by_id,
    get_part_by_name,
    get_parts_count,
    update_part,
)

# Import all receipt functions
from .receipts import (
    add_receipt,
    create_receipts_table,
    delete_receipt,
    get_all_receipts,
    get_receipt_by_id,
    get_receipt_by_plate_and_date,
    get_receipts_count,
    update_receipt,
    update_receipt_status,
)

# Import all settings functions
from .settings import (
    create_settings_table,
    get_all_settings,
    get_receipt_number,
    get_tva,
    update_receipt_number,
    update_tva,
)

__all__ = [
    # Initialization
    "init_database",
    # Client functions
    "get_all_clients",
    "get_client_by_id",
    "add_client",
    "update_client",
    "delete_client",
    "get_clients_count",
    "get_clients_for_dropdown",
    # Car functions
    "get_all_cars",
    "get_car_by_id",
    "add_car",
    "update_car",
    "update_car_kilometers",
    "delete_car",
    "get_cars_count",
    # Labor functions
    "get_all_labor",
    "get_labor_by_id",
    "add_labor",
    "update_labor",
    "delete_labor",
    "get_labor_count",
    # Parts functions
    "get_all_parts",
    "get_part_by_id",
    "add_part",
    "update_part",
    "delete_part",
    "get_parts_count",
    # Defects functions
    "get_all_defects",
    "get_defect_by_id",
    "add_defect",
    "update_defect",
    "delete_defect",
    "get_defects_count",
    # Settings functions
    "get_tva",
    "update_tva",
    "get_receipt_number",
    "update_receipt_number",
    "get_all_settings",
    # Employee functions
    "get_all_employees",
    "get_employee_by_id",
    "add_employee",
    "update_employee",
    "delete_employee",
    "get_employees_count",
    "get_employees_for_dropdown",
    # Receipt functions
    "get_all_receipts",
    "get_receipt_by_id",
    "add_receipt",
    "update_receipt",
    "update_receipt_status",
    "delete_receipt",
    "get_receipts_count",
]


def init_database():
    """Initialize all database tables."""
    create_clients_table()
    create_cars_table()
    create_labor_table()
    create_parts_table()
    create_defects_table()
    create_settings_table()
    create_receipts_table()
    create_employees_table()
