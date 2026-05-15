"""Cars page."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    add_car,
    delete_car,
    get_all_cars,
    get_clients_for_dropdown,
    update_car,
)
from src.styles import theme
from src.utils import show_critical, show_warning


class CarDialog(QDialog):
    """Dialog for adding or editing a car."""

    def __init__(self, parent=None, car=None):
        super().__init__(parent)
        self.car = car
        self.clients = get_clients_for_dropdown()
        # Sort clients alphabetically by name
        self.clients.sort(key=lambda c: c["name"].lower())
        self._km_updating = False
        self.setup_ui()

        if car:
            self.setWindowTitle("Edit Car")
            # Set client dropdown
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == car["client_id"]:
                    self.client_combo.setCurrentIndex(i)
                    break
            self.plate_input.setText(car["plate_number"])
            self.vin_input.setText(car["vin"])
            self.model_input.setText(car["model"])
            km_value = car.get("kilometers", 0)
            if km_value > 0:
                self.kilometers_input.setText(self.format_kilometers(km_value))
        else:
            self.setWindowTitle("Add Car")

    def setup_ui(self):
        """Setup the dialog UI."""
        self.setMinimumWidth(400)
        self.setStyleSheet(theme.dialog() + theme.line_edit_dialog() + theme.combobox())

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Client dropdown
        self.client_combo = QComboBox()
        self.client_combo.addItem("-- Select Client --", None)
        for client in self.clients:
            self.client_combo.addItem(client["name"], client["id"])
        form_layout.addRow("Client:", self.client_combo)

        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("Enter plate number (e.g., ABC-1234)")
        form_layout.addRow("Plate Number:", self.plate_input)

        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Enter VIN (17 characters)")
        self.vin_input.setMaxLength(17)
        form_layout.addRow("VIN:", self.vin_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Enter model (e.g., Audi A4)")
        form_layout.addRow("Model:", self.model_input)

        self.kilometers_input = QLineEdit()
        self.kilometers_input.setPlaceholderText("e.g. 120 000")
        self.kilometers_input.textChanged.connect(self.on_km_text_changed)
        form_layout.addRow("Kilometers:", self.kilometers_input)

        layout.addLayout(form_layout)

        # Buttons
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

    def on_km_text_changed(self, text):
        """Handle kilometers input change with formatting."""
        if self._km_updating:
            return

        self._km_updating = True

        # Get cursor position before formatting
        cursor_pos = self.kilometers_input.cursorPosition()
        old_text = text

        # Remove all non-digit characters
        digits_only = "".join(c for c in text if c.isdigit())

        # Format with thousand separators
        if digits_only:
            formatted = self.format_kilometers(int(digits_only))
        else:
            formatted = ""

        # Calculate new cursor position
        # Count how many digits were before the cursor in old text
        digits_before_cursor = sum(1 for c in old_text[:cursor_pos] if c.isdigit())

        # Find where to place cursor in new formatted text
        new_cursor_pos = 0
        digit_count = 0
        for i, c in enumerate(formatted):
            if digit_count >= digits_before_cursor:
                break
            if c.isdigit():
                digit_count += 1
            new_cursor_pos = i + 1

        # Update the text
        self.kilometers_input.setText(formatted)
        self.kilometers_input.setCursorPosition(new_cursor_pos)

        self._km_updating = False

    def format_kilometers(self, value) -> str:
        """Format a number with thousand separators (spaces)."""
        try:
            num = int(value)
            # Format with spaces as thousand separators
            formatted = f"{num:,}".replace(",", " ")
            return formatted
        except (ValueError, TypeError):
            return str(value) if value else ""

    def parse_kilometers(self, text: str) -> int:
        """Parse formatted kilometers text to raw number."""
        # Remove all spaces and non-digit characters
        digits = "".join(c for c in text if c.isdigit())
        try:
            return int(digits) if digits else 0
        except ValueError:
            return 0

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.validate_and_accept()
        else:
            super().keyPressEvent(event)

    def validate_and_accept(self):
        """Validate input and accept dialog."""
        client_id = self.client_combo.currentData()
        plate_number = self.plate_input.text().strip()
        vin = self.vin_input.text().strip()
        model = self.model_input.text().strip()
        kilometers_text = self.kilometers_input.text().strip()

        # Validate client selection
        if not client_id:
            show_warning(self, "Validation Error", "Please select a client.")
            self.client_combo.setFocus()
            return

        # Validate plate number
        if not plate_number:
            show_warning(self, "Validation Error", "Plate number is required.")
            self.plate_input.setFocus()
            return

        # Plate number must contain at least one dash
        if "-" not in plate_number:
            show_warning(
                self,
                "Validation Error",
                "Plate number must contain at least one dash (e.g., ABC-1234).",
            )
            self.plate_input.setFocus()
            return

        # Plate number cannot be only numeric (excluding dashes/spaces)
        plate_alphanumeric = "".join(c for c in plate_number if c.isalnum())
        if plate_alphanumeric.isdigit():
            show_warning(
                self,
                "Validation Error",
                "Plate number cannot contain only numbers. It must include letters.",
            )
            self.plate_input.setFocus()
            return

        # Validate VIN
        if not vin:
            show_warning(self, "Validation Error", "VIN is required.")
            self.vin_input.setFocus()
            return

        if len(vin) != 17:
            show_warning(self, "Validation Error", "VIN must be exactly 17 characters.")
            self.vin_input.setFocus()
            return

        # Validate model
        if not model:
            show_warning(self, "Validation Error", "Model is required.")
            self.model_input.setFocus()
            return

        # Validate kilometers
        if not kilometers_text:
            show_warning(self, "Validation Error", "Kilometers is required.")
            self.kilometers_input.setFocus()
            return

        kilometers_value = self.parse_kilometers(kilometers_text)
        if kilometers_value < 0:
            show_warning(self, "Validation Error", "Kilometers must be a positive number.")
            self.kilometers_input.setFocus()
            return

        self.accept()

    def get_data(self):
        """Get the form data."""
        return {
            "client_id": self.client_combo.currentData(),
            "plate_number": self.plate_input.text().strip().upper(),
            "vin": self.vin_input.text().strip().upper(),
            "model": self.model_input.text().strip(),
            "kilometers": self.parse_kilometers(self.kilometers_input.text()),
        }


class CarsPage(QWidget):
    """Cars page content."""

    def __init__(self):
        super().__init__()
        self.all_cars = []  # Store all cars for filtering
        self.setup_ui()
        self.load_data()

    def showEvent(self, event):
        """Called when the page is shown. Reload data to reflect any changes."""
        super().showEvent(event)
        self.load_data()
        if hasattr(self, "search_input"):
            self.filter_cars(self.search_input.text())

    def setup_ui(self):
        """Setup the cars UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("🚗 Cars")
        title.setStyleSheet(theme.page_title())
        header_layout.addWidget(title)

        layout.addLayout(header_layout)

        # Toolbar: Search and Action buttons
        toolbar_layout = QHBoxLayout()

        # Search bar
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search cars by plate, VIN, model or client...")
        self.search_input.setStyleSheet(theme.search_input())
        self.search_input.textChanged.connect(self.filter_cars)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addSpacing(20)

        # Action buttons
        add_btn = QPushButton("➕ Add Car")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_car)
        toolbar_layout.addWidget(add_btn)

        layout.addLayout(toolbar_layout)

        # Cars table
        self.cars_table = QTableWidget()
        self.cars_table.setStyleSheet(theme.table())
        self.cars_table.setAlternatingRowColors(True)
        self.cars_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cars_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cars_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cars_table.verticalHeader().setVisible(False)
        self.cars_table.verticalHeader().setDefaultSectionSize(50)
        self.cars_table.setColumnCount(7)
        self.cars_table.setHorizontalHeaderLabels(
            ["ID", "Client", "Plate Number", "VIN", "Model", "Kilometers", "Actions"]
        )
        self.cars_table.doubleClicked.connect(self.edit_car)

        layout.addWidget(self.cars_table)

    def load_data(self):
        """Load cars data from the database."""
        self.all_cars = get_all_cars()
        self.display_cars(self.all_cars)

    def filter_cars(self, search_text: str):
        """Filter cars based on search text."""
        search_text = search_text.lower().strip()

        if not search_text:
            filtered = self.all_cars
        else:
            filtered = [
                car
                for car in self.all_cars
                if search_text in car["plate_number"].lower()
                or search_text in car["vin"].lower()
                or search_text in car["model"].lower()
                or search_text in (car.get("client_name") or "").lower()
            ]

        self.display_cars(filtered)

    def display_cars(self, cars: list):
        """Display cars in the table."""
        # Populate table
        self.cars_table.setRowCount(len(cars))

        for row, car in enumerate(cars):
            id_item = QTableWidgetItem(str(car["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, car["id"])  # Store ID for reference
            self.cars_table.setItem(row, 0, id_item)

            self.cars_table.setItem(row, 1, QTableWidgetItem(car.get("client_name", "")))
            self.cars_table.setItem(row, 2, QTableWidgetItem(car["plate_number"]))
            self.cars_table.setItem(row, 3, QTableWidgetItem(car["vin"]))
            self.cars_table.setItem(row, 4, QTableWidgetItem(car["model"]))

            km_item = QTableWidgetItem(f"{car.get('kilometers', 0):,} km")
            km_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cars_table.setItem(row, 5, km_item)

            # Actions column with Edit and Delete buttons
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, c=car: self.edit_car_by_id(c["id"]))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, c=car: self.delete_car_by_id(c["id"]))
            actions_layout.addWidget(delete_btn)

            self.cars_table.setCellWidget(row, 6, actions_widget)

        # Set column widths
        header = self.cars_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.cars_table.setColumnWidth(6, 100)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

    def get_selected_car(self):
        """Get the currently selected car."""
        selected_rows = self.cars_table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        car_id = self.cars_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        # Find car in all_cars list
        for car in self.all_cars:
            if car["id"] == car_id:
                return car
        return None

    def add_car(self):
        """Open dialog to add a new car."""
        dialog = CarDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                add_car(
                    data["client_id"],
                    data["plate_number"],
                    data["vin"],
                    data["model"],
                    data["kilometers"],
                )
                self.load_data()
                self.search_input.clear()
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    show_warning(self, "Error", "A car with this VIN already exists.")
                else:
                    show_critical(self, "Error", f"Failed to add car: {str(e)}")

    def edit_car(self):
        """Open dialog to edit the selected car."""
        car = self.get_selected_car()
        if not car:
            show_warning(self, "No Selection", "Please select a car to edit.")
            return

        dialog = CarDialog(self, car)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                update_car(
                    car["id"],
                    data["client_id"],
                    data["plate_number"],
                    data["vin"],
                    data["model"],
                    data["kilometers"],
                )
                self.load_data()
                self.filter_cars(self.search_input.text())
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    show_warning(self, "Error", "A car with this VIN already exists.")
                else:
                    show_critical(self, "Error", f"Failed to update car: {str(e)}")

    def delete_car(self):
        """Delete the selected car."""
        car = self.get_selected_car()
        if not car:
            show_warning(self, "No Selection", "Please select a car to delete.")
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete {car['model']} ({car['plate_number']})?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        msg_box.setStyleSheet(theme.message_box_confirm())

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            delete_car(car["id"])
            self.load_data()
            self.filter_cars(self.search_input.text())

    def edit_car_by_id(self, car_id: int):
        """Edit a car by ID (used by row action buttons)."""
        # Find the car in all_cars
        car = next((c for c in self.all_cars if c["id"] == car_id), None)
        if not car:
            return

        dialog = CarDialog(self, car)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                update_car(
                    car["id"],
                    data["client_id"],
                    data["plate_number"],
                    data["vin"],
                    data["model"],
                    data["kilometers"],
                )
                self.load_data()
                self.filter_cars(self.search_input.text())
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    show_warning(self, "Error", "A car with this VIN already exists.")
                else:
                    show_critical(self, "Error", f"Failed to update car: {str(e)}")

    def delete_car_by_id(self, car_id: int):
        """Delete a car by ID (used by row action buttons)."""
        # Find the car in all_cars
        car = next((c for c in self.all_cars if c["id"] == car_id), None)
        if not car:
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete {car['model']} ({car['plate_number']})?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        msg_box.setStyleSheet(theme.message_box_confirm())

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            delete_car(car_id)
            self.load_data()
            self.filter_cars(self.search_input.text())
