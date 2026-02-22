"""Receipts page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QMessageBox,
    QGroupBox,
)
from PySide6.QtCore import QEvent, Qt

from .receipt_info import ReceiptInfoWidget
from .estimates_section import EstimatesSectionWidget
from .defects_section import DefectsSectionWidget
from .parts_section import PartsSectionWidget
from .labor_section import LaborSectionWidget
from .billable_parts_section import BillablePartsSectionWidget
from src.services import generate_receipt_excel, template_exists, create_backup
from src.database.models.cars import update_car_kilometers
from src.styles import theme
from src.utils import show_warning, show_info, show_critical


class ReceiptsPage(QWidget):
    """Receipts page content."""
    
    def __init__(self):
        super().__init__()
        self.receipt_data = {}  # Store complete receipt form data
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the receipts UI."""
        # Main layout for the page
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Create content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        title = QLabel("🧾 Receipts")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        content_layout.addWidget(title)
        
        # Receipt information section (customer and car data)
        self.receipt_info_widget = ReceiptInfoWidget()
        self.receipt_info_widget.data_changed.connect(self.on_receipt_info_changed)
        content_layout.addWidget(self.receipt_info_widget)

        # Estimates section
        self.estimates_widget = EstimatesSectionWidget("Estimates")
        self.estimates_widget.estimates_changed.connect(self.on_estimates_changed)
        content_layout.addWidget(self.estimates_widget)
        self.on_estimates_changed(
            self.estimates_widget.get_estimate_cost(),
            self.estimates_widget.get_estimated_final_date(),
        )
        
        # Defects section
        self.defects_widget = DefectsSectionWidget("Defects by the Client")
        self.defects_widget.defects_changed.connect(self.on_defects_changed)
        content_layout.addWidget(self.defects_widget)
        
        # Discovered Defects section
        self.discovered_defects_widget = DefectsSectionWidget("Discovered Defects")
        self.discovered_defects_widget.defects_changed.connect(self.on_discovered_defects_changed)
        content_layout.addWidget(self.discovered_defects_widget)
        
        # Parts section
        self.parts_widget = PartsSectionWidget("Parts received from client")
        self.parts_widget.parts_changed.connect(self.on_parts_changed)
        content_layout.addWidget(self.parts_widget)
        
        # Labor section
        self.labor_widget = LaborSectionWidget("Labor Services")
        self.labor_widget.labor_changed.connect(self.on_labor_changed)
        content_layout.addWidget(self.labor_widget)
        
        # Billable parts section (parts used with units and pricing)
        self.billable_parts_widget = BillablePartsSectionWidget("Parts Used")
        self.billable_parts_widget.parts_changed.connect(self.on_billable_parts_changed)
        content_layout.addWidget(self.billable_parts_widget)
        
        # Grand Total section (Labor + Parts)
        grand_total_group = QGroupBox("Grand Total")
        grand_total_group.setStyleSheet(theme.groupbox() + theme.form_label())
        grand_total_layout = QHBoxLayout()
        grand_total_layout.setSpacing(10)
        
        grand_total_label = QLabel("Total (Labor + Parts):")
        grand_total_label.setStyleSheet(theme.form_label())
        grand_total_layout.addWidget(grand_total_label)
        
        self.grand_total_value = QLabel("0.00 Lei")
        self.grand_total_value.setStyleSheet(theme.form_label())
        grand_total_layout.addWidget(self.grand_total_value)
        
        grand_total_layout.addStretch()
        grand_total_group.setLayout(grand_total_layout)
        content_layout.addWidget(grand_total_group)
        
        # Generate button section
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0)
        button_layout.addStretch()
        
        self.generate_button = QPushButton("📄 Generate Receipt")
        self.generate_button.setStyleSheet(theme.button("success"))
        self.generate_button.setMinimumHeight(50)
        self.generate_button.setMinimumWidth(200)
        self.generate_button.clicked.connect(self.on_generate_clicked)
        button_layout.addWidget(self.generate_button)
        
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def showEvent(self, event):
        """Called when the page is shown. Reload data to reflect any changes."""
        super().showEvent(event)
        # Only reload if we've been shown before (not the first time)
        if hasattr(self, '_first_show'):
            self.receipt_info_widget.load_data(restore_state=True)
            self.defects_widget.load_data(restore_state=True)
            self.discovered_defects_widget.load_data(restore_state=True)
            self.parts_widget.load_data(restore_state=True)
            self.labor_widget.load_data(restore_state=True)
            self.billable_parts_widget.load_data(restore_state=True)
        else:
            self._first_show = True
    
    def on_receipt_info_changed(self, data: dict):
        """Handle receipt information data change."""
        # Update receipt_data with receipt info
        self.receipt_data.update(data)
        self.update_receipt_data()
    
    def on_defects_changed(self, defect_ids: list):
        """Handle defects list change."""
        # Update receipt_data with defects
        self.receipt_data['defects'] = defect_ids
        self.update_receipt_data()

    def on_estimates_changed(self, estimate_cost: float, estimated_final_date: str):
        """Handle estimates section data change."""
        self.receipt_data['estimate_cost'] = estimate_cost
        self.receipt_data['estimated_final_date'] = estimated_final_date
        self.update_receipt_data()
    
    def on_discovered_defects_changed(self, defect_ids: list):
        """Handle discovered defects list change."""
        # Update receipt_data with discovered defects
        self.receipt_data['discovered_defects'] = defect_ids
        self.update_receipt_data()
    
    def on_parts_changed(self, part_ids: list):
        """Handle parts list change."""
        # Update receipt_data with parts
        self.receipt_data['parts'] = part_ids
        self.update_receipt_data()
    
    def on_labor_changed(self, labor_ids: list, total_cost: float):
        """Handle labor list change."""
        # Update receipt_data with labor IDs and total cost
        self.receipt_data['labor'] = labor_ids
        self.receipt_data['total_labor_cost'] = total_cost
        self.update_receipt_data()
        self.update_grand_total()
    
    def on_billable_parts_changed(self, parts_list: list, total_cost: float):
        """Handle billable parts list change."""
        # Update receipt_data with billable parts (with units and pricing)
        self.receipt_data['billable_parts'] = parts_list
        self.receipt_data['total_parts_cost'] = total_cost
        self.update_receipt_data()
        self.update_grand_total()
    
    def update_grand_total(self):
        """Update the grand total label (Labor + Parts)."""
        labor_cost = self.receipt_data.get('total_labor_cost', 0.0)
        parts_cost = self.receipt_data.get('total_parts_cost', 0.0)
        grand_total = labor_cost + parts_cost
        self.grand_total_value.setText(f"{self.format_price(grand_total)} Lei")
    
    def format_price(self, value) -> str:
        """Format a number with thousand separators."""
        try:
            num = float(value)
        except (ValueError, TypeError):
            return "0.00"
        integer_part = int(num)
        decimal_part = f"{num:.2f}".split('.')[1]
        formatted = ''
        int_str = str(integer_part)
        for i, d in enumerate(reversed(int_str)):
            if i > 0 and i % 3 == 0:
                formatted = ' ' + formatted
            formatted = d + formatted
        return f"{formatted}.{decimal_part}"
    
    def update_receipt_data(self):
        """Update and log the complete receipt data object."""
        # For debugging/verification - you can remove this later
        print(f"Receipt data updated: {self.receipt_data}")
    
    def on_generate_clicked(self):
        """Handle generate button click - export receipt to Excel."""
        # Check if template exists
        if not template_exists():
            show_warning(
                self,
                "Template Not Found",
                "The Excel template 'Template-Deviz.xlsx' was not found in the templates folder.\n\n"
                "Please add the template file to:\n"
                "templates/Template-Deviz.xlsx"
            )
            return
        
        # Check if client is selected
        if not self.receipt_data.get('client_id'):
            show_warning(
                self,
                "Missing Information",
                "Please select a client before generating the receipt."
            )
            return
        
        try:
            # Create backup before generating receipt (critical operation)
            print("[INFO] Creating pre-receipt backup...")
            create_backup("pre-receipt")
            
            # Update car kilometers in database if changed
            car_id = self.receipt_data.get('car_id')
            kilometers = self.receipt_data.get('kilometers', '')
            if car_id and kilometers:
                try:
                    km_value = int(kilometers)
                    update_car_kilometers(car_id, km_value)
                except ValueError:
                    pass  # Ignore if kilometers is not a valid number
            
            # Generate the Excel file
            output_path, warnings = generate_receipt_excel(self.receipt_data)
            
            # Prepare success message
            message = f"Receipt has been generated successfully!\n\nFile saved to:\n{output_path}"
            
            # Add warnings if any
            if warnings:
                message += "\n\n" + "\n".join(warnings)
            
            show_info(self, "Receipt Generated", message)
            
            # Optionally open the file
            import os
            os.startfile(output_path)
            
        except Exception as e:
            show_critical(self, "Error", f"Failed to generate receipt:\n{str(e)}")

