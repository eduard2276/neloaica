"""Employees page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QDialog,
    QFormLayout,
    QMessageBox,
)
from PySide6.QtCore import Qt

from src.database.models import (
    get_all_employees,
    add_employee,
    update_employee,
    delete_employee,
)
from src.styles import theme
from src.utils import show_warning


class EmployeeDialog(QDialog):
    """Dialog for adding or editing an employee."""

    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self.employee = employee
        self.setup_ui()

        if employee:
            self.setWindowTitle("Edit Employee")
            self.first_name_input.setText(employee["first_name"])
            self.last_name_input.setText(employee["last_name"])
        else:
            self.setWindowTitle("Add Employee")

    def setup_ui(self):
        """Setup the dialog UI."""
        self.setMinimumWidth(350)
        self.setStyleSheet(theme.dialog() + theme.line_edit_dialog())

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Enter first name")
        form_layout.addRow("First Name:", self.first_name_input)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Enter last name")
        form_layout.addRow("Last Name:", self.last_name_input)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(theme.button("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(theme.button("primary"))
        save_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.validate_and_accept()
        else:
            super().keyPressEvent(event)

    def validate_and_accept(self):
        """Validate input and accept dialog."""
        if not self.first_name_input.text().strip():
            show_warning(self, "Validation Error", "First name is required.")
            self.first_name_input.setFocus()
            return

        if not self.last_name_input.text().strip():
            show_warning(self, "Validation Error", "Last name is required.")
            self.last_name_input.setFocus()
            return

        self.accept()

    def get_data(self):
        """Get the form data."""
        return {
            "first_name": self.first_name_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
        }


class EmployeesPage(QWidget):
    """Employees page content."""

    def __init__(self):
        super().__init__()
        self.all_employees = []
        self.setup_ui()
        self.load_data()

    def showEvent(self, event):
        """Called when the page is shown. Reload data to reflect any changes."""
        super().showEvent(event)
        self.load_data()
        self.filter_employees(self.search_input.text())

    def setup_ui(self):
        """Setup the employees UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = QLabel("🧑‍💼 Employees")
        title.setStyleSheet(theme.page_title())
        header_layout.addWidget(title)
        layout.addLayout(header_layout)

        toolbar_layout = QHBoxLayout()

        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search employees by name...")
        self.search_input.setStyleSheet(theme.search_input())
        self.search_input.textChanged.connect(self.filter_employees)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addSpacing(20)

        add_btn = QPushButton("➕ Add Employee")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_employee)
        toolbar_layout.addWidget(add_btn)

        layout.addLayout(toolbar_layout)

        self.employees_table = QTableWidget()
        self.employees_table.setStyleSheet(theme.table())
        self.employees_table.setAlternatingRowColors(True)
        self.employees_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.employees_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.employees_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.employees_table.verticalHeader().setVisible(False)
        self.employees_table.verticalHeader().setDefaultSectionSize(50)
        self.employees_table.setColumnCount(4)
        self.employees_table.setHorizontalHeaderLabels(["ID", "First Name", "Last Name", "Actions"])
        self.employees_table.doubleClicked.connect(self.edit_employee)

        layout.addWidget(self.employees_table)

    def load_data(self):
        """Load employees data from the database."""
        self.all_employees = get_all_employees()
        self.display_employees(self.all_employees)

    def filter_employees(self, search_text: str):
        """Filter employees based on search text."""
        search_text = search_text.lower().strip()

        if not search_text:
            filtered = self.all_employees
        else:
            filtered = [
                emp for emp in self.all_employees
                if search_text in emp["first_name"].lower()
                or search_text in emp["last_name"].lower()
                or search_text in f"{emp['first_name']} {emp['last_name']}".lower()
            ]

        self.display_employees(filtered)

    def display_employees(self, employees: list):
        """Display employees in the table."""
        self.employees_table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            id_item = QTableWidgetItem(str(emp["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, emp["id"])
            self.employees_table.setItem(row, 0, id_item)

            self.employees_table.setItem(row, 1, QTableWidgetItem(emp["first_name"]))
            self.employees_table.setItem(row, 2, QTableWidgetItem(emp["last_name"]))

            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee_by_id(e["id"]))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee_by_id(e["id"]))
            actions_layout.addWidget(delete_btn)

            self.employees_table.setCellWidget(row, 3, actions_widget)

        header = self.employees_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.employees_table.setColumnWidth(3, 100)

    def add_employee(self):
        """Open dialog to add a new employee."""
        dialog = EmployeeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_employee(data["first_name"], data["last_name"])
            self.load_data()
            self.search_input.clear()

    def edit_employee(self):
        """Open dialog to edit the selected employee."""
        selected = self.employees_table.selectionModel().selectedRows()
        if not selected:
            show_warning(self, "No Selection", "Please select an employee to edit.")
            return

        row = selected[0].row()
        emp_id = self.employees_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.edit_employee_by_id(emp_id)

    def edit_employee_by_id(self, employee_id: int):
        """Edit an employee by ID."""
        emp = next((e for e in self.all_employees if e["id"] == employee_id), None)
        if not emp:
            return

        dialog = EmployeeDialog(self, emp)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_employee(emp["id"], data["first_name"], data["last_name"])
            self.load_data()
            self.filter_employees(self.search_input.text())

    def delete_employee_by_id(self, employee_id: int):
        """Delete an employee by ID."""
        emp = next((e for e in self.all_employees if e["id"] == employee_id), None)
        if not emp:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(
            f"Are you sure you want to delete {emp['first_name']} {emp['last_name']}?"
        )
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(theme.message_box_confirm())

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            delete_employee(employee_id)
            self.load_data()
            self.filter_employees(self.search_input.text())
