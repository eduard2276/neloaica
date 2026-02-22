"""Labor/Services page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
    QFormLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt

from src.database.models import (
    get_all_labor,
    add_labor,
    update_labor,
    delete_labor,
)
from src.styles import theme
from src.utils import show_warning


class LaborDialog(QDialog):
    """Dialog for adding/editing labor services."""

    def __init__(self, parent=None, labor_data=None):
        super().__init__(parent)
        self.labor_data = labor_data
        self.setup_ui()
        
        if labor_data:
            self.setWindowTitle("Edit Service")
            self.populate_data()
        else:
            self.setWindowTitle("Add Service")

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
        form_layout.addRow("Service Name:", self.service_name_edit)
        
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

    def populate_data(self):
        """Populate form with existing data."""
        if self.labor_data:
            self.service_name_edit.setText(self.labor_data.get("service_name", ""))

    def get_data(self) -> dict:
        """Get form data."""
        return {
            "service_name": self.service_name_edit.text().strip(),
        }

    def accept(self):
        """Validate and accept the dialog."""
        data = self.get_data()
        
        if not data["service_name"]:
            show_warning(self, "Validation Error", "Service name is required.")
            self.service_name_edit.setFocus()
            return
        
        super().accept()


class LaborPage(QWidget):
    """Labor/Services management page."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()

    def showEvent(self, event):
        """Called when the page is shown. Reload data to reflect any changes."""
        super().showEvent(event)
        self.load_data()

    def setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("⚙️ Labor Services")
        title.setStyleSheet(theme.page_title())
        header_layout.addWidget(title)
        
        layout.addLayout(header_layout)

        # Toolbar: Search and Action buttons
        toolbar_layout = QHBoxLayout()
        
        # Search bar
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        toolbar_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search services...")
        self.search_edit.textChanged.connect(self.filter_labor)
        self.search_edit.setStyleSheet(theme.search_input())
        toolbar_layout.addWidget(self.search_edit)
        
        toolbar_layout.addSpacing(20)
        
        # Action buttons
        add_btn = QPushButton("➕ Add Service")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_labor)
        toolbar_layout.addWidget(add_btn)
        
        layout.addLayout(toolbar_layout)

        # Labor table
        self.table = QTableWidget()
        self.table.setStyleSheet(theme.table())
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Service Name", "Actions"])
        self.table.doubleClicked.connect(self.edit_labor)
        
        layout.addWidget(self.table)

    def load_data(self):
        """Load labor data into the table."""
        self.all_labor = get_all_labor()
        self.display_labor(self.all_labor)

    def display_labor(self, labor_list: list[dict]):
        """Display labor services in the table."""
        self.table.setRowCount(len(labor_list))
        
        for row, labor in enumerate(labor_list):
            id_item = QTableWidgetItem(str(labor["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, labor["id"])
            self.table.setItem(row, 0, id_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(labor["service_name"]))
            
            # Actions column with Edit and Delete buttons
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, l=labor: self.edit_labor_by_id(l["id"]))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, l=labor: self.delete_labor_by_id(l["id"]))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 2, actions_widget)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)

    def filter_labor(self, text: str):
        """Filter labor services based on search text."""
        if not text:
            self.display_labor(self.all_labor)
            return
        
        text = text.lower()
        filtered = [
            labor for labor in self.all_labor
            if text in str(labor["id"]).lower()
            or text in labor["service_name"].lower()
        ]
        self.display_labor(filtered)

    def get_selected_labor_id(self) -> int | None:
        """Get the ID of the selected labor service."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        id_item = self.table.item(row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def add_labor(self):
        """Add a new labor service."""
        dialog = LaborDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_labor(data["service_name"])
            self.load_data()

    def edit_labor(self):
        """Edit the selected labor service."""
        labor_id = self.get_selected_labor_id()
        if not labor_id:
            show_warning(self, "No Selection", "Please select a service to edit.")
            return
        
        # Find the labor data
        labor_data = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if not labor_data:
            return
        
        dialog = LaborDialog(self, labor_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_labor(labor_id, data["service_name"])
            self.load_data()

    def delete_labor(self):
        """Delete the selected labor service."""
        labor_id = self.get_selected_labor_id()
        if not labor_id:
            show_warning(self, "No Selection", "Please select a service to delete.")
            return
        
        # Find the labor data for the confirmation message
        labor_data = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if not labor_data:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the service '{labor_data['service_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet(theme.message_box_confirm())
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_labor(labor_id)
            self.load_data()
    
    def edit_labor_by_id(self, labor_id: int):
        """Edit a labor service by ID (used by row action buttons)."""
        # Find the labor data
        labor_data = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if not labor_data:
            return
        
        dialog = LaborDialog(self, labor_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_labor(labor_id, data["service_name"])
            self.load_data()
    
    def delete_labor_by_id(self, labor_id: int):
        """Delete a labor service by ID (used by row action buttons)."""
        # Find the labor data for the confirmation message
        labor_data = next((l for l in self.all_labor if l["id"] == labor_id), None)
        if not labor_data:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the service '{labor_data['service_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet(theme.message_box_confirm())
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_labor(labor_id)
            self.load_data()
