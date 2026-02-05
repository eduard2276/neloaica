"""Receipts page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import QEvent, Qt

from .receipt_info import ReceiptInfoWidget
from .defects_section import DefectsSectionWidget
from .parts_section import PartsSectionWidget
from .labor_section import LaborSectionWidget
from .billable_parts_section import BillablePartsSectionWidget
from src.services import generate_receipt_excel, template_exists
from src.styles import theme


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
    
    def on_billable_parts_changed(self, parts_list: list, total_cost: float):
        """Handle billable parts list change."""
        # Update receipt_data with billable parts (with units and pricing)
        self.receipt_data['billable_parts'] = parts_list
        self.receipt_data['total_parts_cost'] = total_cost
        self.update_receipt_data()
    
    def update_receipt_data(self):
        """Update and log the complete receipt data object."""
        # For debugging/verification - you can remove this later
        print(f"Receipt data updated: {self.receipt_data}")
    
    def on_generate_clicked(self):
        """Handle generate button click - export receipt to Excel."""
        # Check if template exists
        if not template_exists():
            QMessageBox.warning(
                self,
                "Template Not Found",
                "The Excel template 'Template-Deviz.xlsx' was not found in the templates folder.\n\n"
                "Please add the template file to:\n"
                "templates/Template-Deviz.xlsx"
            )
            return
        
        # Check if client is selected
        if not self.receipt_data.get('client_id'):
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select a client before generating the receipt."
            )
            return
        
        try:
            # Generate the Excel file
            output_path, warnings = generate_receipt_excel(self.receipt_data)
            
            # Prepare success message
            message = f"Receipt has been generated successfully!\n\nFile saved to:\n{output_path}"
            
            # Add warnings if any
            if warnings:
                message += "\n\n" + "\n".join(warnings)
            
            QMessageBox.information(
                self,
                "Receipt Generated",
                message
            )
            
            # Optionally open the file
            import os
            os.startfile(output_path)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate receipt:\n{str(e)}"
            )

