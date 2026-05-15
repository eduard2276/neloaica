"""
Neloaica - PySide6 Desktop Application
Main entry point for the application.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.database import init_database
from src.pages import (
    CarsPage,
    ClientsPage,
    DefectsPage,
    EmployeesPage,
    LaborPage,
    PartsPage,
    ReceiptsPage,
    SettingsPage,
)
from src.services import create_backup, should_create_daily_backup
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
        self.nav_list.addItem(QListWidgetItem("🧑‍💼  Employees"))
        self.nav_list.addItem(QListWidgetItem("🧾  Receipts"))
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
        self.pages.addWidget(EmployeesPage())
        self.pages.addWidget(ReceiptsPage())
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
    app.setApplicationVersion(__version__)

    # Initialize database (create tables if they don't exist)
    init_database()

    # Create automatic backups
    # 1. Backup on startup
    print("[INFO] Creating startup backup...")
    create_backup("startup")

    # 2. Daily automatic backup (if not already created today)
    if should_create_daily_backup():
        print("[INFO] Creating daily automatic backup...")
        create_backup("auto")
    else:
        print("[INFO] Daily backup already exists for today.")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
