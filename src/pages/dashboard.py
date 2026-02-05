"""Dashboard page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt

from src.database.models import get_clients_count


class StatCard(QFrame):
    """A card widget displaying a single statistic."""
    
    def __init__(self, title: str, value: str, color: str = "#3498db"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 4px solid {color};
            }}
        """)
        self.setMinimumSize(150, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        
        layout.addWidget(value_label)
        layout.addWidget(title_label)


class DashboardPage(QWidget):
    """Dashboard page content."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("📊 Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        # Stats cards container
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(15)
        layout.addLayout(self.stats_layout)
        
        # Welcome message
        welcome = QLabel(
            "Welcome to Neloaica!\n\n"
            "Use the sidebar to navigate between pages.\n"
            "• View and manage your clients in the Clients page\n"
            "• Configure application settings in the Settings page"
        )
        welcome.setStyleSheet("""
            font-size: 14px; 
            color: #34495e; 
            background-color: white;
            padding: 20px;
            border-radius: 8px;
        """)
        welcome.setWordWrap(True)
        layout.addWidget(welcome)
        
        layout.addStretch()
    
    def load_data(self):
        """Load data from the database."""
        # Clear existing stats
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add stat cards
        clients_count = get_clients_count()
        
        cards = [
            ("Total Clients", str(clients_count), "#3498db"),
        ]
        
        for title, value, color in cards:
            card = StatCard(title, value, color)
            self.stats_layout.addWidget(card)
        
        self.stats_layout.addStretch()
