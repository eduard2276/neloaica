"""Settings page."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class SettingsPage(QWidget):
    """Settings page content."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        content = QLabel(
            "Welcome to the Settings page!\n\n"
            "This is another mock page for the navigation demo.\n"
            "You can add configuration options and preferences here.\n\n"
            "• Application preferences\n"
            "• User profile settings\n"
            "• Theme customization\n"
            "• Notification options"
        )
        content.setStyleSheet("font-size: 14px; color: #34495e; line-height: 1.6;")
        content.setWordWrap(True)
        content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(content)
        layout.addStretch()
