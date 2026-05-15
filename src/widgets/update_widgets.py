"""Qt-side glue for the auto-updater.

This module is the thin layer that bridges the Qt event loop with the
GUI-agnostic :mod:`src.services.updater` package. It lives under
``src/widgets/`` precisely so the ``src/services/updater/`` subtree
stays Qt-free (and therefore trivially importable from CLI scripts /
unit tests that do not pull in PySide6).

What it exposes:

* :class:`UpdateCheckWorker` - runs ``orchestrator.check()`` on a
  background ``QThread`` and emits ``finished_ok(info_or_none)`` /
  ``failed(message)`` when done.
* :class:`UpdateDownloadWorker` - runs ``orchestrator.download(info)``
  on a background thread, forwards every progress callback as a
  ``progress(bytes_done, total_or_minus_one)`` signal (Qt's signal
  marshalling cannot carry ``None``, so the total is emitted as -1
  when the server omits ``Content-Length``).
* :class:`UpdateProgressDialog` - a small ``QDialog`` with a
  determinate progress bar, status label and Cancel button. Used
  from :class:`SettingsPage` but reusable from any other place that
  wants to surface a download.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from src.services.updater import (
    DownloadResult,
    UpdateCheckError,
    UpdateDownloadError,
    UpdateError,
    UpdateInfo,
    UpdateOrchestrator,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


class UpdateCheckWorker(QThread):
    """Run ``orchestrator.check()`` off the GUI thread.

    Emits exactly one of :attr:`finished_ok` or :attr:`failed`. Both
    signals are connected with ``Qt.QueuedConnection`` by default so
    receivers run on the GUI thread regardless of which thread the
    worker is destroyed from.
    """

    #: Emitted on success. Argument is the :class:`UpdateInfo` for an
    #: available update, or ``None`` when the current version is the
    #: latest one.
    finished_ok = Signal(object)

    #: Emitted on failure. Argument is a human-readable error message
    #: ready to be shown in a dialog box.
    failed = Signal(str)

    def __init__(self, orchestrator: UpdateOrchestrator, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._orchestrator = orchestrator

    def run(self) -> None:
        try:
            info = self._orchestrator.check()
        except UpdateCheckError as exc:
            logger.warning("Update check failed: %s", exc)
            self.failed.emit(str(exc))
        except UpdateError as exc:
            logger.warning("Update check error: %s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected error during update check")
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.finished_ok.emit(info)


class UpdateDownloadWorker(QThread):
    """Run ``orchestrator.download(info)`` off the GUI thread.

    Progress is reported through :attr:`progress`. Because Qt signal
    marshalling cannot carry ``None`` natively across threads, the
    "total bytes" field is emitted as ``-1`` when the server does not
    advertise ``Content-Length``.

    Cancellation is cooperative: call :meth:`request_cancel` and the
    next chunk reported by the downloader aborts the run, emitting
    :attr:`failed` with a "cancelled" message.
    """

    progress = Signal(int, int)  # bytes_done, total_or_minus_one
    finished_ok = Signal(object)  # DownloadResult
    failed = Signal(str)

    def __init__(
        self,
        orchestrator: UpdateOrchestrator,
        info: UpdateInfo,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._orchestrator = orchestrator
        self._info = info
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Schedule cancellation; takes effect at the next chunk."""
        self._cancel_requested = True

    def _on_progress(self, done: int, total: Optional[int]) -> None:
        # Qt cannot serialise ``None`` over a signal of (int, int).
        self.progress.emit(done, total if total is not None else -1)

    def _is_cancelled(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:
        try:
            result = self._orchestrator.download(
                self._info,
                on_progress=self._on_progress,
                cancel=self._is_cancelled,
            )
        except UpdateDownloadError as exc:
            logger.warning("Update download failed: %s", exc)
            self.failed.emit(str(exc))
        except UpdateError as exc:
            logger.warning("Update download error: %s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unexpected error during update download")
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.finished_ok.emit(result)


# ---------------------------------------------------------------------------
# Progress dialog
# ---------------------------------------------------------------------------


class UpdateProgressDialog(QDialog):
    """Modal dialog with a determinate progress bar.

    Wraps :class:`UpdateDownloadWorker` for convenience. The caller
    constructs the dialog with an orchestrator + ``UpdateInfo`` and
    calls :meth:`start`. ``exec()`` returns ``QDialog.Accepted`` on a
    successful download (``result()`` exposed via
    :attr:`download_result`), ``Rejected`` on cancel or error.
    """

    def __init__(
        self,
        orchestrator: UpdateOrchestrator,
        info: UpdateInfo,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Descarc Neloaica v{info.version}")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._info = info
        self._download_result: Optional[DownloadResult] = None
        self._error: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._status = QLabel(f"Se descarcă versiunea {info.version}...")
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate until first progress event
        self._bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._bar)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._buttons.rejected.connect(self._on_cancel_clicked)
        layout.addWidget(self._buttons)

        self._worker = UpdateDownloadWorker(orchestrator, info, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.failed.connect(self._on_failed)

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    @property
    def download_result(self) -> Optional[DownloadResult]:
        return self._download_result

    @property
    def error_message(self) -> Optional[str]:
        return self._error

    def start(self) -> None:
        """Kick off the background download. Safe to call before exec()."""
        self._worker.start()

    # ---------------------------------------------------------------
    # Slots
    # ---------------------------------------------------------------

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            if self._bar.maximum() != total:
                self._bar.setRange(0, total)
            self._bar.setValue(done)
            percent = int(done * 100 / total)
            self._status.setText(
                f"Se descarcă versiunea {self._info.version}... {percent}% "
                f"({_format_bytes(done)} / {_format_bytes(total)})"
            )
        else:
            # Unknown total — keep the bar marquee-style but still
            # display the number of bytes received.
            self._status.setText(
                f"Se descarcă versiunea {self._info.version}... " f"{_format_bytes(done)}"
            )

    def _on_finished_ok(self, result: DownloadResult) -> None:
        self._download_result = result
        self.accept()

    def _on_failed(self, message: str) -> None:
        self._error = message
        self.reject()

    def _on_cancel_clicked(self) -> None:
        self._status.setText("Se anulează descărcarea...")
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self._worker.request_cancel()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        # If the user closes the window directly, behave like Cancel
        # and make sure the worker has a chance to clean up its
        # partial files before we tear it down.
        if self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(2000)
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_bytes(value: int) -> str:
    """Pretty-print a byte count for the status line."""
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    if value < 1024 * 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    return f"{value / (1024 * 1024 * 1024):.2f} GB"


__all__ = [
    "UpdateCheckWorker",
    "UpdateDownloadWorker",
    "UpdateProgressDialog",
]
