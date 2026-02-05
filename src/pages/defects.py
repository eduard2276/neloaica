"""Defects page."""

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
    get_all_defects,
    add_defect,
    update_defect,
    delete_defect,
)
from src.styles import theme


class DefectDialog(QDialog):
    """Dialog for adding/editing defects."""

    def __init__(self, parent=None, defect_data=None):
        super().__init__(parent)
        self.defect_data = defect_data
        self.setup_ui()
        
        if defect_data:
            self.setWindowTitle("Edit Defect")
            self.populate_data()
        else:
            self.setWindowTitle("Add Defect")

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

    def populate_data(self):
        """Populate form with existing data."""
        if self.defect_data:
            self.defect_name_edit.setText(self.defect_data.get("defect_name", ""))

    def get_data(self) -> dict:
        """Get form data."""
        return {
            "defect_name": self.defect_name_edit.text().strip(),
        }

    def accept(self):
        """Validate and accept the dialog."""
        data = self.get_data()
        
        if not data["defect_name"]:
            QMessageBox.warning(self, "Validation Error", "Defect description is required.")
            self.defect_name_edit.setFocus()
            return
        
        super().accept()


class DefectsPage(QWidget):
    """Defects management page."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Set up the page UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("⚠️ Defects")
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
        self.search_edit.setPlaceholderText("Search defects...")
        self.search_edit.textChanged.connect(self.filter_defects)
        self.search_edit.setStyleSheet(theme.search_input())
        toolbar_layout.addWidget(self.search_edit)
        
        toolbar_layout.addSpacing(20)
        
        # Action buttons
        add_btn = QPushButton("➕ Add Defect")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_defect)
        toolbar_layout.addWidget(add_btn)
        
        layout.addLayout(toolbar_layout)

        # Defects table
        self.table = QTableWidget()
        self.table.setStyleSheet(theme.table())
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Defect", "Actions"])
        self.table.doubleClicked.connect(self.edit_defect)
        
        layout.addWidget(self.table)

    def load_data(self):
        """Load defects data into the table."""
        self.all_defects = get_all_defects()
        self.display_defects(self.all_defects)

    def display_defects(self, defects_list: list[dict]):
        """Display defects in the table."""
        self.table.setRowCount(len(defects_list))
        
        for row, defect in enumerate(defects_list):
            id_item = QTableWidgetItem(str(defect["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, defect["id"])
            self.table.setItem(row, 0, id_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(defect["defect_name"]))
            
            # Actions column with Edit and Delete buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, d=defect: self.edit_defect_by_id(d["id"]))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, d=defect: self.delete_defect_by_id(d["id"]))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 2, actions_widget)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)

    def filter_defects(self, text: str):
        """Filter defects based on search text."""
        if not text:
            self.display_defects(self.all_defects)
            return
        
        text = text.lower()
        filtered = [
            defect for defect in self.all_defects
            if text in str(defect["id"]).lower()
            or text in defect["defect_name"].lower()
        ]
        self.display_defects(filtered)

    def get_selected_defect_id(self) -> int | None:
        """Get the ID of the selected defect."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        id_item = self.table.item(row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def add_defect(self):
        """Add a new defect."""
        dialog = DefectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_defect(data["defect_name"])
            self.load_data()

    def edit_defect(self):
        """Edit the selected defect."""
        defect_id = self.get_selected_defect_id()
        if not defect_id:
            QMessageBox.warning(self, "No Selection", "Please select a defect to edit.")
            return
        
        # Find the defect data
        defect_data = next((d for d in self.all_defects if d["id"] == defect_id), None)
        if not defect_data:
            return
        
        dialog = DefectDialog(self, defect_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_defect(defect_id, data["defect_name"])
            self.load_data()

    def delete_defect(self):
        """Delete the selected defect."""
        defect_id = self.get_selected_defect_id()
        if not defect_id:
            QMessageBox.warning(self, "No Selection", "Please select a defect to delete.")
            return
        
        # Find the defect data for the confirmation message
        defect_data = next((d for d in self.all_defects if d["id"] == defect_id), None)
        if not defect_data:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the defect '{defect_data['defect_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2c3e50;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
                background-color: #2c3e50;
            }
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:default {
                background-color: #3498db;
            }
            QPushButton:default:hover {
                background-color: #2980b9;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_defect(defect_id)
            self.load_data()
    
    def edit_defect_by_id(self, defect_id: int):
        """Edit a defect by ID (used by row action buttons)."""
        # Find the defect data
        defect_data = next((d for d in self.all_defects if d["id"] == defect_id), None)
        if not defect_data:
            return
        
        dialog = DefectDialog(self, defect_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_defect(defect_id, data["defect_name"])
            self.load_data()
    
    def delete_defect_by_id(self, defect_id: int):
        """Delete a defect by ID (used by row action buttons)."""
        # Find the defect data for the confirmation message
        defect_data = next((d for d in self.all_defects if d["id"] == defect_id), None)
        if not defect_data:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the defect '{defect_data['defect_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2c3e50;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
                background-color: #2c3e50;
            }
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:default {
                background-color: #3498db;
            }
            QPushButton:default:hover {
                background-color: #2980b9;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_defect(defect_id)
            self.load_data()
