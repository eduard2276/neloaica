"""Labor section - Labor services for the receipt."""

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
)
from PySide6.QtCore import Qt, Signal, QSize

from src.database.models.labor import get_all_labor, add_labor as add_labor_to_db, get_labor_by_name
from src.widgets import NoScrollComboBox
from src.styles import theme
from src.utils import show_warning, show_info, show_critical


class AddLaborDialog(QDialog):
    """Dialog for adding a new labor service."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Labor Service")
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
        
        # Service Name field
        self.service_name_edit = QLineEdit()
        self.service_name_edit.setPlaceholderText("Enter service name")
        self.service_name_edit.setMinimumHeight(35)
        form_layout.addRow("Service:", self.service_name_edit)
        
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

    def get_service_name(self) -> str:
        """Get the service name."""
        return self.service_name_edit.text().strip()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def accept(self):
        """Validate and accept the dialog."""
        if not self.get_service_name():
            show_warning(self, "Validation Error", "Service name is required.")
            self.service_name_edit.setFocus()
            return
        
        super().accept()


class LaborSectionWidget(QWidget):
    """Widget for labor services section."""
    
    # Signal to notify parent when labor list or total cost changes
    # Emits tuple: (labor_ids: list, total_cost: float)
    labor_changed = Signal(list, float)
    
    def __init__(self, title="Labor Services"):
        super().__init__()
        self.title = title
        self.all_labor = []
        self.selected_labor = []  # List of labor IDs
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the labor section UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box for labor
        labor_group = QGroupBox(self.title)
        labor_group.setStyleSheet(theme.groupbox())
        labor_layout = QVBoxLayout(labor_group)
        labor_layout.setSpacing(15)
        
        # Top row: Combo box and Add button
        top_layout = QHBoxLayout()
        
        # Labor combo box
        self.labor_combo = NoScrollComboBox()
        self.labor_combo.setStyleSheet(theme.combobox())
        self.labor_combo.currentIndexChanged.connect(self.on_labor_changed)
        top_layout.addWidget(self.labor_combo, 1)
        
        # Add new labor button (➕)
        add_new_labor_btn = QPushButton("➕")
        add_new_labor_btn.setStyleSheet(theme.button_add())
        add_new_labor_btn.setFixedSize(40, 40)
        add_new_labor_btn.setToolTip("Add a new labor service to the database")
        add_new_labor_btn.clicked.connect(self.add_new_labor_to_database)
        top_layout.addWidget(add_new_labor_btn)
        
        labor_layout.addLayout(top_layout)
        
        # Selected labor list
        self.labor_list = QListWidget()
        self.labor_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.labor_list.setStyleSheet(theme.list_widget())
        self.update_list_style()
        labor_layout.addWidget(self.labor_list)
        
        # Total labor cost section
        total_layout = QHBoxLayout()
        total_layout.setSpacing(10)
        
        total_label = QLabel("Total Labor Cost:")
        total_label.setStyleSheet(theme.form_label())
        total_layout.addWidget(total_label)
        
        self.total_cost_input = QLineEdit()
        self.total_cost_input.setPlaceholderText("e.g. 1 500.00 Lei")
        self.total_cost_input.setStyleSheet(theme.line_edit())
        self.total_cost_input.setMaximumWidth(200)
        self._cost_updating = False
        self.total_cost_input.textChanged.connect(self.on_cost_text_changed)
        total_layout.addWidget(self.total_cost_input)
        
        total_layout.addStretch()
        
        labor_layout.addLayout(total_layout)
        
        main_layout.addWidget(labor_group)
    
    def load_data(self, restore_state=False):
        """Load labor from database."""
        # Store current selections if restoring
        if restore_state:
            current_labor = self.selected_labor.copy()
            current_total = self.total_cost_input.text()
        else:
            self.selected_labor = []
            self.labor_list.clear()
            self.total_cost_input.clear()
        
        # Load labor
        self.all_labor = get_all_labor()
        
        # Block signals during update
        self.labor_combo.blockSignals(True)
        self.labor_combo.clear()
        self.labor_combo.addItem("-- Select Labor Service --", None)
        
        # Add labor that aren't already selected
        for labor in self.all_labor:
            if labor["id"] not in self.selected_labor:
                self.labor_combo.addItem(labor["service_name"], labor["id"])
        
        self.labor_combo.blockSignals(False)
        
        if restore_state and current_labor:
            self.labor_list.clear()
            self.selected_labor = []
            for labor_id in current_labor:
                labor = next((l for l in self.all_labor if l["id"] == labor_id), None)
                if labor:
                    self.add_labor(labor_id, labor["service_name"])
            self.total_cost_input.setText(current_total)
        elif not restore_state:
            self.update_list_style()
            self.emit_labor_changed()
    
    def on_labor_changed(self, index):
        """Handle labor combo box selection."""
        labor_id = self.labor_combo.currentData()
        
        if labor_id is None:
            return
        
        # Get labor name
        labor = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if not labor:
            return
        
        # Add to list
        self.add_labor(labor_id, labor["service_name"])
        
        # Reset combo box
        self.labor_combo.blockSignals(True)
        self.labor_combo.setCurrentIndex(0)
        self.labor_combo.blockSignals(False)
    
    def add_labor(self, labor_id: int, service_name: str):
        """Add a labor to the list."""
        # Create list item
        list_item = QListWidgetItem()
        self.labor_list.addItem(list_item)
        
        # Create widget for the item
        item_widget = QWidget()
        item_widget.setObjectName("laborItem")
        item_widget.setStyleSheet("#laborItem, #laborItem * { background-color: white; } #laborItem { border-bottom: 1px solid #bdc3c7; }")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(10, 8, 10, 8)
        item_layout.setSpacing(10)
        
        # Label with labor name
        labor_label = QLabel(service_name)
        labor_label.setStyleSheet(theme.label_item())
        item_layout.addWidget(labor_label, 1)
        
        # Remove button
        remove_btn = QPushButton("🗑️")
        remove_btn.setStyleSheet(theme.button_icon("delete"))
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(lambda checked, l_id=labor_id: self.remove_labor(l_id))
        item_layout.addWidget(remove_btn)
        
        # Set the widget to the list item
        list_item.setSizeHint(QSize(0, 46))
        self.labor_list.setItemWidget(list_item, item_widget)
        
        # Add to selected labor
        self.selected_labor.append(labor_id)
        
        # Remove from combo box
        self.labor_combo.blockSignals(True)
        for i in range(self.labor_combo.count()):
            if self.labor_combo.itemData(i) == labor_id:
                self.labor_combo.removeItem(i)
                break
        self.labor_combo.blockSignals(False)
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.emit_labor_changed()
    
    def remove_labor(self, labor_id: int):
        """Remove a labor from the list."""
        # Find and remove from selected_labor
        if labor_id not in self.selected_labor:
            return
        
        self.selected_labor.remove(labor_id)
        
        # Remove from list widget
        for i in range(self.labor_list.count()):
            item = self.labor_list.item(i)
            item_widget = self.labor_list.itemWidget(item)
            if item_widget:
                # Check if this is the right item by looking for the labor in selected list
                self.labor_list.takeItem(i)
                break
        
        # Add back to combo box
        labor = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if labor:
            self.labor_combo.blockSignals(True)
            # Insert in alphabetical order
            inserted = False
            for i in range(1, self.labor_combo.count()):  # Skip first item (placeholder)
                if self.labor_combo.itemText(i) > labor["service_name"]:
                    self.labor_combo.insertItem(i, labor["service_name"], labor["id"])
                    inserted = True
                    break
            if not inserted:
                self.labor_combo.addItem(labor["service_name"], labor["id"])
            self.labor_combo.blockSignals(False)
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.emit_labor_changed()
    
    def update_list_style(self):
        """Update list widget background and height based on item count."""
        if len(self.selected_labor) > 0:
            self.labor_list.setStyleSheet(theme.list_widget_with_items())
        else:
            self.labor_list.setStyleSheet(theme.list_widget())
        self._resize_list()

    def _resize_list(self):
        """Resize list widget height to fit all items without scrollbar."""
        count = self.labor_list.count()
        if count == 0:
            self.labor_list.setFixedHeight(0)
            return
        total = sum(
            self.labor_list.sizeHintForRow(i) for i in range(count)
        )
        margins = self.labor_list.contentsMargins()
        total += margins.top() + margins.bottom() + 4
        self.labor_list.setFixedHeight(total)
    
    def add_new_labor_to_database(self):
        """Open dialog to add new labor to the database."""
        dialog = AddLaborDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            service_name = dialog.get_service_name()

            existing = get_labor_by_name(service_name)
            if existing:
                show_warning(
                    self, "Duplicate Entry",
                    f"A service named '{existing['service_name']}' already exists."
                )
                return

            # Add to database
            try:
                labor_id = add_labor_to_db(service_name)
                
                # Reload data to include new labor
                self.load_data(restore_state=True)
                
                show_info(self, "Success", f"Labor service '{service_name}' added successfully!")
            except Exception as e:
                show_critical(self, "Error", f"Failed to add labor service: {str(e)}")
    
    def on_cost_text_changed(self, text):
        """Format cost input with thousand separators, allowing decimals."""
        if self._cost_updating:
            return
        self._cost_updating = True
        
        cursor_pos = self.total_cost_input.cursorPosition()
        old_len = len(text)
        
        # Split on decimal point
        parts = text.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else None
        
        # Keep only digits in integer part
        digits = ''.join(c for c in integer_part if c.isdigit())
        
        # Format with thousand separators
        if digits:
            formatted = ''
            for i, d in enumerate(reversed(digits)):
                if i > 0 and i % 3 == 0:
                    formatted = ' ' + formatted
                formatted = d + formatted
        else:
            formatted = ''
        
        # Re-add decimal part if present
        if decimal_part is not None:
            # Keep only digits in decimal part (max 2)
            dec_digits = ''.join(c for c in decimal_part if c.isdigit())[:2]
            formatted = formatted + '.' + dec_digits
        
        new_len = len(formatted)
        new_cursor = cursor_pos + (new_len - old_len)
        new_cursor = max(0, min(new_cursor, new_len))
        
        self.total_cost_input.setText(formatted)
        self.total_cost_input.setCursorPosition(new_cursor)
        
        self._cost_updating = False
        self.emit_labor_changed()
    
    def emit_labor_changed(self):
        """Emit the labor_changed signal with current labor list and total cost."""
        self.labor_changed.emit(self.get_selected_labor(), self.get_total_labor_cost())
    
    def get_selected_labor(self) -> list:
        """Get list of selected labor IDs."""
        return self.selected_labor.copy()
    
    def set_data(self, labor_ids: list, total_cost: float = 0.0):
        """Populate with existing labor IDs and total cost."""
        self.load_data(restore_state=False)
        for labor_id in labor_ids:
            labor = next((l for l in self.all_labor if l["id"] == labor_id), None)
            if labor:
                self.add_labor(labor_id, labor["service_name"])
        if total_cost > 0:
            self.total_cost_input.setText(self._format_cost(total_cost))

    def _format_cost(self, value: float) -> str:
        """Format a cost value with thousand separators."""
        int_part = int(value)
        dec_part = f"{value:.2f}".split('.')[1]
        formatted = ''
        int_str = str(int_part)
        for i, d in enumerate(reversed(int_str)):
            if i > 0 and i % 3 == 0:
                formatted = ' ' + formatted
            formatted = d + formatted
        return f"{formatted}.{dec_part}"

    def get_total_labor_cost(self) -> float:
        """Get the total labor cost from the input field."""
        text = self.total_cost_input.text().replace(' ', '').strip()
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0
