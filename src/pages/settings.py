"""Settings page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFormLayout, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

from src.database.models import get_tva, update_tva
from src.styles.theme_manager import ThemeManager


class SettingsPage(QWidget):
    """Settings page content."""
    
    def __init__(self):
        super().__init__()
        self.theme = ThemeManager()
        self.init_ui()
        self.load_settings()
        self.set_editing(False)
        
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Settings")
        title.setStyleSheet(self.theme.page_title())
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        
        # TVA Settings Group - styled like Receipt Information
        tva_group = QGroupBox("TVA (VAT) Settings")
        tva_group.setStyleSheet(self.theme.groupbox() + self.theme.form_label())
        
        tva_layout = QFormLayout()
        tva_layout.setSpacing(15)
        tva_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # TVA input as QLineEdit with placeholder
        self.tva_input = QLineEdit()
        self.tva_input.setPlaceholderText("e.g. 21.00")
        self.tva_input.setStyleSheet(self.theme.line_edit())
        self.tva_input.setMaximumWidth(200)
        self._tva_updating = False
        self.tva_input.textChanged.connect(self.on_tva_text_changed)
        
        tva_layout.addRow("TVA (%):", self.tva_input)
        
        tva_group.setLayout(tva_layout)
        layout.addWidget(tva_group)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Edit button - visible when not editing
        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(self.theme.button("success"))
        self.edit_button.setMinimumHeight(40)
        self.edit_button.setMaximumWidth(200)
        self.edit_button.clicked.connect(self.start_editing)
        buttons_layout.addWidget(self.edit_button)
        
        # Save button - visible when editing
        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet(self.theme.button("success"))
        self.save_button.setMinimumHeight(40)
        self.save_button.setMaximumWidth(200)
        self.save_button.clicked.connect(self.save_settings)
        buttons_layout.addWidget(self.save_button)
        
        # Cancel button - visible when editing
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(self.theme.button("cancel"))
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setMaximumWidth(200)
        self.cancel_button.clicked.connect(self.cancel_editing)
        buttons_layout.addWidget(self.cancel_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
    
    def showEvent(self, event):
        """Reload settings when the page is shown."""
        super().showEvent(event)
        self.load_settings()
        self.set_editing(False)
    
    def set_editing(self, editing: bool):
        """Toggle between editing and read-only mode."""
        self.tva_input.setReadOnly(not editing)
        
        if editing:
            self.tva_input.setStyleSheet(self.theme.line_edit())
        else:
            self.tva_input.setStyleSheet(self.theme.line_edit_readonly())
        
        # Show/hide buttons
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)
    
    def start_editing(self):
        """Enter editing mode."""
        self.set_editing(True)
        self.tva_input.setFocus()
    
    def cancel_editing(self):
        """Cancel editing and restore values from database."""
        self.load_settings()
        self.set_editing(False)
    
    def on_tva_text_changed(self, text):
        """Validate TVA input to only allow decimal numbers."""
        if self._tva_updating:
            return
        self._tva_updating = True
        
        cursor_pos = self.tva_input.cursorPosition()
        
        # Allow only digits and one decimal point
        parts = text.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else None
        
        # Keep only digits
        digits = ''.join(c for c in integer_part if c.isdigit())
        
        formatted = digits
        
        if decimal_part is not None:
            dec_digits = ''.join(c for c in decimal_part if c.isdigit())[:2]
            formatted = formatted + '.' + dec_digits
        
        self.tva_input.setText(formatted)
        self.tva_input.setCursorPosition(min(cursor_pos, len(formatted)))
        
        self._tva_updating = False
    
    def load_settings(self):
        """Load settings from database."""
        tva = get_tva()
        self._tva_updating = True
        if tva == int(tva):
            self.tva_input.setText(str(int(tva)))
        else:
            self.tva_input.setText(f"{tva:.2f}")
        self._tva_updating = False
    
    def save_settings(self):
        """Save settings to database."""
        text = self.tva_input.text().strip()
        try:
            tva_value = float(text) if text else 0.0
        except ValueError:
            tva_value = 0.0
        
        if tva_value < 0 or tva_value > 100:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Validation Error")
            msg.setText("TVA must be between 0 and 100.")
            msg.setStyleSheet(self.theme.message_box_confirm())
            msg.exec()
            return
        
        update_tva(tva_value)
        self.set_editing(False)
        
        # Show success message
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Settings Saved")
        msg.setText("Settings have been saved successfully!")
        msg.setStyleSheet(self.theme.message_box_confirm())
        msg.exec()
