"""Parts section - Parts received from client."""

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

from src.database.models.parts import get_all_parts, add_part as add_part_to_db, get_part_by_name
from src.widgets import NoScrollComboBox
from src.styles import theme
from src.utils import show_warning, show_info, show_critical


class AddPartDialog(QDialog):
    """Dialog for adding a new part."""

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

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def accept(self):
        """Validate and accept the dialog."""
        if not self.get_part_name():
            show_warning(self, "Validation Error", "Part name is required.")
            self.part_name_edit.setFocus()
            return
        
        super().accept()


class PartsSectionWidget(QWidget):
    """Widget for parts received from client section."""
    
    # Signal to notify parent when parts list changes
    parts_changed = Signal(list)  # Emits list of selected part IDs
    
    def __init__(self, title="Parts received from client"):
        super().__init__()
        self.title = title
        self.all_parts = []
        self.selected_parts = []
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the parts section UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Parts section
        parts_group = QGroupBox(self.title)
        parts_group.setStyleSheet(theme.groupbox())
        
        parts_layout = QVBoxLayout()
        parts_layout.setSpacing(15)
        
        # Part selection row with add button
        part_selection_layout = QHBoxLayout()
        
        self.part_combo = NoScrollComboBox()
        self.part_combo.setPlaceholderText("Select a part")
        self.part_combo.currentIndexChanged.connect(self.on_part_changed)
        self.part_combo.setStyleSheet(theme.combobox())
        
        # Add new part button
        self.add_new_part_btn = QPushButton("➕")
        self.add_new_part_btn.setToolTip("Add new part to database")
        self.add_new_part_btn.setFixedSize(44, 44)
        self.add_new_part_btn.clicked.connect(self.add_new_part_to_database)
        self.add_new_part_btn.setStyleSheet(theme.button_add())
        
        part_selection_layout.addWidget(self.part_combo)
        part_selection_layout.addWidget(self.add_new_part_btn)
        parts_layout.addLayout(part_selection_layout)
        
        # List of selected parts
        self.parts_list = QListWidget()
        self.parts_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.parts_list.setStyleSheet(theme.list_widget())
        self.update_list_style()
        parts_layout.addWidget(self.parts_list)
        
        parts_group.setLayout(parts_layout)
        layout.addWidget(parts_group)
    
    def load_data(self, restore_state=False):
        """Load parts from database."""
        if not restore_state:
            self.selected_parts = []
            self.parts_list.clear()

        # Get all parts
        self.all_parts = get_all_parts()
        
        # Clear and repopulate combo
        self.part_combo.clear()
        self.part_combo.addItem("Select a part", None)
        
        # Add parts that are not in selected list
        for part in self.all_parts:
            if part['id'] not in self.selected_parts:
                self.part_combo.addItem(part['part_name'], part['id'])

        if not restore_state:
            self.update_list_style()
            self.parts_changed.emit([])
    
    def on_part_changed(self, index):
        """Handle part selection change."""
        if index <= 0:  # Skip placeholder
            return
        
        part_id = self.part_combo.itemData(index)
        if part_id is not None:
            # Find the part
            part = next((p for p in self.all_parts if p['id'] == part_id), None)
            if part:
                # Block signals to prevent triggering during manipulation
                self.part_combo.blockSignals(True)
                self.add_part(part)
                # Reset combo to placeholder
                self.part_combo.setCurrentIndex(0)
                self.part_combo.blockSignals(False)
    
    def add_part(self, part: dict):
        """Add a part to the selected list."""
        if part['id'] in self.selected_parts:
            return  # Already in list
        
        # Add to selected parts
        self.selected_parts.append(part['id'])
        
        # Create list item
        item_widget = QWidget()
        item_widget.setObjectName("partItem")
        item_widget.setStyleSheet("#partItem, #partItem * { background-color: white; } #partItem { border-bottom: 1px solid #bdc3c7; }")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(10, 8, 10, 8)
        
        part_label = QLabel(part['part_name'])
        part_label.setStyleSheet(theme.label_item())
        
        remove_btn = QPushButton("🗑️")
        remove_btn.setFixedSize(30, 30)
        remove_btn.setStyleSheet(theme.button_icon("delete"))
        remove_btn.clicked.connect(lambda checked, p_id=part['id']: self.remove_part(p_id))
        
        item_layout.addWidget(part_label)
        item_layout.addStretch()
        item_layout.addWidget(remove_btn)
        
        list_item = QListWidgetItem(self.parts_list)
        list_item.setSizeHint(QSize(0, 46))
        self.parts_list.addItem(list_item)
        self.parts_list.setItemWidget(list_item, item_widget)
        
        # Remove from combo
        for i in range(self.part_combo.count()):
            if self.part_combo.itemData(i) == part['id']:
                self.part_combo.removeItem(i)
                break
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.parts_changed.emit(self.selected_parts.copy())
    
    def remove_part(self, part_id: int):
        """Remove a part from the selected list."""
        if part_id not in self.selected_parts:
            return
        
        # Remove from selected parts
        self.selected_parts.remove(part_id)
        
        # Find and remove the list item
        for i in range(self.parts_list.count()):
            item = self.parts_list.item(i)
            widget = self.parts_list.itemWidget(item)
            if widget:
                label = widget.findChild(QLabel)
                if label:
                    # Find the part to check the name
                    part = next((p for p in self.all_parts if p['id'] == part_id), None)
                    if part and label.text() == part['part_name']:
                        self.parts_list.takeItem(i)
                        break
        
        # Add back to combo
        part = next((p for p in self.all_parts if p['id'] == part_id), None)
        if part:
            # Insert in alphabetical order
            inserted = False
            for i in range(1, self.part_combo.count()):  # Skip placeholder at 0
                if self.part_combo.itemText(i) > part['part_name']:
                    self.part_combo.insertItem(i, part['part_name'], part['id'])
                    inserted = True
                    break
            
            if not inserted:
                self.part_combo.addItem(part['part_name'], part['id'])
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.parts_changed.emit(self.selected_parts.copy())
    
    def update_list_style(self):
        """Update list widget background and height based on item count."""
        if len(self.selected_parts) > 0:
            self.parts_list.setStyleSheet(theme.list_widget_with_items())
        else:
            self.parts_list.setStyleSheet(theme.list_widget())
        self._resize_list()

    def _resize_list(self):
        """Resize list widget height to fit all items without scrollbar."""
        count = self.parts_list.count()
        if count == 0:
            self.parts_list.setFixedHeight(0)
            return
        total = sum(
            self.parts_list.sizeHintForRow(i) for i in range(count)
        )
        margins = self.parts_list.contentsMargins()
        total += margins.top() + margins.bottom() + 4
        self.parts_list.setFixedHeight(total)
    
    def add_new_part_to_database(self):
        """Open dialog to add a new part to the database."""
        dialog = AddPartDialog(self)
        if dialog.exec():
            part_name = dialog.get_part_name()

            existing = get_part_by_name(part_name)
            if existing:
                show_warning(
                    self, "Duplicate Entry",
                    f"A part named '{existing['part_name']}' already exists."
                )
                return

            try:
                # Add to database
                part_id = add_part_to_db(part_name)
                
                # Reload data
                self.load_data()
                
                # Show success message
                show_info(self, "Success", f"Part '{part_name}' has been added to the database.")
            except Exception as e:
                show_critical(self, "Error", f"Failed to add part: {str(e)}")
    
    def set_data(self, part_ids: list):
        """Populate with existing part IDs."""
        self.load_data(restore_state=False)
        for part_id in part_ids:
            part = next((p for p in self.all_parts if p['id'] == part_id), None)
            if part:
                self.add_part(part)

    def get_selected_parts(self) -> list:
        """Get the list of selected part IDs."""
        return self.selected_parts.copy()
