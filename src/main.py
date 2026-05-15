"""
Neloaica - PySide6 Desktop Application
Main entry point for the application.
"""

import logging
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
from src.paths import (
    get_app_dir,
    get_backups_dir,
    get_database_path,
    migrate_legacy_db,
    migrate_legacy_dir,
)
from src.services import create_backup, setup_logging, should_create_daily_backup
from src.styles import theme

logger = logging.getLogger(__name__)


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

        title = QLabel("Neloaica")
        title.setStyleSheet(theme.sidebar_title())
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.addWidget(ClientsPage())
        self.pages.addWidget(CarsPage())
        self.pages.addWidget(LaborPage())
        self.pages.addWidget(PartsPage())
        self.pages.addWidget(DefectsPage())
        self.pages.addWidget(EmployeesPage())
        self.pages.addWidget(ReceiptsPage())
        self.pages.addWidget(SettingsPage())

        self.sidebar = Sidebar(self.change_page)

        content_frame = QFrame()
        content_frame.setStyleSheet(theme.content_area())
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.addWidget(self.pages)

        layout.addWidget(self.sidebar)
        layout.addWidget(content_frame, 1)

    def change_page(self, index):
        """Switch to the selected page."""
        self.pages.setCurrentIndex(index)


def bootstrap() -> None:
    """Run the non-Qt startup sequence: logging, DB migration, schema, backups.

    Split out from :func:`main` so it can be unit-tested without spinning up
    a real ``QApplication``. The order matters:

    1. **Logging first.** Anything that runs after this can call
       ``logger.info(...)`` and have it land in the rotating log file.
    2. **Migrate legacy DB.** Older builds wrote ``neloaica.db`` next to the
       executable. We move it into the user data dir before opening any
       connection so the singleton picks up the migrated file.
    3. **Initialise the schema.** ``init_database`` is idempotent — it only
       creates tables that don't already exist.
    4. **Backups.** A startup snapshot plus a daily one if none exists yet.
    """
    log_file = setup_logging()
    logger.info("Neloaica %s starting up", __version__)
    logger.info("Logs: %s", log_file)

    legacy_db = get_app_dir() / "neloaica.db"
    new_db = get_database_path()
    if legacy_db != new_db and migrate_legacy_db(legacy_db, new_db):
        logger.info("Migrated legacy DB from %s to %s", legacy_db, new_db)

    legacy_backups = get_app_dir() / "backups"
    new_backups = get_backups_dir()
    if legacy_backups != new_backups:
        moved = migrate_legacy_dir(legacy_backups, new_backups)
        if moved:
            logger.info(
                "Migrated %d legacy backup file(s) from %s to %s",
                moved,
                legacy_backups,
                new_backups,
            )

    init_database()

    logger.info("Creating startup backup...")
    create_backup("startup")

    if should_create_daily_backup():
        logger.info("Creating daily automatic backup...")
        create_backup("auto")
    else:
        logger.info("Daily backup already exists for today.")


def main():
    """Application entry point."""
    app = QApplication(sys.argv)

    app.setApplicationName("Neloaica")
    app.setOrganizationName("Neloaica Project")
    app.setApplicationVersion(__version__)

    bootstrap()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
