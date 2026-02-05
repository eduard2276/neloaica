"""Excel export functionality for receipts."""

import os
import shutil
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from src.database.models.defects import get_defect_by_id


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
EXPORTS_DIR = PROJECT_ROOT / "exports" / "receipts"

# Template file name
TEMPLATE_FILE = "Template-deviz.xlsx"


def ensure_exports_dir():
    """Ensure the exports directory exists."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_receipt_excel(receipt_data: dict) -> str:
    """
    Generate a receipt Excel file from the template.
    
    Args:
        receipt_data: Dictionary containing all receipt information
        
    Returns:
        Path to the generated Excel file
        
    Raises:
        FileNotFoundError: If template file is not found
        Exception: If there's an error generating the file
    """
    # Ensure exports directory exists
    ensure_exports_dir()
    
    # Check if template exists
    template_path = TEMPLATES_DIR / TEMPLATE_FILE
    
    # Debug logging
    print(f"[DEBUG] PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"[DEBUG] TEMPLATES_DIR: {TEMPLATES_DIR}")
    print(f"[DEBUG] TEMPLATE_FILE: {TEMPLATE_FILE}")
    print(f"[DEBUG] Full template_path: {template_path}")
    print(f"[DEBUG] template_path.exists(): {template_path.exists()}")
    print(f"[DEBUG] template_path.is_file(): {template_path.is_file() if template_path.exists() else 'N/A'}")
    
    # List files in templates directory
    if TEMPLATES_DIR.exists():
        print(f"[DEBUG] Files in TEMPLATES_DIR:")
        for file in TEMPLATES_DIR.iterdir():
            print(f"  - {file.name}")
    else:
        print(f"[DEBUG] TEMPLATES_DIR does not exist!")
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client_name = receipt_data.get('client_name', 'Unknown').replace(' ', '_')
    output_filename = f"Deviz_{client_name}_{timestamp}.xlsx"
    output_path = EXPORTS_DIR / output_filename
    
    # Copy template to output location
    shutil.copy2(template_path, output_path)
    
    # Open the copied file and fill in the data
    workbook = load_workbook(output_path)
    sheet = workbook.active  # Get Sheet 1
    
    # Fill in client data
    # B10: Client name
    sheet['B10'] = receipt_data.get('client_name', '')
    
    # D10: Car model
    sheet['D10'] = receipt_data.get('model', '')
    
    # F10: Car kilometers
    kilometers = receipt_data.get('kilometers', '')
    if kilometers:
        try:
            sheet['F10'] = int(kilometers)
        except ValueError:
            sheet['F10'] = kilometers
    
    # E11: Plate number
    sheet['E11'] = receipt_data.get('plate_number', '')
    
    # E12: VIN
    sheet['E12'] = receipt_data.get('vin', '')
    
    # B12: Client address
    sheet['B12'] = receipt_data.get('client_address', '')
    
    # A14-A18: Defects by the client (max 5)
    defect_ids = receipt_data.get('defects', [])
    warning_messages = []
    
    if len(defect_ids) > 5:
        warning_messages.append(f"Warning: {len(defect_ids)} defects found, only the first 5 were added to the receipt.")
    
    # Add up to 5 defects starting at A14
    for i, defect_id in enumerate(defect_ids[:5]):
        defect = get_defect_by_id(defect_id)
        if defect:
            cell_row = 14 + i  # A14, A15, A16, A17, A18
            sheet[f'A{cell_row}'] = defect['defect_name']
    
    # Save the workbook
    workbook.save(output_path)
    workbook.close()
    
    return str(output_path), warning_messages


def get_template_path() -> Path:
    """Get the path to the template file."""
    return TEMPLATES_DIR / TEMPLATE_FILE


def template_exists() -> bool:
    """Check if the template file exists."""
    template_path = get_template_path()
    
    # Debug logging
    print(f"[DEBUG template_exists()] PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"[DEBUG template_exists()] TEMPLATES_DIR: {TEMPLATES_DIR}")
    print(f"[DEBUG template_exists()] TEMPLATE_FILE: {TEMPLATE_FILE}")
    print(f"[DEBUG template_exists()] template_path: {template_path}")
    print(f"[DEBUG template_exists()] TEMPLATES_DIR.exists(): {TEMPLATES_DIR.exists()}")
    
    if TEMPLATES_DIR.exists():
        print(f"[DEBUG template_exists()] Files in templates directory:")
        try:
            for file in TEMPLATES_DIR.iterdir():
                print(f"  - {file.name}")
        except Exception as e:
            print(f"  Error listing files: {e}")
    
    exists = template_path.exists()
    print(f"[DEBUG template_exists()] template_path.exists(): {exists}")
    
    return exists
