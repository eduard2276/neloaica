"""Excel export functionality for receipts."""

import os
import shutil
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from src.database.models.defects import get_defect_by_id
from src.database.models.parts import get_part_by_id
from src.database.models.labor import get_labor_by_id
from src.database.models.settings import get_tva


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
    
    # A20-A24: Discovered defects (max 5)
    discovered_defect_ids = receipt_data.get('discovered_defects', [])
    
    if len(discovered_defect_ids) > 5:
        warning_messages.append(f"Warning: {len(discovered_defect_ids)} discovered defects found, only the first 5 were added to the receipt.")
    
    # Add up to 5 discovered defects starting at A20
    for i, defect_id in enumerate(discovered_defect_ids[:5]):
        defect = get_defect_by_id(defect_id)
        if defect:
            cell_row = 20 + i  # A20, A21, A22, A23, A24
            sheet[f'A{cell_row}'] = defect['defect_name']
    
    # C14-C17: Parts received from client (max 4)
    part_ids = receipt_data.get('parts', [])
    
    if len(part_ids) > 4:
        warning_messages.append(f"Warning: {len(part_ids)} parts received found, only the first 4 were added to the receipt.")
    
    # Add up to 4 parts starting at C14
    for i, part_id in enumerate(part_ids[:4]):
        part = get_part_by_id(part_id)
        if part:
            cell_row = 14 + i  # C14, C15, C16, C17
            sheet[f'C{cell_row}'] = part['part_name']
    
    # Labor services starting at B36
    labor_ids = receipt_data.get('labor', [])
    total_labor_cost = receipt_data.get('total_labor_cost', 0.0)
    
    # Add labor services starting at row 36
    for i, labor_id in enumerate(labor_ids):
        labor = get_labor_by_id(labor_id)
        if labor:
            current_row = 36 + i
            # If this is not the first labor item, copy the previous row to maintain formatting
            if i > 0:
                # Copy row 36 to create a new row with the same formatting
                sheet.insert_rows(current_row)
                for col in range(1, sheet.max_column + 1):
                    source_cell = sheet.cell(row=36, column=col)
                    target_cell = sheet.cell(row=current_row, column=col)
                    # Copy cell formatting
                    if source_cell.has_style:
                        target_cell.font = source_cell.font.copy()
                        target_cell.border = source_cell.border.copy()
                        target_cell.fill = source_cell.fill.copy()
                        target_cell.number_format = source_cell.number_format
                        target_cell.protection = source_cell.protection.copy()
                        target_cell.alignment = source_cell.alignment.copy()
            # Add labor service name to column B
            sheet[f'B{current_row}'] = labor['service_name']
    
    # Add total labor cost to column E at the next row after all labor items
    if labor_ids:
        total_row = 36 + len(labor_ids)
        sheet[f'E{total_row}'] = total_labor_cost
        # Add TVA for labor at column F (extract TVA from price that includes TVA)
        tva_percentage = get_tva()
        labor_tva = (total_labor_cost * tva_percentage) / (100 + tva_percentage)
        sheet[f'F{total_row}'] = labor_tva
    
    # Parts Used section - starts at row 42, adjusted for labor rows added
    billable_parts = receipt_data.get('billable_parts', [])
    total_parts_cost = receipt_data.get('total_parts_cost', 0.0)
    
    # Calculate the starting row for parts (base 42 + number of labor items)
    parts_start_row = 41 + len(labor_ids)
    
    # Add billable parts starting at the calculated row
    for i, part_data in enumerate(billable_parts):
        current_row = parts_start_row + i
        # If this is not the first part, copy the previous row to maintain formatting
        if i > 0:
            # Copy the parts start row to create a new row with the same formatting
            sheet.insert_rows(current_row)
            for col in range(1, sheet.max_column + 1):
                source_cell = sheet.cell(row=parts_start_row, column=col)
                target_cell = sheet.cell(row=current_row, column=col)
                # Copy cell formatting
                if source_cell.has_style:
                    target_cell.font = source_cell.font.copy()
                    target_cell.border = source_cell.border.copy()
                    target_cell.fill = source_cell.fill.copy()
                    target_cell.number_format = source_cell.number_format
                    target_cell.protection = source_cell.protection.copy()
                    target_cell.alignment = source_cell.alignment.copy()
        
        # Add part data to columns B, C, D, E
        sheet[f'B{current_row}'] = part_data['part_name']  # Part name
        sheet[f'C{current_row}'] = part_data['units']  # Units
        sheet[f'D{current_row}'] = part_data['price_per_unit']  # Price per unit
        # Calculate and add total value (units × price per unit)
        part_total = part_data['units'] * part_data['price_per_unit']
        sheet[f'E{current_row}'] = part_total
        # Calculate and add TVA for this part at column F (extract TVA from price that includes TVA)
        tva_percentage = get_tva()
        part_tva = (part_total * tva_percentage) / (100 + tva_percentage)
        sheet[f'F{current_row}'] = part_tva
    
    # Add total parts cost to column E at the next row after all parts
    if billable_parts:
        total_parts_row = parts_start_row + len(billable_parts)
        sheet[f'E{total_parts_row}'] = total_parts_cost
        # Add total TVA for parts at column F (extract TVA from price that includes TVA)
        tva_percentage = get_tva()
        total_parts_tva = (total_parts_cost * tva_percentage) / (100 + tva_percentage)
        sheet[f'F{total_parts_row}'] = total_parts_tva
    
    # Grand total row (Total Labor + Total Parts) at the next row after total parts
    grand_total = total_labor_cost + total_parts_cost
    if billable_parts:
        grand_total_row = total_parts_row + 1
    elif labor_ids:
        grand_total_row = 36 + len(labor_ids) + 1
    else:
        grand_total_row = 42
    
    tva_percentage = get_tva()
    grand_total_tva = (grand_total * tva_percentage) / (100 + tva_percentage)
    sheet[f'F{grand_total_row}'] = grand_total
    
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
