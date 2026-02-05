"""
Neloaica - PySide6 Desktop Application
Main entry point for the application.
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
)
from PySide6.QtCore import Qt

from src.pages import CarsPage, ClientsPage, DashboardPage, DefectsPage, LaborPage, PartsPage, ReceiptsPage, SettingsPage
from src.database import init_database, populate_mock_data
from src.styles import theme


class Sidebar(QWidget):
    """Sidebar navigation widget."""
    
    def __init__(self, on_page_changed):
        super().__init__()
        self.on_page_changed = on_page_changed
        self.setMinimumWidth(200)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.setStyleSheet(theme.sidebar())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # App title
        title = QLabel("Neloaica")
        title.setStyleSheet(theme.sidebar_title())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.addItem(QListWidgetItem("👥  Clients"))
        self.nav_list.addItem(QListWidgetItem("🚗  Cars"))
        self.nav_list.addItem(QListWidgetItem("⚙️  Labor"))
        self.nav_list.addItem(QListWidgetItem("🔧  Parts"))
        self.nav_list.addItem(QListWidgetItem("⚠️  Defects"))
        self.nav_list.addItem(QListWidgetItem("🧾  Receipts"))
        self.nav_list.addItem(QListWidgetItem("📊  Dashboard"))
        self.nav_list.addItem(QListWidgetItem("⚙️  Settings"))
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self.on_page_changed)
        layout.addWidget(self.nav_list)
        
        


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neloaica")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create stacked widget for pages
        self.pages = QStackedWidget()
        self.pages.addWidget(ClientsPage())
        self.pages.addWidget(CarsPage())
        self.pages.addWidget(LaborPage())
        self.pages.addWidget(PartsPage())
        self.pages.addWidget(DefectsPage())
        self.pages.addWidget(ReceiptsPage())
        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(SettingsPage())
        
        # Create sidebar
        self.sidebar = Sidebar(self.change_page)
        
        # Content area styling
        content_frame = QFrame()
        content_frame.setStyleSheet(theme.content_area())
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.addWidget(self.pages)
        
        # Add widgets to main layout
        layout.addWidget(self.sidebar)
        layout.addWidget(content_frame, 1)
    
    def change_page(self, index):
        """Switch to the selected page."""
        self.pages.setCurrentIndex(index)


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Neloaica")
    app.setOrganizationName("Nokia")
    app.setApplicationVersion("1.0.0")
    
    # Initialize database and populate with mock data
    init_database()
    populate_mock_data()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
