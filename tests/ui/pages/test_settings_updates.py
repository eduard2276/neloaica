"""UI tests for the auto-update section in ``SettingsPage``.

These exercise the wiring between the page, the orchestrator and the
worker/dialog widgets. The orchestrator itself is stubbed out so no
network / disk activity happens.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from src import __version__
from src.services.updater import (
    ApplyPlan,
    DownloadResult,
    UpdateApplyError,
    UpdateChannel,
    UpdateCheckError,
    UpdateInfo,
)


class _SyncCheckWorker(QObject):
    """Drop-in replacement for ``UpdateCheckWorker``.

    Same public surface as the real worker but runs ``check()``
    synchronously inside ``start()`` so tests never spin up a real
    ``QThread``. Using a fake here avoids race-conditions and the
    sporadic Windows access violations we observed when the real
    QThread was wired into pytest-qt across multiple test files.
    """

    finished_ok = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orchestrator = orchestrator

    def isRunning(self):  # noqa: N802 (Qt naming compatibility)
        return False

    def wait(self, _msecs=None):
        return True

    def start(self):
        try:
            info = self._orchestrator.check()
        except UpdateCheckError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.finished_ok.emit(info)
        finally:
            self.finished.emit()


@pytest.fixture(autouse=True)
def _stub_check_worker():
    """Swap the real QThread-based worker for the sync stub."""
    with patch("src.pages.settings.UpdateCheckWorker", _SyncCheckWorker):
        yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def page(qapp, qtbot):
    """Build a SettingsPage with the DB layer mocked out.

    Registered with ``qtbot`` so pytest-qt closes the widget cleanly
    after the test — without this, a still-running ``QThread`` from
    the auto-update flow can race with interpreter tear-down and
    crash the process with an access violation.
    """
    with (
        patch("src.pages.settings.get_tva", return_value=21.0),
        patch("src.pages.settings.get_receipt_number", return_value=1),
    ):
        from src.pages.settings import SettingsPage

        widget = SettingsPage()
        qtbot.addWidget(widget)
        return widget


@pytest.fixture(autouse=True)
def _silence_msgbox():
    """Default messageboxes to ``Yes`` so prompts don't block."""
    with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _info(version="2.0.0", **overrides):
    entry = {
        "version": version,
        "download_url": f"https://example.com/Neloaica-v{version}-windows.zip",
        **overrides,
    }
    return UpdateInfo.from_manifest_entry(UpdateChannel.STABLE, entry)


def _download_result(info=None, path=Path("/tmp/x.zip")):
    return DownloadResult(
        path=path,
        bytes_downloaded=42,
        sha256="a" * 64,
        info=info or _info(),
    )


def _apply_plan(info=None):
    info = info or _info()
    return ApplyPlan(
        archive_path=Path("/tmp/x.zip"),
        staging_dir=Path("/tmp/stage"),
        install_dir=Path("/tmp/install"),
        executable_path=Path("/tmp/install/Neloaica.exe"),
        backup_dir=Path("/tmp/install.old"),
        helper_script_path=Path("/tmp/stage/apply_update.ps1"),
        info=info,
        current_pid=1234,
    )


def _install_orchestrator(page, orchestrator):
    """Make the page use ``orchestrator`` instead of the real factory."""
    page.set_update_orchestrator_factory(lambda: orchestrator)


# ===========================================================================
# TestUpdateSectionLayout
# ===========================================================================


class TestUpdateSectionLayout:
    def test_section_widgets_present(self, page):
        assert page.current_version_label is not None
        assert page.update_status_label is not None
        assert page.check_update_button is not None

    def test_current_version_label_shows_version(self, page):
        assert __version__ in page.current_version_label.text()

    def test_initial_status_invites_check(self, page):
        text = page.update_status_label.text().lower()
        assert "verifica" in text or "verifică" in text


# ===========================================================================
# TestCheckButtonNoUpdate
# ===========================================================================


class TestCheckButtonNoUpdate:
    def test_status_shows_up_to_date(self, page, qtbot):
        orch = MagicMock()
        orch.check.return_value = None
        _install_orchestrator(page, orch)

        page.on_check_update_clicked()
        qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)
        assert __version__ in page.update_status_label.text()
        assert "recent" in page.update_status_label.text().lower()

    def test_check_button_disabled_during_run(self, page, qtbot):
        orch = MagicMock()
        orch.check.return_value = None
        _install_orchestrator(page, orch)

        page.on_check_update_clicked()
        # Button should be re-enabled once the worker finishes.
        qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)


# ===========================================================================
# TestCheckButtonFailure
# ===========================================================================


class TestCheckButtonFailure:
    def test_status_shows_error_summary(self, page, qtbot):
        orch = MagicMock()
        orch.check.side_effect = UpdateCheckError("DNS failure")
        _install_orchestrator(page, orch)

        page.on_check_update_clicked()
        qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)
        assert "eșuat" in page.update_status_label.text().lower()


# ===========================================================================
# TestCheckButtonHasUpdate
# ===========================================================================


class TestCheckButtonHasUpdate:
    def test_declined_download_keeps_status(self, page, qtbot, monkeypatch):
        info = _info("9.9.9")
        orch = MagicMock()
        orch.check.return_value = info
        _install_orchestrator(page, orch)

        # User clicks "No" on the download prompt.
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.No):
            page.on_check_update_clicked()
            qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)

        text = page.update_status_label.text()
        assert "9.9.9" in text
        # Download / apply should NOT have been called when the user
        # declines the prompt.
        orch.download.assert_not_called()
        orch.apply.assert_not_called()

    def test_accepted_download_then_decline_apply(self, page, qtbot):
        info = _info("9.9.9")
        result = _download_result(info=info)
        orch = MagicMock()
        orch.check.return_value = info

        # Stub the dialog so we don't have to run a real QThread.
        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
        fake_dialog.download_result = result
        fake_dialog.error_message = None

        # Prompt #1 (download) accepted, Prompt #2 (apply) declined.
        prompts = iter([QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No])

        _install_orchestrator(page, orch)
        with (
            patch(
                "src.pages.settings.UpdateProgressDialog",
                return_value=fake_dialog,
            ),
            patch.object(QMessageBox, "exec", side_effect=lambda: next(prompts)),
        ):
            page.on_check_update_clicked()
            qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)

        fake_dialog.start.assert_called_once()
        fake_dialog.exec.assert_called_once()
        orch.apply.assert_not_called()
        # The path of the downloaded archive must be surfaced so the
        # user can re-apply later.
        assert str(result.path) in page.update_status_label.text()

    def test_full_flow_apply_calls_quit(self, page, qtbot):
        info = _info("9.9.9")
        result = _download_result(info=info)
        plan = _apply_plan(info=info)
        orch = MagicMock()
        orch.check.return_value = info
        orch.apply.return_value = plan

        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
        fake_dialog.download_result = result
        fake_dialog.error_message = None

        _install_orchestrator(page, orch)
        with (
            patch(
                "src.pages.settings.UpdateProgressDialog",
                return_value=fake_dialog,
            ),
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch.object(QApplication, "instance") as qapp_instance,
        ):
            qapp_instance.return_value = MagicMock()
            page.on_check_update_clicked()
            qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)

        orch.apply.assert_called_once_with(result)
        qapp_instance.return_value.quit.assert_called_once()

    def test_download_dialog_failure_keeps_app_open(self, page, qtbot):
        info = _info("9.9.9")
        orch = MagicMock()
        orch.check.return_value = info

        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = QDialog.DialogCode.Rejected
        fake_dialog.download_result = None
        fake_dialog.error_message = "network broke"

        _install_orchestrator(page, orch)
        with (
            patch(
                "src.pages.settings.UpdateProgressDialog",
                return_value=fake_dialog,
            ),
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
        ):
            page.on_check_update_clicked()
            qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)

        orch.apply.assert_not_called()
        assert "eșuat" in page.update_status_label.text().lower()

    def test_apply_failure_surfaces_in_status(self, page, qtbot):
        info = _info("9.9.9")
        result = _download_result(info=info)
        orch = MagicMock()
        orch.check.return_value = info
        orch.apply.side_effect = UpdateApplyError("disk full")

        fake_dialog = MagicMock()
        fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
        fake_dialog.download_result = result
        fake_dialog.error_message = None

        _install_orchestrator(page, orch)
        with (
            patch(
                "src.pages.settings.UpdateProgressDialog",
                return_value=fake_dialog,
            ),
            patch.object(
                QMessageBox,
                "exec",
                return_value=QMessageBox.StandardButton.Yes,
            ),
        ):
            page.on_check_update_clicked()
            qtbot.waitUntil(lambda: page.check_update_button.isEnabled(), timeout=2000)

        assert "eșuat" in page.update_status_label.text().lower()


# ===========================================================================
# TestOrchestratorFactoryInjection
# ===========================================================================


class TestOrchestratorFactoryInjection:
    def test_set_update_orchestrator_factory_overrides_default(self, page):
        custom = MagicMock(return_value=MagicMock())
        page.set_update_orchestrator_factory(custom)
        assert page._orchestrator_factory is custom
