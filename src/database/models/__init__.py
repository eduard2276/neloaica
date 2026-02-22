"""Database models package."""

# Import all client functions
from .clients import (
    create_clients_table,
    get_all_clients,
    get_client_by_id,
    add_client,
    update_client,
    delete_client,
    get_clients_count,
    get_clients_for_dropdown,
)

# Import all car functions
from .cars import (
    create_cars_table,
    get_all_cars,
    get_car_by_id,
    add_car,
    update_car,
    update_car_kilometers,
    delete_car,
    get_cars_count,
)

# Import all labor functions
from .labor import (
    create_labor_table,
    get_all_labor,
    get_labor_by_id,
    add_labor,
    update_labor,
    delete_labor,
    get_labor_count,
)

# Import all parts functions
from .parts import (
    create_parts_table,
    get_all_parts,
    get_part_by_id,
    add_part,
    update_part,
    delete_part,
    get_parts_count,
)

# Import all defects functions
from .defects import (
    create_defects_table,
    get_all_defects,
    get_defect_by_id,
    add_defect,
    update_defect,
    delete_defect,
    get_defects_count,
)

# Import all settings functions
from .settings import (
    create_settings_table,
    get_tva,
    update_tva,
    get_receipt_number,
    update_receipt_number,
    get_all_settings,
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
]


def init_database():
    """Initialize all database tables."""
    create_clients_table()
    create_cars_table()
    create_labor_table()
    create_parts_table()
    create_defects_table()
    create_settings_table()


