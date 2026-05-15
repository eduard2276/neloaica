"""Parts page."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.models import (
    add_part,
    delete_part,
    get_all_parts,
    get_part_by_name,
    update_part,
)
from src.styles import theme
from src.utils import show_warning


class PartDialog(QDialog):
    """Dialog for adding/editing parts."""

    def __init__(self, parent=None, part_data=None):
        super().__init__(parent)
        self.part_data = part_data
        self.setup_ui()

        if part_data:
            self.setWindowTitle("Edit Part")
            self.populate_data()
        else:
            self.setWindowTitle("Add Part")

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
        form_layout.addRow("Part Name:", self.part_name_edit)

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
        if self.part_data:
            self.part_name_edit.setText(self.part_data.get("part_name", ""))

    def get_data(self) -> dict:
        """Get form data."""
        return {
            "part_name": self.part_name_edit.text().strip(),
        }

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)

    def accept(self):
        """Validate and accept the dialog."""
        data = self.get_data()

        if not data["part_name"]:
            show_warning(self, "Validation Error", "Part name is required.")
            self.part_name_edit.setFocus()
            return

        super().accept()


class PartsPage(QWidget):
    """Parts management page."""

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

        title = QLabel("🔧 Parts")
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
        self.search_edit.setPlaceholderText("Search parts...")
        self.search_edit.textChanged.connect(self.filter_parts)
        self.search_edit.setStyleSheet(theme.search_input())
        toolbar_layout.addWidget(self.search_edit)

        toolbar_layout.addSpacing(20)

        # Action buttons
        add_btn = QPushButton("➕ Add Part")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_part)
        toolbar_layout.addWidget(add_btn)

        layout.addLayout(toolbar_layout)

        # Parts table
        self.table = QTableWidget()
        self.table.setStyleSheet(theme.table())
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Part Name", "Actions"])
        self.table.doubleClicked.connect(self.edit_part)

        layout.addWidget(self.table)

    def load_data(self):
        """Load parts data into the table."""
        self.all_parts = get_all_parts()
        self.display_parts(self.all_parts)

    def display_parts(self, parts_list: list[dict]):
        """Display parts in the table."""
        self.table.setRowCount(len(parts_list))

        for row, part in enumerate(parts_list):
            id_item = QTableWidgetItem(str(part["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, part["id"])
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1, QTableWidgetItem(part["part_name"]))

            # Actions column with Edit and Delete buttons
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, p=part: self.edit_part_by_id(p["id"]))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, p=part: self.delete_part_by_id(p["id"]))
            actions_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 2, actions_widget)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)

    def filter_parts(self, text: str):
        """Filter parts based on search text."""
        if not text:
            self.display_parts(self.all_parts)
            return

        text = text.lower()
        filtered = [
            part
            for part in self.all_parts
            if text in str(part["id"]).lower() or text in part["part_name"].lower()
        ]
        self.display_parts(filtered)

    def get_selected_part_id(self) -> int | None:
        """Get the ID of the selected part."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        id_item = self.table.item(row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def add_part(self):
        """Add a new part."""
        dialog = PartDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            existing = get_part_by_name(data["part_name"])
            if existing:
                show_warning(
                    self,
                    "Duplicate Entry",
                    f"A part named '{existing['part_name']}' already exists.",
                )
                return
            add_part(data["part_name"])
            self.load_data()

    def edit_part(self):
        """Edit the selected part."""
        part_id = self.get_selected_part_id()
        if not part_id:
            show_warning(self, "No Selection", "Please select a part to edit.")
            return

        # Find the part data
        part_data = next((p for p in self.all_parts if p["id"] == part_id), None)
        if not part_data:
            return

        dialog = PartDialog(self, part_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_part(part_id, data["part_name"])
            self.load_data()

    def delete_part(self):
        """Delete the selected part."""
        part_id = self.get_selected_part_id()
        if not part_id:
            show_warning(self, "No Selection", "Please select a part to delete.")
            return

        # Find the part data for the confirmation message
        part_data = next((p for p in self.all_parts if p["id"] == part_id), None)
        if not part_data:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the part '{part_data['part_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        msg_box.setStyleSheet(theme.message_box_confirm())

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            delete_part(part_id)
            self.load_data()

    def edit_part_by_id(self, part_id: int):
        """Edit a part by ID (used by row action buttons)."""
        # Find the part data
        part_data = next((p for p in self.all_parts if p["id"] == part_id), None)
        if not part_data:
            return

        dialog = PartDialog(self, part_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            existing = get_part_by_name(data["part_name"])
            if existing and existing["id"] != part_id:
                show_warning(
                    self,
                    "Duplicate Entry",
                    f"A part named '{existing['part_name']}' already exists.",
                )
                return
            update_part(part_id, data["part_name"])
            self.load_data()

    def delete_part_by_id(self, part_id: int):
        """Delete a part by ID (used by row action buttons)."""
        # Find the part data for the confirmation message
        part_data = next((p for p in self.all_parts if p["id"] == part_id), None)
        if not part_data:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete the part '{part_data['part_name']}'?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        msg_box.setStyleSheet(theme.message_box_confirm())

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            delete_part(part_id)
            self.load_data()
