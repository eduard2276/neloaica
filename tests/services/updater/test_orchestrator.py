"""Tests for ``src/services/updater/orchestrator.py``.

The orchestrator is a thin facade — we focus on its caching
behaviour, error semantics and the propagation of progress / cancel
callbacks. The underlying stages are stubbed out so the test never
touches the network or the filesystem.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.services.updater import (
    ApplyPlan,
    DownloadResult,
    UpdateChannel,
    UpdateCheckError,
    UpdateInfo,
    UpdateOrchestrator,
    Version,
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


def _download_result(info=None, path=Path("/tmp/Neloaica-v1.2.3.zip")):
    return DownloadResult(
        path=Path(path),
        bytes_downloaded=1234,
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
        task_name="Neloaica-Apply-Update-test-1234",
    )


def _make_orch(
    *,
    check_returns=None,
    check_raises=None,
    download_returns=None,
    apply_returns=None,
):
    checker = MagicMock()
    if check_raises is not None:
        checker.check.side_effect = check_raises
    else:
        checker.check.return_value = check_returns

    downloader = MagicMock()
    if download_returns is not None:
        downloader.download.return_value = download_returns

    applier = MagicMock()
    if apply_returns is not None:
        applier.apply.return_value = apply_returns

    orch = UpdateOrchestrator(
        Version(1, 0, 0),
        checker=checker,
        downloader=downloader,
        applier=applier,
    )
    return orch, checker, downloader, applier


# ===========================================================================
# TestConstruction
# ===========================================================================


class TestConstruction:
    def test_requires_version_instance(self):
        with pytest.raises(TypeError):
            UpdateOrchestrator("1.0.0")  # type: ignore[arg-type]

    def test_defaults_current_version_property(self):
        orch, *_ = _make_orch()
        assert orch.current_version == Version(1, 0, 0)
        assert orch.channel is UpdateChannel.STABLE

    def test_initial_state_is_empty(self):
        orch, *_ = _make_orch()
        assert orch.last_info is None
        assert orch.last_download is None
        assert orch.last_plan is None
        assert orch.is_update_available() is False
        assert orch.is_download_ready() is False


# ===========================================================================
# TestCheck
# ===========================================================================


class TestCheck:
    def test_check_returns_info_and_caches(self):
        target = _info("2.0.0")
        orch, checker, *_ = _make_orch(check_returns=target)
        result = orch.check()
        assert result is target
        assert orch.last_info is target
        assert orch.is_update_available() is True
        assert checker.check.call_count == 1

    def test_check_returns_none_when_no_update(self):
        orch, *_ = _make_orch(check_returns=None)
        assert orch.check() is None
        assert orch.last_info is None
        assert orch.is_update_available() is False

    def test_check_propagates_check_error(self):
        orch, *_ = _make_orch(check_raises=UpdateCheckError("dns"))
        with pytest.raises(UpdateCheckError):
            orch.check()
        assert orch.last_info is None


# ===========================================================================
# TestDownload
# ===========================================================================


class TestDownload:
    def test_download_uses_last_info_by_default(self, tmp_path):
        info = _info("2.0.0")
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch, _, downloader, _ = _make_orch(check_returns=info, download_returns=result)
        orch.check()
        out = orch.download()
        assert out is result
        downloader.download.assert_called_once()
        assert downloader.download.call_args.args[0] is info

    def test_download_accepts_explicit_info(self, tmp_path):
        info = _info("3.0.0")
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch, _, downloader, _ = _make_orch(download_returns=result)
        out = orch.download(info)
        assert out is result
        assert downloader.download.call_args.args[0] is info

    def test_download_raises_when_no_info(self):
        orch, *_ = _make_orch()
        with pytest.raises(RuntimeError) as ei:
            orch.download()
        assert "check()" in str(ei.value).lower() or "info=" in str(ei.value)

    def test_download_forwards_progress_and_cancel(self, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        orch, _, downloader, _ = _make_orch(download_returns=result)

        progress = lambda d, t: None  # noqa: E731
        cancel = lambda: False  # noqa: E731

        orch.download(info, on_progress=progress, cancel=cancel)
        kwargs = downloader.download.call_args.kwargs
        assert kwargs["on_progress"] is progress
        assert kwargs["cancel"] is cancel


# ===========================================================================
# TestApply
# ===========================================================================


class TestApply:
    def test_apply_uses_last_download_by_default(self, tmp_path):
        info = _info("2.0.0")
        result = _download_result(info=info, path=tmp_path / "x.zip")
        plan = _apply_plan(info=info)
        orch, _, _, applier = _make_orch(
            check_returns=info, download_returns=result, apply_returns=plan
        )
        orch.check()
        orch.download()
        out = orch.apply()
        assert out is plan
        applier.apply.assert_called_once_with(result.path, info)
        assert orch.last_plan is plan

    def test_apply_accepts_explicit_download(self, tmp_path):
        info = _info()
        result = _download_result(info=info, path=tmp_path / "x.zip")
        plan = _apply_plan(info=info)
        orch, _, _, applier = _make_orch(apply_returns=plan)
        out = orch.apply(result)
        assert out is plan
        applier.apply.assert_called_once_with(result.path, info)

    def test_apply_raises_when_no_download(self):
        orch, *_ = _make_orch()
        with pytest.raises(RuntimeError):
            orch.apply()


# ===========================================================================
# TestEndToEndChain
# ===========================================================================


class TestEndToEndChain:
    def test_full_chain_caches_each_stage(self, tmp_path):
        info = _info("2.0.0")
        result = _download_result(info=info, path=tmp_path / "x.zip")
        plan = _apply_plan(info=info)
        orch, *_ = _make_orch(check_returns=info, download_returns=result, apply_returns=plan)
        assert orch.check() is info
        assert orch.is_update_available() is True
        assert orch.download() is result
        assert orch.is_download_ready() is True
        assert orch.apply() is plan
        assert orch.last_info is info
        assert orch.last_download is result
        assert orch.last_plan is plan


# ===========================================================================
# TestManifestUrlPropagation
# ===========================================================================


class TestManifestUrlPropagation:
    def test_passes_explicit_url_to_default_checker(self):
        orch = UpdateOrchestrator(Version(1, 0, 0), manifest_url="https://x/y.json")
        assert orch.manifest_url == "https://x/y.json"
        assert orch.checker.manifest_url == "https://x/y.json"

    def test_honors_env_var(self, monkeypatch):
        monkeypatch.setenv("NELOAICA_UPDATE_MANIFEST_URL", "https://branch.example/m.json")
        orch = UpdateOrchestrator(Version(1, 0, 0))
        assert orch.manifest_url == "https://branch.example/m.json"
