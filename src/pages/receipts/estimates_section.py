"""Estimates section - Estimated cost and final date for the receipt."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QCalendarWidget,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtGui import QTextCharFormat, QColor

from src.styles import theme


class EstimatesSectionWidget(QWidget):
    """Widget for estimates section."""

    estimates_changed = Signal(float, str)

    def __init__(self, title="Estimates"):
        super().__init__()
        self.title = title
        self._cost_updating = False
        self._selected_date = QDate.currentDate()
        self.setup_ui()
        self.emit_estimates_changed()

    def setup_ui(self):
        """Setup the estimates UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        estimates_group = QGroupBox(self.title)
        estimates_group.setStyleSheet(theme.groupbox() + theme.form_label())

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Estimate cost input
        self.estimate_cost_input = QLineEdit()
        self.estimate_cost_input.setPlaceholderText("e.g. 1 500.00 Lei")
        self.estimate_cost_input.setStyleSheet(theme.line_edit())
        self.estimate_cost_input.setMaximumWidth(200)
        self.estimate_cost_input.textChanged.connect(self.on_cost_text_changed)
        form_layout.addRow("Estimate Cost:", self.estimate_cost_input)

        # Estimated final date picker, same style as receipt info
        self.date_display = QLineEdit()
        self.date_display.setReadOnly(True)
        self.date_display.setText(self._selected_date.toString("dd.MM.yyyy"))
        self.date_display.setStyleSheet(theme.line_edit())
        self.date_display.setMaximumWidth(200)

        self.date_button = QPushButton("📅", self.date_display)
        self.date_button.setFixedSize(28, 28)
        self.date_button.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 16px; } "
            "QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; }"
        )
        self.date_button.setToolTip("Pick estimated final date")
        self.date_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.date_button.clicked.connect(self.show_calendar)

        # Position button inside the input on the right side
        self.date_display.setTextMargins(0, 0, 30, 0)

        form_layout.addRow("Estimated Final Date:", self.date_display)

        estimates_group.setLayout(form_layout)
        layout.addWidget(estimates_group)

    def resizeEvent(self, event):
        """Reposition the calendar button inside the date input."""
        super().resizeEvent(event)
        if hasattr(self, "date_button") and hasattr(self, "date_display"):
            btn_x = self.date_display.width() - self.date_button.width() - 5
            btn_y = (self.date_display.height() - self.date_button.height()) // 2
            self.date_button.move(btn_x, btn_y)

    def showEvent(self, event):
        """Reposition calendar button when shown."""
        super().showEvent(event)
        if hasattr(self, "date_button") and hasattr(self, "date_display"):
            btn_x = self.date_display.width() - self.date_button.width() - 5
            btn_y = (self.date_display.height() - self.date_button.height()) // 2
            self.date_button.move(btn_x, btn_y)

    def on_cost_text_changed(self, text):
        """Format cost input with thousand separators, allowing decimals."""
        if self._cost_updating:
            return
        self._cost_updating = True

        cursor_pos = self.estimate_cost_input.cursorPosition()
        old_len = len(text)

        parts = text.split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else None

        digits = "".join(c for c in integer_part if c.isdigit())

        if digits:
            formatted = ""
            for i, d in enumerate(reversed(digits)):
                if i > 0 and i % 3 == 0:
                    formatted = " " + formatted
                formatted = d + formatted
        else:
            formatted = ""

        if decimal_part is not None:
            dec_digits = "".join(c for c in decimal_part if c.isdigit())[:2]
            formatted = formatted + "." + dec_digits

        new_len = len(formatted)
        new_cursor = cursor_pos + (new_len - old_len)
        new_cursor = max(0, min(new_cursor, new_len))

        self.estimate_cost_input.setText(formatted)
        self.estimate_cost_input.setCursorPosition(new_cursor)

        self._cost_updating = False
        self.emit_estimates_changed()

    def get_estimate_cost(self) -> float:
        """Get estimate cost from input."""
        text = self.estimate_cost_input.text().replace(" ", "").strip()
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0

    def get_estimated_final_date(self) -> str:
        """Get estimated final date as dd.MM.yyyy string."""
        return self._selected_date.toString("dd.MM.yyyy")

    def emit_estimates_changed(self):
        """Emit estimates data."""
        self.estimates_changed.emit(self.get_estimate_cost(), self.get_estimated_final_date())

    def set_data(self, estimate_cost: float, estimated_final_date: str):
        """Populate with existing estimates data."""
        if estimate_cost > 0:
            int_part = int(estimate_cost)
            dec_part = f"{estimate_cost:.2f}".split('.')[1]
            formatted = ''
            int_str = str(int_part)
            for i, d in enumerate(reversed(int_str)):
                if i > 0 and i % 3 == 0:
                    formatted = ' ' + formatted
                formatted = d + formatted
            self.estimate_cost_input.setText(f"{formatted}.{dec_part}")

        if estimated_final_date:
            parsed = QDate.fromString(estimated_final_date, "dd.MM.yyyy")
            if parsed.isValid():
                self._selected_date = parsed
                self.date_display.setText(estimated_final_date)

        self.emit_estimates_changed()

    def show_calendar(self):
        """Show a calendar popup to pick estimated final date."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Estimated Final Date")
        dialog.setMinimumSize(350, 300)
        dialog.setStyleSheet(theme.calendar_dialog())

        layout = QVBoxLayout(dialog)

        calendar = QCalendarWidget()
        calendar.setSelectedDate(self._selected_date)
        calendar.setGridVisible(True)
        calendar.setStyleSheet(theme.calendar())
        calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        sunday_format = QTextCharFormat()
        sunday_format.setForeground(QColor("red"))
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, sunday_format)

        other_month_format = QTextCharFormat()
        other_month_format.setForeground(QColor("#c8c8c8"))
        other_month_format.setBackground(QColor("#f5f5f5"))

        _page_changed = [False]
        _restore_page = [calendar.yearShown(), calendar.monthShown()]

        def update_other_month_dates():
            current_month = calendar.monthShown()
            current_year = calendar.yearShown()
            first_day = QDate(current_year, current_month, 1)
            for i in range(-7, 49):
                d = first_day.addDays(i)
                if d.month() != current_month or d.year() != current_year:
                    calendar.setDateTextFormat(d, other_month_format)
                else:
                    calendar.setDateTextFormat(d, QTextCharFormat())

        def on_page_changed(_year, _month):
            _page_changed[0] = True
            update_other_month_dates()

            def after_event_loop():
                if _page_changed[0]:
                    _restore_page[0] = calendar.yearShown()
                    _restore_page[1] = calendar.monthShown()
                    _page_changed[0] = False

            QTimer.singleShot(0, after_event_loop)

        def on_date_clicked(date):
            if _page_changed[0]:
                _page_changed[0] = False
                calendar.setCurrentPage(_restore_page[0], _restore_page[1])
                return

            self._selected_date = date
            self.date_display.setText(date.toString("dd.MM.yyyy"))
            self.emit_estimates_changed()
            dialog.accept()

        update_other_month_dates()
        calendar.currentPageChanged.connect(on_page_changed)
        calendar.clicked.connect(on_date_clicked)

        layout.addWidget(calendar)
        dialog.exec()
