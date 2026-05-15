"""Tests for ``src/widgets/update_widgets.py``.

The ``UpdateCheckWorker`` and ``UpdateDownloadWorker`` classes are
``QThread`` subclasses, but for the unit-test layer we exercise their
business logic by calling ``run()`` synchronously rather than
``start()``. Signals are still emitted normally (Qt does not require
a thread for that) and the tests therefore avoid the race-conditions
we observed with the pytest-qt + QThread + offscreen combination on
Windows.

Real threading is exercised end-to-end through the GitHub Actions
CI pipeline and by manually clicking the button from the Settings
page.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog

from src.services.updater import (
    DownloadResult,
    UpdateChannel,
    UpdateCheckError,
    UpdateDownloadError,
    UpdateInfo,
)
from src.widgets.update_widgets import (
    UpdateCheckWorker,
    UpdateDownloadWorker,
    UpdateProgressDialog,
    _format_bytes,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _info(version="1.2.3"):
    return UpdateInfo.from_manifest_entry(
        UpdateChannel.STABLE,
        {
            "version": version,
            "download_url": f"https://example.com/Neloaica-v{version}-windows.zip",
        },
    )


def _download_result(info=None, path=Path("/tmp/x.zip")):
    return DownloadResult(
        path=path,
        bytes_downloaded=42,
        sha256="a" * 64,
        info=info or _info(),
    )


def _orchestrator(
    *,
    check_return=None,
    check_raise=None,
    download_return=None,
    download_raise=None,
    progress_events=None,
    cancel_check=None,
):
    orch = MagicMock()

    def _check_side_effect():
        if check_raise is not None:
            raise check_raise
        return check_return

    orch.check.side_effect = _check_side_effect

    def _download_side_effect(info, *, on_progress=None, cancel=None):
        # Replay any pre-canned progress events.
        if progress_events is not None:
            for done, total in progress_events:
                if cancel is not None and cancel():
                    raise UpdateDownloadError("cancelled at %d" % done)
                if on_progress is not None:
                    on_progress(done, total)
        if cancel_check is not None and cancel is not None:
            # Allow tests to assert cancel was wired.
            cancel_check(cancel)
        if download_raise is not None:
            raise download_raise
        return download_return

    orch.download.side_effect = _download_side_effect
    return orch


# ===========================================================================
# TestFormatBytes
# ===========================================================================


class TestFormatBytes:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "0 B"),
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1024 * 1024, "1.0 MB"),
            (3 * 1024 * 1024, "3.0 MB"),
            (1024**3, "1.00 GB"),
        ],
    )
    def test_formats_pretty(self, value, expected):
        assert _format_bytes(value) == expected


# ===========================================================================
# TestUpdateCheckWorker
# ===========================================================================


class TestUpdateCheckWorker:
    """Drive ``UpdateCheckWorker.run()`` synchronously and assert on
    the signals it emits. See module docstring for rationale."""

    def test_emits_finished_ok_with_info(self, qapp):
        info = _info("2.0.0")
        orch = _orchestrator(check_return=info)
        worker = UpdateCheckWorker(orch)

        emitted = []
        worker.finished_ok.connect(lambda value: emitted.append(value))
        worker.failed.connect(lambda msg: emitted.append(("FAIL", msg)))
        worker.run()

        assert emitted == [info]

    def test_emits_finished_ok_with_none(self, qapp):
        orch = _orchestrator(check_return=None)
        worker = UpdateCheckWorker(orch)
        emitted = []
        worker.finished_ok.connect(lambda value: emitted.append(value))
        worker.run()
        assert emitted == [None]

    def test_emits_failed_on_check_error(self, qapp):
        orch = _orchestrator(check_raise=UpdateCheckError("dns"))
        worker = UpdateCheckWorker(orch)
        messages = []
        worker.failed.connect(lambda msg: messages.append(msg))
        worker.run()
        assert messages and "dns" in messages[0]

    def test_emits_failed_on_unexpected_exception(self, qapp):
        orch = _orchestrator(check_raise=RuntimeError("boom"))
        worker = UpdateCheckWorker(orch)
        messages = []
        worker.failed.connect(lambda msg: messages.append(msg))
        worker.run()
        assert messages and "boom" in messages[0]


# ===========================================================================
# TestUpdateDownloadWorker
# ===========================================================================


class TestUpdateDownloadWorker:
    def test_emits_finished_ok_with_result(self, qapp, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch = _orchestrator(download_return=result)
        worker = UpdateDownloadWorker(orch, info)
        emitted = []
        worker.finished_ok.connect(lambda r: emitted.append(r))
        worker.run()
        assert emitted == [result]

    def test_forwards_progress_events(self, qapp, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch = _orchestrator(
            download_return=result,
            progress_events=[(0, 100), (50, 100), (100, 100)],
        )
        worker = UpdateDownloadWorker(orch, info)
        events = []
        worker.progress.connect(lambda d, t: events.append((d, t)))
        worker.run()
        assert events == [(0, 100), (50, 100), (100, 100)]

    def test_translates_none_total_to_minus_one(self, qapp, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch = _orchestrator(download_return=result, progress_events=[(0, None), (10, None)])
        worker = UpdateDownloadWorker(orch, info)
        events = []
        worker.progress.connect(lambda d, t: events.append((d, t)))
        worker.run()
        assert all(total == -1 for _, total in events)

    def test_emits_failed_on_download_error(self, qapp, tmp_path):
        info = _info()
        orch = _orchestrator(download_raise=UpdateDownloadError("network broke"))
        worker = UpdateDownloadWorker(orch, info)
        messages = []
        worker.failed.connect(lambda msg: messages.append(msg))
        worker.run()
        assert messages and "network broke" in messages[0]

    def test_request_cancel_is_observed_by_orchestrator(self, qapp, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        captured = {}

        def remember_cancel(cancel_predicate):
            captured["fn"] = cancel_predicate

        orch = _orchestrator(download_return=result, cancel_check=remember_cancel)
        worker = UpdateDownloadWorker(orch, info)
        worker.run()
        assert "fn" in captured
        assert captured["fn"]() is False
        worker.request_cancel()
        assert captured["fn"]() is True


# ===========================================================================
# TestUpdateProgressDialog
# ===========================================================================


class TestUpdateProgressDialog:
    """Drive the dialog's worker synchronously to keep the test
    deterministic. We exercise the signal-slot wiring without
    relying on a real QThread (see module docstring)."""

    def test_dialog_completes_with_accepted(self, qtbot, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch = _orchestrator(
            download_return=result,
            progress_events=[(0, 100), (100, 100)],
        )
        dialog = UpdateProgressDialog(orch, info)
        qtbot.addWidget(dialog)
        dialog._worker.run()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.download_result is result
        assert dialog.error_message is None

    def test_dialog_rejects_on_download_error(self, qtbot, tmp_path):
        info = _info()
        orch = _orchestrator(download_raise=UpdateDownloadError("nope"))
        dialog = UpdateProgressDialog(orch, info)
        qtbot.addWidget(dialog)
        dialog._worker.run()
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert dialog.download_result is None
        assert "nope" in (dialog.error_message or "")

    def test_progress_updates_bar(self, qtbot, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch = _orchestrator(
            download_return=result,
            progress_events=[(0, 200), (100, 200), (200, 200)],
        )
        dialog = UpdateProgressDialog(orch, info)
        qtbot.addWidget(dialog)
        dialog._worker.run()
        assert dialog._bar.maximum() == 200
        assert dialog._bar.value() == 200
