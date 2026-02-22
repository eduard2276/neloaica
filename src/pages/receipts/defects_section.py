"""Defects section - Client defects selection and management."""

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
    QFrame,
)
from PySide6.QtCore import Qt, Signal

from src.database.models import get_all_defects
from src.database.models.defects import add_defect as add_defect_to_db
from src.widgets import NoScrollComboBox
from src.styles import theme
from src.utils import show_warning, show_info, show_critical


class AddDefectDialog(QDialog):
    """Dialog for adding a new defect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Defect")
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
        
        # Defect Name field
        self.defect_name_edit = QLineEdit()
        self.defect_name_edit.setPlaceholderText("Enter defect description")
        self.defect_name_edit.setMinimumHeight(35)
        form_layout.addRow("Defect:", self.defect_name_edit)
        
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

    def get_defect_name(self) -> str:
        """Get the defect name."""
        return self.defect_name_edit.text().strip()

    def accept(self):
        """Validate and accept the dialog."""
        if not self.get_defect_name():
            show_warning(self, "Validation Error", "Defect description is required.")
            self.defect_name_edit.setFocus()
            return
        
        super().accept()


class DefectsSectionWidget(QWidget):
    """Widget for defects by the client section."""
    
    # Signal to notify parent when defects list changes
    defects_changed = Signal(list)  # Emits list of selected defect IDs
    
    def __init__(self, title="Defects by the Client"):
        super().__init__()
        self.title = title
        self.all_defects = []
        self.selected_defects = []
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the defects section UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Defects section
        defects_group = QGroupBox(self.title)
        defects_group.setStyleSheet(theme.groupbox())
        
        defects_layout = QVBoxLayout()
        defects_layout.setSpacing(15)
        
        # Defect selection row with add button
        defect_selection_layout = QHBoxLayout()
        
        self.defect_combo = NoScrollComboBox()
        self.defect_combo.setPlaceholderText("Select a defect")
        self.defect_combo.currentIndexChanged.connect(self.on_defect_changed)
        self.defect_combo.setStyleSheet(theme.combobox())
        
        # Add new defect button
        self.add_new_defect_btn = QPushButton("➕")
        self.add_new_defect_btn.setFixedSize(44, 44)
        self.add_new_defect_btn.setToolTip("Add new defect to database")
        self.add_new_defect_btn.clicked.connect(self.add_new_defect_to_database)
        self.add_new_defect_btn.setStyleSheet(theme.button_add())
        
        defect_selection_layout.addWidget(self.defect_combo)
        defect_selection_layout.addWidget(self.add_new_defect_btn)
        
        defects_layout.addLayout(defect_selection_layout)
        
        # Defects list
        self.defects_list = QListWidget()
        self.defects_list.setStyleSheet(theme.list_widget())
        self.defects_list.setMinimumHeight(150)
        self.update_list_style()  # Set initial style
        
        defects_layout.addWidget(self.defects_list)
        
        defects_group.setLayout(defects_layout)
        layout.addWidget(defects_group)
    
    def load_data(self, restore_state=False):
        """Load defects from database."""
        self.all_defects = get_all_defects()
        
        # Populate defects dropdown
        self.defect_combo.clear()
        self.defect_combo.addItem("Select a defect", None)
        for defect in self.all_defects:
            # Only add if not already selected
            if defect['id'] not in self.selected_defects:
                self.defect_combo.addItem(defect['defect_name'], defect['id'])
    
    def on_defect_changed(self, index):
        """Handle defect selection change - automatically add to list."""
        if index <= 0:  # Skip placeholder
            return
        
        defect_id = self.defect_combo.currentData()
        if defect_id is not None:
            self.add_defect()
    
    def add_defect(self):
        """Add selected defect to the list."""
        defect_id = self.defect_combo.currentData()
        if defect_id is None:
            return
        
        # Check if defect is already added
        if defect_id in self.selected_defects:
            self.defect_combo.setCurrentIndex(0)
            return
        
        # Add to selected defects list
        self.selected_defects.append(defect_id)
        
        # Get defect name for display
        defect = next((d for d in self.all_defects if d['id'] == defect_id), None)
        if defect:
            # Create list item with delete button
            item_widget = QWidget()
            item_widget.setObjectName("defectItem")
            item_widget.setStyleSheet("#defectItem, #defectItem * { background-color: white; } #defectItem { border-bottom: 1px solid #bdc3c7; }")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 8, 10, 8)
            
            # Defect label
            defect_label = QLabel(defect['defect_name'])
            defect_label.setStyleSheet(theme.label_item())
            
            # Delete button
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, d_id=defect_id: self.remove_defect(d_id))
            
            item_layout.addWidget(defect_label)
            item_layout.addStretch()
            item_layout.addWidget(delete_btn)
            
            # Add to list widget
            list_item = QListWidgetItem(self.defects_list)
            from PySide6.QtCore import QSize
            list_item.setSizeHint(QSize(0, 46))
            list_item.setData(Qt.ItemDataRole.UserRole, defect_id)
            self.defects_list.addItem(list_item)
            self.defects_list.setItemWidget(list_item, item_widget)
        
        # Remove from dropdown
        current_index = self.defect_combo.currentIndex()
        self.defect_combo.blockSignals(True)
        self.defect_combo.removeItem(current_index)
        self.defect_combo.setCurrentIndex(0)
        self.defect_combo.blockSignals(False)
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.defects_changed.emit(self.selected_defects.copy())
    
    def remove_defect(self, defect_id):
        """Remove defect from the list."""
        # Remove from selected defects
        if defect_id in self.selected_defects:
            self.selected_defects.remove(defect_id)
        
        # Remove from list widget
        for i in range(self.defects_list.count()):
            item = self.defects_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == defect_id:
                self.defects_list.takeItem(i)
                break
        
        # Add back to dropdown
        defect = next((d for d in self.all_defects if d['id'] == defect_id), None)
        if defect:
            self.defect_combo.blockSignals(True)
            self.defect_combo.addItem(defect['defect_name'], defect['id'])
            self.defect_combo.blockSignals(False)
        
        # Update list style based on item count
        self.update_list_style()
        
        # Emit signal
        self.defects_changed.emit(self.selected_defects.copy())
    
    def add_new_defect_to_database(self):
        """Open dialog to add a new defect to the database."""
        dialog = AddDefectDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            defect_name = dialog.get_defect_name()
            
            try:
                # Add to database
                new_defect_id = add_defect_to_db(defect_name)
                
                # Reload defects from database
                self.all_defects = get_all_defects()
                
                # Add to dropdown if not already selected
                if new_defect_id not in self.selected_defects:
                    self.defect_combo.blockSignals(True)
                    self.defect_combo.addItem(defect_name, new_defect_id)
                    self.defect_combo.blockSignals(False)
                
                show_info(self, "Success", f"Defect '{defect_name}' added successfully!")
            except Exception as e:
                show_critical(self, "Error", f"Failed to add defect: {str(e)}")
    
    def update_list_style(self):
        """Update list widget background based on item count."""
        if len(self.selected_defects) > 0:
            # White background when items are present
            self.defects_list.setStyleSheet(theme.list_widget_with_items())
        else:
            # Grey background when empty
            self.defects_list.setStyleSheet(theme.list_widget())
    
    def get_selected_defects(self) -> list:
        """Get list of selected defect IDs."""
        return self.selected_defects.copy()
