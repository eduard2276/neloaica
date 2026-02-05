"""Billable parts section - Parts used in repair with units and pricing."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QMessageBox,
    QSpinBox,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt, Signal

from src.database.models.parts import get_all_parts, add_part as add_part_to_db
from src.widgets import NoScrollComboBox
from src.styles import theme


class AddPartDialog(QDialog):
    """Dialog for adding a new part to the database."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Part")
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Part Name field
        self.part_name_edit = QLineEdit()
        self.part_name_edit.setPlaceholderText("Enter part name")
        self.part_name_edit.setMinimumHeight(35)
        form_layout.addRow("Part:", self.part_name_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.save_button = QPushButton("Save")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        # Styling
        self.setStyleSheet(theme.dialog() + theme.line_edit_dialog())
        self.save_button.setStyleSheet(theme.button("success"))
        self.cancel_button.setStyleSheet(theme.button("cancel"))

    def get_part_name(self) -> str:
        """Get the part name."""
        return self.part_name_edit.text().strip()

    def accept(self):
        """Validate and accept the dialog."""
        if not self.get_part_name():
            QMessageBox.warning(self, "Validation Error", "Part name is required.")
            self.part_name_edit.setFocus()
            return
        
        super().accept()


class BillablePartsSectionWidget(QWidget):
    """Widget for billable parts section with units and pricing."""
    
    # Signal to notify parent when parts list changes
    # Emits tuple: (parts_list: list, total_parts_cost: float)
    # parts_list format: [{"part_id": int, "part_name": str, "units": int, "price_per_unit": float}, ...]
    parts_changed = Signal(list, float)
    
    def __init__(self, title="Parts Used"):
        super().__init__()
        self.title = title
        self.all_parts = []
        self.selected_parts = []  # List of dicts with part_id, part_name, units, price_per_unit
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the billable parts section UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box for parts
        parts_group = QGroupBox(self.title)
        parts_group.setStyleSheet(theme.groupbox())
        parts_layout = QVBoxLayout(parts_group)
        parts_layout.setSpacing(15)
        
        # Top row: Combo box and Add button
        top_layout = QHBoxLayout()
        
        # Part combo box
        self.part_combo = NoScrollComboBox()
        self.part_combo.setStyleSheet(theme.combobox())
        self.part_combo.currentIndexChanged.connect(self.on_part_changed)
        top_layout.addWidget(self.part_combo, 1)
        
        # Add new part button (➕)
        add_new_part_btn = QPushButton("➕")
        add_new_part_btn.setStyleSheet(theme.button_add())
        add_new_part_btn.setFixedSize(40, 40)
        add_new_part_btn.setToolTip("Add a new part to the database")
        add_new_part_btn.clicked.connect(self.add_new_part_to_database)
        top_layout.addWidget(add_new_part_btn)
        
        parts_layout.addLayout(top_layout)
        
        # Selected parts list
        self.parts_list = QListWidget()
        self.parts_list.setStyleSheet(theme.list_widget())
        self.parts_list.setMinimumHeight(150)
        parts_layout.addWidget(self.parts_list)
        
        # Total parts cost section
        total_layout = QHBoxLayout()
        total_layout.setSpacing(10)
        
        total_label = QLabel("Total Parts Cost:")
        total_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        total_layout.addWidget(total_label)
        
        total_layout.addStretch()
        
        self.total_cost_label = QLabel("$0.00")
        self.total_cost_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #27ae60;")
        total_layout.addWidget(self.total_cost_label)
        
        parts_layout.addLayout(total_layout)
        
        main_layout.addWidget(parts_group)
    
    def load_data(self, restore_state=False):
        """Load parts from database."""
        # Store current selections if restoring
        if restore_state:
            current_parts = self.selected_parts.copy()
        
        # Load parts
        self.all_parts = get_all_parts()
        
        # Block signals during update
        self.part_combo.blockSignals(True)
        self.part_combo.clear()
        self.part_combo.addItem("-- Select Part --", None)
        
        # Add parts that aren't already selected
        selected_ids = [item["part_id"] for item in self.selected_parts]
        for part in self.all_parts:
            if part["id"] not in selected_ids:
                self.part_combo.addItem(part["part_name"], part["id"])
        
        self.part_combo.blockSignals(False)
        
        # Restore selections if requested
        if restore_state and current_parts:
            self.parts_list.clear()
            self.selected_parts = []
            for part_item in current_parts:
                part_id = part_item["part_id"]
                part = next((p for p in self.all_parts if p["id"] == part_id), None)
                if part:
                    self.add_part(
                        part_id, 
                        part["part_name"], 
                        part_item.get("units", 1),
                        part_item.get("price_per_unit", 0.0)
                    )
    
    def on_part_changed(self, index):
        """Handle part combo box selection."""
        part_id = self.part_combo.currentData()
        
        if part_id is None:
            return
        
        # Get part name
        part = next((p for p in self.all_parts if p["id"] == part_id), None)
        if not part:
            return
        
        # Add to list with default values
        self.add_part(part_id, part["part_name"], 1, 0.0)
        
        # Reset combo box
        self.part_combo.blockSignals(True)
        self.part_combo.setCurrentIndex(0)
        self.part_combo.blockSignals(False)
    
    def add_part(self, part_id: int, part_name: str, units: int = 1, price_per_unit: float = 0.0):
        """Add a part to the list."""
        # Create list item
        list_item = QListWidgetItem()
        self.parts_list.addItem(list_item)
        
        # Create widget for the item
        item_widget = QWidget()
        item_widget.setProperty("part_id", part_id)  # Store part_id for later identification
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 5, 5, 5)
        item_layout.setSpacing(10)
        
        # Label with part name
        part_label = QLabel(part_name)
        part_label.setStyleSheet(theme.label_item())
        part_label.setMinimumWidth(150)
        item_layout.addWidget(part_label)
        
        # Units input
        units_label = QLabel("Units:")
        units_label.setStyleSheet("font-size: 12px; color: #2c3e50;")
        item_layout.addWidget(units_label)
        
        units_input = QSpinBox()
        units_input.setRange(1, 9999)
        units_input.setValue(units)
        units_input.setMinimumWidth(80)
        units_input.setStyleSheet(theme.line_edit())
        units_input.valueChanged.connect(lambda val: self.update_part_units(part_id, val))
        item_layout.addWidget(units_input)
        
        # Price per unit input
        price_label = QLabel("Price/Unit:")
        price_label.setStyleSheet("font-size: 12px; color: #2c3e50;")
        item_layout.addWidget(price_label)
        
        price_input = QDoubleSpinBox()
        price_input.setPrefix("$")
        price_input.setDecimals(2)
        price_input.setRange(0.0, 999999.99)
        price_input.setValue(price_per_unit)
        price_input.setMinimumWidth(100)
        price_input.setStyleSheet(theme.line_edit())
        price_input.valueChanged.connect(lambda val: self.update_part_price(part_id, val))
        item_layout.addWidget(price_input)
        
        # Subtotal label
        subtotal_label = QLabel(f"${units * price_per_unit:.2f}")
        subtotal_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #27ae60; min-width: 80px;")
        subtotal_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        item_layout.addWidget(subtotal_label)
        
        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setStyleSheet(theme.button_remove())
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(lambda: self.remove_part(part_id))
        item_layout.addWidget(remove_btn)
        
        # Set the widget to the list item
        list_item.setSizeHint(item_widget.sizeHint())
        self.parts_list.setItemWidget(list_item, item_widget)
        
        # Add to selected parts
        self.selected_parts.append({
            "part_id": part_id,
            "part_name": part_name,
            "units": units,
            "price_per_unit": price_per_unit
        })
        
        # Remove from combo box
        self.part_combo.blockSignals(True)
        for i in range(self.part_combo.count()):
            if self.part_combo.itemData(i) == part_id:
                self.part_combo.removeItem(i)
                break
        self.part_combo.blockSignals(False)
        
        # Emit signal
        self.emit_parts_changed()
    
    def update_part_units(self, part_id: int, units: int):
        """Update the units of a part item."""
        for part_item in self.selected_parts:
            if part_item["part_id"] == part_id:
                part_item["units"] = units
                break
        
        # Update subtotal label in the list
        self.update_subtotal_label(part_id)
        
        # Emit signal
        self.emit_parts_changed()
    
    def update_part_price(self, part_id: int, price: float):
        """Update the price per unit of a part item."""
        for part_item in self.selected_parts:
            if part_item["part_id"] == part_id:
                part_item["price_per_unit"] = price
                break
        
        # Update subtotal label in the list
        self.update_subtotal_label(part_id)
        
        # Emit signal
        self.emit_parts_changed()
    
    def update_subtotal_label(self, part_id: int):
        """Update the subtotal label for a specific part."""
        # Find the part in selected_parts
        part_item = next((p for p in self.selected_parts if p["part_id"] == part_id), None)
        if not part_item:
            return
        
        # Calculate subtotal
        subtotal = part_item["units"] * part_item["price_per_unit"]
        
        # Find the list widget item with matching part_id and update the subtotal label
        for i in range(self.parts_list.count()):
            item = self.parts_list.item(i)
            item_widget = self.parts_list.itemWidget(item)
            if item_widget and item_widget.property("part_id") == part_id:
                # Get the layout and find the subtotal label (5th widget)
                layout = item_widget.layout()
                if layout and layout.count() > 5:
                    subtotal_label = layout.itemAt(5).widget()
                    if isinstance(subtotal_label, QLabel):
                        subtotal_label.setText(f"${subtotal:.2f}")
                        break
    
    def remove_part(self, part_id: int):
        """Remove a part from the list."""
        # Find and remove from selected_parts
        part_item = None
        for item in self.selected_parts:
            if item["part_id"] == part_id:
                part_item = item
                break
        
        if not part_item:
            return
        
        self.selected_parts.remove(part_item)
        
        # Remove from list widget
        for i in range(self.parts_list.count()):
            item = self.parts_list.item(i)
            item_widget = self.parts_list.itemWidget(item)
            if item_widget and item_widget.property("part_id") == part_id:
                self.parts_list.takeItem(i)
                break
        
        # Add back to combo box
        part = next((p for p in self.all_parts if p["id"] == part_id), None)
        if part:
            self.part_combo.blockSignals(True)
            # Insert in alphabetical order
            inserted = False
            for i in range(1, self.part_combo.count()):  # Skip first item (placeholder)
                if self.part_combo.itemText(i) > part["part_name"]:
                    self.part_combo.insertItem(i, part["part_name"], part["id"])
                    inserted = True
                    break
            if not inserted:
                self.part_combo.addItem(part["part_name"], part["id"])
            self.part_combo.blockSignals(False)
        
        # Emit signal
        self.emit_parts_changed()
    
    def add_new_part_to_database(self):
        """Open dialog to add new part to the database."""
        dialog = AddPartDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            part_name = dialog.get_part_name()
            
            # Add to database
            try:
                part_id = add_part_to_db(part_name)
                
                # Reload data to include new part
                self.load_data(restore_state=True)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Part '{part_name}' added successfully!"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to add part: {str(e)}"
                )
    
    def emit_parts_changed(self):
        """Emit the parts_changed signal with current parts list and total cost."""
        self.parts_changed.emit(self.get_selected_parts(), self.get_total_parts_cost())
        self.update_total_cost_label()
    
    def get_selected_parts(self) -> list:
        """Get list of selected parts with units and pricing."""
        return self.selected_parts.copy()
    
    def get_total_parts_cost(self) -> float:
        """Calculate and return the total cost of all parts."""
        return sum(item["units"] * item["price_per_unit"] for item in self.selected_parts)
    
    def update_total_cost_label(self):
        """Update the total cost label."""
        total = self.get_total_parts_cost()
        self.total_cost_label.setText(f"${total:.2f}")
