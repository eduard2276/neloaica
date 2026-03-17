"""Receipt information section - Customer and car data."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QCalendarWidget,
)
from PySide6.QtCore import Qt, Signal, QDate

from src.database.models import (
    get_all_clients,
    get_all_cars,
    get_all_employees,
)
from src.widgets import NoScrollComboBox
from src.styles import theme


class ReceiptInfoWidget(QWidget):
    """Widget for receipt information (client and car data)."""
    
    # Signals to notify parent when data changes
    data_changed = Signal(dict)  # Emits updated receipt info data
    
    def __init__(self):
        super().__init__()
        self.all_clients = []
        self.all_cars = []
        self.all_employees = []
        self.saved_client_id = None
        self.saved_car_id = None
        self.saved_kilometers = ""
        self.saved_executant_id = None
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the receipt information UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Form container with combined styling for group and labels
        form_group = QGroupBox("Receipt Information")
        form_group.setStyleSheet(theme.groupbox() + theme.form_label())
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Client dropdown
        self.client_combo = NoScrollComboBox()
        self.client_combo.setPlaceholderText("Select a client")
        self.client_combo.currentIndexChanged.connect(self.on_client_changed)
        self.client_combo.setStyleSheet(theme.combobox())
        form_layout.addRow("Client:", self.client_combo)
        
        # Car dropdown
        self.car_combo = NoScrollComboBox()
        self.car_combo.setPlaceholderText("Select a car")
        self.car_combo.setEnabled(False)
        self.car_combo.currentIndexChanged.connect(self.on_car_changed)
        self.car_combo.setStyleSheet(theme.combobox())
        form_layout.addRow("Car:", self.car_combo)
        
        # Car details (read-only except kilometers)
        self.plate_input = QLineEdit()
        self.plate_input.setReadOnly(True)
        self.plate_input.setPlaceholderText("Plate number")
        
        self.vin_input = QLineEdit()
        self.vin_input.setReadOnly(True)
        self.vin_input.setPlaceholderText("VIN")
        
        self.model_input = QLineEdit()
        self.model_input.setReadOnly(True)
        self.model_input.setPlaceholderText("Model")
        
        self.km_input = QLineEdit()
        self.km_input.setPlaceholderText("e.g. 120 000")
        self.km_input.textChanged.connect(self.on_km_text_changed)
        self._km_updating = False  # Flag to prevent recursive updates
        
        # Styling for inputs - read-only fields get grey background
        readonly_style = theme.line_edit_readonly()
        editable_style = theme.line_edit()
        
        self.plate_input.setStyleSheet(readonly_style)
        self.vin_input.setStyleSheet(readonly_style)
        self.model_input.setStyleSheet(readonly_style)
        self.km_input.setStyleSheet(editable_style)
        
        # Date picker (QLineEdit with overlaid calendar button)
        self.date_display = QLineEdit()
        self.date_display.setReadOnly(True)
        self.date_display.setText(QDate.currentDate().toString("dd.MM.yyyy"))
        self.date_display.setStyleSheet(editable_style)
        self.date_display.setMaximumWidth(200)
        
        self.date_button = QPushButton("📅", self.date_display)
        self.date_button.setFixedSize(28, 28)
        self.date_button.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 16px; } QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; }")
        self.date_button.setToolTip("Pick a date")
        self.date_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.date_button.clicked.connect(self.show_calendar)
        
        # Position button inside the input on the right side
        self.date_display.setTextMargins(0, 0, 30, 0)
        
        self._selected_date = QDate.currentDate()
        
        form_layout.addRow("Plate Number:", self.plate_input)
        form_layout.addRow("VIN:", self.vin_input)
        form_layout.addRow("Model:", self.model_input)
        # Executant dropdown
        self.executant_combo = NoScrollComboBox()
        self.executant_combo.setPlaceholderText("Select an executant")
        self.executant_combo.currentIndexChanged.connect(self.on_executant_changed)
        self.executant_combo.setStyleSheet(theme.combobox())

        form_layout.addRow("Kilometers:", self.km_input)
        form_layout.addRow("Executant:", self.executant_combo)
        form_layout.addRow("Date:", self.date_display)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
    
    def load_data(self, restore_state=False):
        """Load clients and cars from database."""
        if restore_state:
            self.save_form_state()
        
        self.all_clients = get_all_clients()
        self.all_cars = get_all_cars()
        self.all_employees = get_all_employees()
        
        # Sort clients alphabetically by first name, then last name
        self.all_clients.sort(key=lambda c: (c['first_name'].lower(), c['last_name'].lower()))
        
        # Populate executant dropdown
        self.executant_combo.blockSignals(True)
        self.executant_combo.clear()
        self.executant_combo.addItem("Select an executant", None)
        for emp in self.all_employees:
            display_text = f"{emp['first_name']} {emp['last_name']}"
            self.executant_combo.addItem(display_text, emp['id'])
        if restore_state and self.saved_executant_id is not None:
            for i in range(self.executant_combo.count()):
                if self.executant_combo.itemData(i) == self.saved_executant_id:
                    self.executant_combo.setCurrentIndex(i)
                    break
        self.executant_combo.blockSignals(False)
        
        self.client_combo.blockSignals(True)
        
        # Populate client dropdown
        self.client_combo.clear()
        self.client_combo.addItem("Select a client", None)
        for client in self.all_clients:
            display_text = f"{client['first_name']} {client['last_name']}"
            self.client_combo.addItem(display_text, client['id'])
        
        if restore_state and self.saved_client_id is not None:
            self.restore_form_state()
        else:
            self.car_combo.clear()
            self.car_combo.addItem("Select a car", None)
            self.car_combo.setEnabled(False)
            self.clear_car_details()
        
        self.client_combo.blockSignals(False)
        
        if not restore_state:
            self.emit_data_changed()
    
    def save_form_state(self):
        """Save current form state."""
        self.saved_client_id = self.client_combo.currentData()
        self.saved_car_id = self.car_combo.currentData()
        self.saved_kilometers = self.km_input.text()
        self.saved_executant_id = self.executant_combo.currentData()
    
    def restore_form_state(self):
        """Restore previously saved form state."""
        if self.saved_client_id is not None:
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == self.saved_client_id:
                    self.client_combo.setCurrentIndex(i)
                    break
        
        if self.saved_car_id is not None:
            for i in range(self.car_combo.count()):
                if self.car_combo.itemData(i) == self.saved_car_id:
                    self.car_combo.setCurrentIndex(i)
                    break
        
        if self.saved_kilometers and self.km_input.text() != self.saved_kilometers:
            self.km_input.setText(self.saved_kilometers)
    
    def on_client_changed(self, index):
        """Handle client selection change."""
        self.car_combo.clear()
        self.car_combo.addItem("Select a car", None)
        
        if index <= 0:
            self.car_combo.setEnabled(False)
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        client_id = self.client_combo.currentData()
        if client_id is None:
            self.car_combo.setEnabled(False)
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        # Filter cars for selected client
        client_cars = [car for car in self.all_cars if car['client_id'] == client_id]
        
        if client_cars:
            self.car_combo.setEnabled(True)
            for car in client_cars:
                display_text = f"{car['model']} ({car['vin']})"
                self.car_combo.addItem(display_text, car['id'])
        else:
            self.car_combo.setEnabled(False)
        
        self.clear_car_details()
        self.emit_data_changed()
    
    def on_car_changed(self, index):
        """Handle car selection change."""
        if index <= 0:
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        car_id = self.car_combo.currentData()
        if car_id is None:
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        # Find the selected car
        selected_car = next((car for car in self.all_cars if car['id'] == car_id), None)
        
        if selected_car:
            self.plate_input.setText(selected_car['plate_number'])
            self.vin_input.setText(selected_car['vin'])
            self.model_input.setText(selected_car['model'])
            # Format kilometers with thousand separators
            km_value = selected_car.get('kilometers', 0)
            self.km_input.setText(self.format_kilometers(km_value))
        
        self.emit_data_changed()
    
    def on_executant_changed(self, index):
        """Handle executant selection change."""
        self.emit_data_changed()

    def on_km_text_changed(self, text):
        """Handle kilometers input change with formatting."""
        if self._km_updating:
            return
        
        self._km_updating = True
        
        # Get cursor position before formatting
        cursor_pos = self.km_input.cursorPosition()
        old_text = text
        
        # Remove all non-digit characters
        digits_only = ''.join(c for c in text if c.isdigit())
        
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
        self.km_input.setText(formatted)
        self.km_input.setCursorPosition(new_cursor_pos)
        
        self._km_updating = False
        self.emit_data_changed()
    
    def format_kilometers(self, value) -> str:
        """Format a number with thousand separators (spaces)."""
        try:
            num = int(value)
            # Format with spaces as thousand separators
            formatted = f"{num:,}".replace(",", " ")
            return formatted
        except (ValueError, TypeError):
            return str(value) if value else ""
    
    def parse_kilometers(self, text: str) -> str:
        """Parse formatted kilometers text to raw number string."""
        # Remove all spaces and non-digit characters
        return ''.join(c for c in text if c.isdigit())
    
    def resizeEvent(self, event):
        """Reposition the calendar button inside the date input."""
        super().resizeEvent(event)
        if hasattr(self, 'date_button') and hasattr(self, 'date_display'):
            btn_x = self.date_display.width() - self.date_button.width() - 5
            btn_y = (self.date_display.height() - self.date_button.height()) // 2
            self.date_button.move(btn_x, btn_y)
    
    def showEvent(self, event):
        """Reposition calendar button when shown."""
        super().showEvent(event)
        if hasattr(self, 'date_button') and hasattr(self, 'date_display'):
            btn_x = self.date_display.width() - self.date_button.width() - 5
            btn_y = (self.date_display.height() - self.date_button.height()) // 2
            self.date_button.move(btn_x, btn_y)
    
    def show_calendar(self):
        """Show a calendar popup to pick a date."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout as QVBox
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QTextCharFormat, QColor
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date")
        dialog.setMinimumSize(350, 300)
        dialog.setStyleSheet(theme.calendar_dialog())
        
        layout = QVBox(dialog)
        
        calendar = QCalendarWidget()
        calendar.setSelectedDate(self._selected_date)
        calendar.setGridVisible(True)
        calendar.setStyleSheet(theme.calendar())
        # Hide week numbers
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        
        # Keep Sundays red for current-month dates (per-date format overrides this
        # for other-month Sundays)
        sunday_format = QTextCharFormat()
        sunday_format.setForeground(QColor("red"))
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, sunday_format)
        
        # Grey styling for dates outside the displayed month
        other_month_format = QTextCharFormat()
        other_month_format.setForeground(QColor("#c8c8c8"))
        other_month_format.setBackground(QColor("#f5f5f5"))
        
        # State for tracking page changes vs date clicks.
        # When a user clicks a date from another month, Qt fires
        # currentPageChanged BEFORE clicked. We use this flag to detect
        # that scenario and revert the navigation.
        _page_changed = [False]
        _restore_page = [calendar.yearShown(), calendar.monthShown()]
        
        def update_other_month_dates():
            """Apply grey format to dates not belonging to the displayed month."""
            current_month = calendar.monthShown()
            current_year = calendar.yearShown()
            first_day = QDate(current_year, current_month, 1)
            # Iterate from 7 days before the 1st through 49 days after to
            # guarantee all 42 visible grid cells are covered regardless of
            # which day the week starts on.
            for i in range(-7, 49):
                d = first_day.addDays(i)
                if d.month() != current_month or d.year() != current_year:
                    calendar.setDateTextFormat(d, other_month_format)
                else:
                    # Reset to default so weekday formats (e.g. red Sunday) apply
                    calendar.setDateTextFormat(d, QTextCharFormat())
        
        def on_page_changed(year, month):
            """Handle month/year page navigation."""
            _page_changed[0] = True
            update_other_month_dates()
            
            def after_event_loop():
                """Runs on the next event-loop iteration.
                
                If the flag is still set, no clicked() signal followed the
                page change, meaning the user used the navigation buttons.
                Update the restore point so the next other-month click can
                revert to this page.
                """
                if _page_changed[0]:
                    _restore_page[0] = calendar.yearShown()
                    _restore_page[1] = calendar.monthShown()
                    _page_changed[0] = False
            
            QTimer.singleShot(0, after_event_loop)
        
        def on_date_clicked(date):
            """Handle date selection, rejecting other-month dates."""
            if _page_changed[0]:
                # A page change fired right before this click, which means
                # the user clicked a date belonging to the previous/next
                # month. Revert to the page they were viewing.
                _page_changed[0] = False
                calendar.setCurrentPage(_restore_page[0], _restore_page[1])
                return
            
            # Valid same-month date — accept it
            self._selected_date = date
            self.date_display.setText(date.toString("dd.MM.yyyy"))
            self.emit_data_changed()
            dialog.accept()
        
        update_other_month_dates()
        calendar.currentPageChanged.connect(on_page_changed)
        calendar.clicked.connect(on_date_clicked)
        
        layout.addWidget(calendar)
        dialog.exec()
    
    def clear_car_details(self):
        """Clear all car detail inputs."""
        self.plate_input.clear()
        self.vin_input.clear()
        self.model_input.clear()
        self.km_input.clear()
    
    def get_data(self) -> dict:
        """Get current form data."""
        # Get client name and address
        client_id = self.client_combo.currentData()
        client_name = ""
        client_address = ""
        
        if client_id is not None:
            client = next((c for c in self.all_clients if c['id'] == client_id), None)
            if client:
                client_name = f"{client['first_name']} {client['last_name']}"
                client_address = client.get('address', '')
        
        executant_name = ""
        executant_id = self.executant_combo.currentData()
        if executant_id is not None:
            emp = next((e for e in self.all_employees if e['id'] == executant_id), None)
            if emp:
                executant_name = f"{emp['first_name']} {emp['last_name']}"

        return {
            'client_id': client_id,
            'client_name': client_name,
            'client_address': client_address,
            'car_id': self.car_combo.currentData(),
            'plate_number': self.plate_input.text(),
            'vin': self.vin_input.text(),
            'model': self.model_input.text(),
            'kilometers': self.parse_kilometers(self.km_input.text()),
            'executant_name': executant_name,
            'date': self._selected_date.toString("dd.MM.yyyy"),
        }
    
    def set_data(self, data: dict):
        """Populate the form with existing receipt data."""
        self.load_data(restore_state=False)

        client_id = data.get('client_id')
        if client_id is not None:
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == client_id:
                    self.client_combo.setCurrentIndex(i)
                    break

        car_id = data.get('car_id')
        if car_id is not None:
            for i in range(self.car_combo.count()):
                if self.car_combo.itemData(i) == car_id:
                    self.car_combo.setCurrentIndex(i)
                    break

        km = data.get('kilometers', '')
        if km:
            self.km_input.setText(self.format_kilometers(int(km)) if km.isdigit() else km)

        executant_name = data.get('executant_name', '')
        if executant_name:
            for i in range(self.executant_combo.count()):
                if self.executant_combo.itemText(i) == executant_name:
                    self.executant_combo.setCurrentIndex(i)
                    break

        date_str = data.get('date', '')
        if date_str:
            from PySide6.QtCore import QDate
            parsed = QDate.fromString(date_str, "dd.MM.yyyy")
            if parsed.isValid():
                self._selected_date = parsed
                self.date_display.setText(date_str)

    def emit_data_changed(self):
        """Emit signal with current data."""
        self.data_changed.emit(self.get_data())
