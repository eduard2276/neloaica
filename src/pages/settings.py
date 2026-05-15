"""Settings page."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.database.models import get_receipt_number, get_tva, update_receipt_number, update_tva
from src.services import create_backup
from src.services.updater import (
    UpdateApplyError,
    UpdateInfo,
    UpdateOrchestrator,
    Version,
)
from src.styles.theme_manager import ThemeManager
from src.widgets import UpdateCheckWorker, UpdateProgressDialog

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Settings page content."""

    def __init__(self):
        super().__init__()
        self.theme = ThemeManager()
        # The orchestrator is built lazily so the network is never
        # touched until the user clicks "Verifică actualizări". Tests
        # inject a fake via ``set_update_orchestrator_factory``.
        self._orchestrator_factory = _default_orchestrator_factory
        self._check_worker = None
        self.init_ui()
        self.load_settings()
        self.set_editing(False)

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet(self.theme.page_title())
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        # Settings Group - single group for all settings
        settings_group = QGroupBox("Application Settings")
        settings_group.setStyleSheet(self.theme.groupbox() + self.theme.form_label())

        settings_form = QFormLayout()
        settings_form.setSpacing(15)
        settings_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # TVA input
        self.tva_input = QLineEdit()
        self.tva_input.setPlaceholderText("e.g. 21.00")
        self.tva_input.setStyleSheet(self.theme.line_edit())
        self.tva_input.setMaximumWidth(200)
        self._tva_updating = False
        self.tva_input.textChanged.connect(self.on_tva_text_changed)
        settings_form.addRow("TVA (%):", self.tva_input)

        # Receipt Number input
        self.receipt_number_input = QLineEdit()
        self.receipt_number_input.setPlaceholderText("e.g. 1")
        self.receipt_number_input.setStyleSheet(self.theme.line_edit())
        self.receipt_number_input.setMaximumWidth(200)
        self._receipt_number_updating = False
        self.receipt_number_input.textChanged.connect(self.on_receipt_number_text_changed)
        settings_form.addRow("Receipt Number:", self.receipt_number_input)

        settings_group.setLayout(settings_form)
        layout.addWidget(settings_group)

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

        # Database Backup Section
        backup_group = QGroupBox("Database Backup")
        backup_group.setStyleSheet(self.theme.groupbox())
        backup_layout = QVBoxLayout()
        backup_layout.setSpacing(15)

        backup_info = QLabel("Create a backup of your database to protect your data.")
        backup_info.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        backup_layout.addWidget(backup_info)

        backup_button_layout = QHBoxLayout()
        backup_btn = QPushButton("💾 Create Backup Now")
        backup_btn.setStyleSheet(self.theme.button("primary"))
        backup_btn.setMinimumHeight(40)
        backup_btn.setMaximumWidth(250)
        backup_btn.clicked.connect(self.create_manual_backup)
        backup_button_layout.addWidget(backup_btn)
        backup_button_layout.addStretch()

        backup_layout.addLayout(backup_button_layout)
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        # Updates section -----------------------------------------------
        updates_group = QGroupBox("Actualizări")
        updates_group.setStyleSheet(self.theme.groupbox())
        updates_layout = QVBoxLayout()
        updates_layout.setSpacing(15)

        self.current_version_label = QLabel(f"Versiunea curentă: {__version__}")
        self.current_version_label.setStyleSheet("color: #2c3e50; font-size: 13px;")
        updates_layout.addWidget(self.current_version_label)

        self.update_status_label = QLabel("Apasă butonul pentru a verifica actualizările.")
        self.update_status_label.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        self.update_status_label.setWordWrap(True)
        updates_layout.addWidget(self.update_status_label)

        check_layout = QHBoxLayout()
        self.check_update_button = QPushButton("🔄 Verifică actualizări")
        self.check_update_button.setStyleSheet(self.theme.button("primary"))
        self.check_update_button.setMinimumHeight(40)
        self.check_update_button.setMaximumWidth(250)
        self.check_update_button.clicked.connect(self.on_check_update_clicked)
        check_layout.addWidget(self.check_update_button)
        check_layout.addStretch()
        updates_layout.addLayout(check_layout)

        updates_group.setLayout(updates_layout)
        layout.addWidget(updates_group)

        layout.addStretch()

    def showEvent(self, event):
        """Reload settings when the page is shown."""
        super().showEvent(event)
        self.load_settings()
        self.set_editing(False)

    def set_editing(self, editing: bool):
        """Toggle between editing and read-only mode."""
        self.tva_input.setReadOnly(not editing)
        self.receipt_number_input.setReadOnly(not editing)

        if editing:
            self.tva_input.setStyleSheet(self.theme.line_edit())
            self.receipt_number_input.setStyleSheet(self.theme.line_edit())
        else:
            self.tva_input.setStyleSheet(self.theme.line_edit_readonly())
            self.receipt_number_input.setStyleSheet(self.theme.line_edit_readonly())

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
        parts = text.split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else None

        # Keep only digits
        digits = "".join(c for c in integer_part if c.isdigit())

        formatted = digits

        if decimal_part is not None:
            dec_digits = "".join(c for c in decimal_part if c.isdigit())[:2]
            formatted = formatted + "." + dec_digits

        self.tva_input.setText(formatted)
        self.tva_input.setCursorPosition(min(cursor_pos, len(formatted)))

        self._tva_updating = False

    def on_receipt_number_text_changed(self, text):
        """Validate receipt number input to only allow positive integers."""
        if self._receipt_number_updating:
            return
        self._receipt_number_updating = True

        cursor_pos = self.receipt_number_input.cursorPosition()

        # Keep only digits
        digits = "".join(c for c in text if c.isdigit())

        # Remove leading zeros (but keep at least "0" if that's all there is)
        if len(digits) > 1:
            digits = digits.lstrip("0") or "0"

        self.receipt_number_input.setText(digits)
        self.receipt_number_input.setCursorPosition(min(cursor_pos, len(digits)))

        self._receipt_number_updating = False

    def load_settings(self):
        """Load settings from database."""
        tva = get_tva()
        self._tva_updating = True
        if tva == int(tva):
            self.tva_input.setText(str(int(tva)))
        else:
            self.tva_input.setText(f"{tva:.2f}")
        self._tva_updating = False

        receipt_number = get_receipt_number()
        self._receipt_number_updating = True
        self.receipt_number_input.setText(str(receipt_number))
        self._receipt_number_updating = False

    def save_settings(self):
        """Save settings to database."""
        # Validate TVA
        tva_text = self.tva_input.text().strip()
        try:
            tva_value = float(tva_text) if tva_text else 0.0
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

        # Validate Receipt Number
        receipt_text = self.receipt_number_input.text().strip()
        try:
            receipt_value = int(receipt_text) if receipt_text else 1
        except ValueError:
            receipt_value = 1

        if receipt_value < 1:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Validation Error")
            msg.setText("Receipt number must be at least 1.")
            msg.setStyleSheet(self.theme.message_box_confirm())
            msg.exec()
            return

        update_tva(tva_value)
        update_receipt_number(receipt_value)
        self.set_editing(False)

        # Show success message
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Settings Saved")
        msg.setText("Settings have been saved successfully!")
        msg.setStyleSheet(self.theme.message_box_confirm())
        msg.exec()

    def create_manual_backup(self):
        """Create a manual database backup."""
        backup_path, success = create_backup("manual")

        if success:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Backup Created")
            msg.setText(f"Database backup created successfully!\n\nLocation:\n{backup_path}")
            msg.setStyleSheet(self.theme.message_box_confirm())
            msg.exec()
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Backup Failed")
            msg.setText("Failed to create database backup. Please try again.")
            msg.setStyleSheet(self.theme.message_box_confirm())
            msg.exec()

    # ------------------------------------------------------------------
    # Auto-update flow
    # ------------------------------------------------------------------

    def set_update_orchestrator_factory(self, factory):
        """Inject a custom factory (used by tests).

        ``factory`` must be a no-arg callable returning a configured
        :class:`UpdateOrchestrator`.
        """
        self._orchestrator_factory = factory

    def on_check_update_clicked(self):
        """Handler for the "Verifică actualizări" button."""
        if self._check_worker is not None and self._check_worker.isRunning():
            return
        self.check_update_button.setEnabled(False)
        self.update_status_label.setText("Se verifică actualizările...")

        try:
            orchestrator = self._orchestrator_factory()
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to build update orchestrator")
            self._show_update_error(f"Nu am putut iniția verificarea: {exc}")
            self.check_update_button.setEnabled(True)
            return

        self._orchestrator = orchestrator
        # NOTE: deliberately no ``parent=self`` here. ``QThread`` and
        # ``QObject`` parent ownership combined can crash on tear-down
        # if the parent is destroyed while ``run()`` is still active.
        # We instead hold a strong reference on ``self`` so the
        # worker is alive as long as the page is, and we explicitly
        # ``wait()`` for it in ``_cleanup_check_worker`` /
        # ``closeEvent``.
        self._check_worker = UpdateCheckWorker(orchestrator)
        self._check_worker.finished_ok.connect(self._on_check_finished)
        self._check_worker.failed.connect(self._on_check_failed)
        self._check_worker.finished.connect(self._cleanup_check_worker)
        self._check_worker.start()

    def _cleanup_check_worker(self):
        """Slot for ``QThread.finished``.

        We do NOT call ``deleteLater`` here — the worker is parented
        to the page so Qt cleans it up when the page itself is
        destroyed. Calling ``deleteLater`` from the worker's own
        ``finished`` signal can race with pending queued signals
        (``finished_ok``/``failed``) and crash under pytest-qt.
        """
        worker = self._check_worker
        if worker is None:
            return
        worker.wait(2000)
        self._check_worker = None

    def closeEvent(self, event):  # noqa: N802 (Qt naming)
        """Block until any background worker finishes before tear-down.

        Without this Qt can destroy ``self`` while a ``QThread`` is
        still inside ``run()`` and the interpreter crashes with an
        access violation under pytest-qt.
        """
        worker = self._check_worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)
        super().closeEvent(event)

    def _on_check_finished(self, info):
        """Slot for ``UpdateCheckWorker.finished_ok``."""
        self.check_update_button.setEnabled(True)
        if info is None:
            self.update_status_label.setText(f"Folosești cea mai recentă versiune ({__version__}).")
            return

        self.update_status_label.setText(
            f"Versiunea {info.version} este disponibilă (curentă: {__version__})."
        )
        self._prompt_to_download(info)

    def _on_check_failed(self, message: str):
        """Slot for ``UpdateCheckWorker.failed``."""
        self.check_update_button.setEnabled(True)
        self.update_status_label.setText(
            "Verificarea a eșuat. Vezi detaliile în mesajul de mai jos."
        )
        self._show_update_error(
            f"Nu am putut verifica actualizările:\n\n{message}\n\n"
            "Verifică conexiunea la internet și încearcă din nou."
        )

    def _prompt_to_download(self, info: UpdateInfo):
        """Ask the user whether to download the new version."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Actualizare disponibilă")
        text = (
            f"Versiunea {info.version} este disponibilă.\n"
            f"Versiunea curentă: {__version__}.\n\n"
            "Vrei să o descarci acum? La final aplicația va trebui să repornească."
        )
        if info.mandatory:
            text = "[Actualizare obligatorie]\n\n" + text
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        msg.setStyleSheet(self.theme.message_box_confirm())
        if msg.exec() != QMessageBox.StandardButton.Yes:
            self.update_status_label.setText(
                f"Versiunea {info.version} este disponibilă, dar nu ai descărcat-o."
            )
            return

        self._start_download(info)

    def _start_download(self, info: UpdateInfo):
        """Open the progress dialog and run the download."""
        dialog = UpdateProgressDialog(self._orchestrator, info, parent=self)
        dialog.start()
        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            error = dialog.error_message
            if error:
                self.update_status_label.setText("Descărcarea a eșuat.")
                self._show_update_error(f"Descărcarea actualizării a eșuat:\n\n{error}")
            else:
                self.update_status_label.setText("Descărcarea a fost anulată.")
            return

        download = dialog.download_result
        if download is None:  # pragma: no cover - defensive
            self.update_status_label.setText("Descărcarea s-a încheiat fără rezultat.")
            return

        self._prompt_to_apply(download)

    def _prompt_to_apply(self, download):
        """Ask the user whether to apply the freshly downloaded update."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Instalează actualizarea?")
        msg.setText(
            f"Versiunea {download.info.version} a fost descărcată.\n\n"
            "Aplicația trebuie să se închidă pentru a o instala. "
            "Va reporni automat la final. Continui?"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        msg.setStyleSheet(self.theme.message_box_confirm())
        if msg.exec() != QMessageBox.StandardButton.Yes:
            self.update_status_label.setText(
                f"Actualizarea {download.info.version} este pregătită în "
                f"{download.path}. Apasă din nou pentru a o instala."
            )
            return

        try:
            self._orchestrator.apply(download)
        except UpdateApplyError as exc:
            logger.warning("Apply failed: %s", exc)
            self.update_status_label.setText("Instalarea a eșuat.")
            self._show_update_error(f"Instalarea actualizării a eșuat:\n\n{exc}")
            return

        # The helper script is now waiting for THIS process to die so
        # it can swap directories. Closing the Qt event loop is the
        # cleanest way to do that.
        self.update_status_label.setText("Aplicația se închide pentru a finaliza instalarea...")
        QApplication.instance().quit()

    def _show_update_error(self, message: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Actualizări")
        msg.setText(message)
        msg.setStyleSheet(self.theme.message_box_confirm())
        msg.exec()


def _default_orchestrator_factory() -> UpdateOrchestrator:
    """Build an :class:`UpdateOrchestrator` for the running app.

    Kept at module level so :class:`SettingsPage.set_update_orchestrator_factory`
    can swap in a test stub without subclassing.
    """
    return UpdateOrchestrator(Version.coerce(__version__))
