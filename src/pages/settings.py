"""Settings page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox,
    QFormLayout, QDoubleSpinBox, QPushButton, QMessageBox
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
        
    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet(self.theme.page_title())
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        
        # Settings Group
        settings_group = QGroupBox("Application Settings")
        settings_group.setStyleSheet(self.theme.groupbox())
        settings_layout = QFormLayout()
        settings_layout.setSpacing(15)
        
        # TVA (VAT) field
        self.tva_input = QDoubleSpinBox()
        self.tva_input.setStyleSheet(self.theme.line_edit())
        self.tva_input.setRange(0.0, 100.0)
        self.tva_input.setDecimals(2)
        self.tva_input.setSuffix(" %")
        self.tva_input.setSingleStep(0.1)
        self.tva_input.setMinimumWidth(200)
        
        settings_layout.addRow("TVA (VAT):", self.tva_input)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Save button
        self.save_button = QPushButton("💾 Save Settings")
        self.save_button.setStyleSheet(self.theme.button("success"))
        self.save_button.setMinimumHeight(40)
        self.save_button.setMaximumWidth(200)
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)
        
        layout.addStretch()
    
    def load_settings(self):
        """Load settings from database."""
        tva = get_tva()
        self.tva_input.setValue(tva)
    
    def save_settings(self):
        """Save settings to database."""
        tva_value = self.tva_input.value()
        update_tva(tva_value)
        
        # Show success message
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Settings Saved")
        msg.setText("Settings have been saved successfully!")
        msg.setStyleSheet(self.theme.message_box_confirm())
        msg.exec()

