"""
Neloaica - PySide6 Desktop Application
Main entry point for the application.
"""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
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
    get_logo_ico_path,
    get_logo_png_path,
    migrate_legacy_db,
    migrate_legacy_dir,
)
from src.services import create_backup, setup_logging, should_create_daily_backup
from src.styles import theme

#: Width the sidebar logo pixmap is scaled to. Matches the sidebar
#: minimum width (200 px) minus the 12 px padding declared in
#: ``theme.sidebar_logo()`` on each side.
SIDEBAR_LOGO_WIDTH = 176

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

        title = self._build_title_widget()
        layout.addWidget(title)

        self.nav_list = self._build_nav_list()
        layout.addWidget(self.nav_list)

    def _build_title_widget(self) -> QLabel:
        """Return the sidebar header — logo image when available, text fallback.

        The PNG is the preferred asset because Qt's pixmap scaling
        anti-aliases noticeably better than rasterising the ``.ico``.
        If the asset is missing (e.g. a contributor cloned the repo
        without the ``templates/images/`` folder, or a partial
        install) we fall back to the original text title so the app
        still has *something* in the sidebar header.
        """
        title = QLabel()
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = get_logo_png_path()
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaledToWidth(
                    SIDEBAR_LOGO_WIDTH,
                    Qt.TransformationMode.SmoothTransformation,
                )
                title.setPixmap(scaled)
                title.setStyleSheet(theme.sidebar_logo())
                return title
        # Fallback path — keep the old text title.
        title.setText("Neloaica")
        title.setStyleSheet(theme.sidebar_title())
        return title

    def _build_nav_list(self) -> QListWidget:
        """Build the navigation list with all the page entries."""
        nav_list = QListWidget()
        nav_list.addItem(QListWidgetItem("👥  Clients"))
        nav_list.addItem(QListWidgetItem("🚗  Cars"))
        nav_list.addItem(QListWidgetItem("⚙️  Labor"))
        nav_list.addItem(QListWidgetItem("🔧  Parts"))
        nav_list.addItem(QListWidgetItem("⚠️  Defects"))
        nav_list.addItem(QListWidgetItem("🧑‍💼  Employees"))
        nav_list.addItem(QListWidgetItem("🧾  Receipts"))
        nav_list.addItem(QListWidgetItem("⚙️  Settings"))
        nav_list.setCurrentRow(0)
        nav_list.currentRowChanged.connect(self.on_page_changed)
        return nav_list


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


def _resolve_app_icon() -> QIcon:
    """Resolve the application icon, preferring the multi-resolution ``.ico``.

    Windows uses the icon for the taskbar, alt-tab, title bar and tray.
    The ``.ico`` ships multiple sizes (16/32/48/256) so Qt can pick the
    sharpest one for each surface. If only the PNG is available (e.g.
    a non-Windows install missing the ``.ico``) we fall back to it.
    Returns an empty :class:`QIcon` if neither asset exists — Qt's
    ``setWindowIcon`` is a no-op in that case.
    """
    for candidate in (get_logo_ico_path(), get_logo_png_path()):
        if candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)

    app.setApplicationName("Neloaica")
    app.setOrganizationName("Neloaica Project")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_resolve_app_icon())

    bootstrap()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
