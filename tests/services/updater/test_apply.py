"""Tests for ``src/services/updater/apply.py``.

The apply stage talks to the filesystem and (in production) launches
a detached PowerShell process. Tests substitute the ``_popen`` seam
so no subprocess is actually started and every other side effect is
contained inside ``tmp_path``.
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

from src.services.updater import (
    ApplyPlan,
    UpdateApplier,
    UpdateApplyError,
    UpdateChannel,
    UpdateInfo,
)
from src.services.updater.apply import (
    DEFAULT_EXECUTABLE_NAME,
    HELPER_SCRIPT_NAME,
    SCHEDULED_TASK_PREFIX,
    _ps_quote,
    _safe_extract_zip,
    _win_quote_arg,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _info(version: str = "1.2.3"):
    return UpdateInfo.from_manifest_entry(
        UpdateChannel.STABLE,
        {
            "version": version,
            "download_url": f"https://example.com/Neloaica-v{version}-windows.zip",
        },
    )


def _make_zip_payload(files: dict) -> bytes:
    """Build an in-memory zip from a ``{path: content}`` mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(path, content)
    return buf.getvalue()


def _write_zip(tmp_path: Path, files: dict, name: str = "update.zip") -> Path:
    path = tmp_path / name
    path.write_bytes(_make_zip_payload(files))
    return path


def _make_applier(
    tmp_path: Path,
    *,
    spawn: list | None = None,
    install_name: str = "Neloaica",
    staging_name: str = "staging",
    use_schtasks: bool = False,
) -> UpdateApplier:
    install_dir = tmp_path / install_name
    staging_root = tmp_path / staging_name
    applier = UpdateApplier(
        install_dir=install_dir,
        staging_root=staging_root,
        executable_name=DEFAULT_EXECUTABLE_NAME,
        use_schtasks=use_schtasks,
    )
    captured = spawn if spawn is not None else []

    def fake_popen(argv):
        captured.append(list(argv))

    applier._popen = fake_popen  # type: ignore[method-assign]
    applier._captured_popen = captured  # type: ignore[attr-defined]
    return applier


# ===========================================================================
# TestConstruction
# ===========================================================================


class TestConstruction:
    def test_rejects_empty_executable_name(self):
        with pytest.raises(ValueError):
            UpdateApplier(executable_name="")

    def test_install_dir_falls_back_to_project_root(self):
        applier = UpdateApplier()
        install = applier.resolve_install_dir()
        # The project root has a ``src`` folder.
        assert (install / "src").is_dir()

    def test_install_dir_override_wins(self, tmp_path):
        applier = UpdateApplier(install_dir=tmp_path)
        assert applier.resolve_install_dir() == tmp_path

    def test_staging_root_defaults_under_user_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.services.updater.apply.get_user_data_dir", lambda: tmp_path)
        applier = UpdateApplier()
        assert applier.resolve_staging_root() == tmp_path / "updates" / "staging"

    def test_staging_dir_for_uses_version(self, tmp_path):
        applier = UpdateApplier(install_dir=tmp_path, staging_root=tmp_path / "s")
        assert applier.staging_dir_for(_info("1.2.3")).name == "Neloaica-v1.2.3"


# ===========================================================================
# TestPsQuote
# ===========================================================================


class TestPsQuote:
    def test_simple_path(self):
        assert _ps_quote("C:/foo/bar") == "'C:/foo/bar'"

    def test_path_with_space(self):
        assert _ps_quote(r"C:\Program Files\Neloaica") == r"'C:\Program Files\Neloaica'"

    def test_escapes_single_quote(self):
        assert _ps_quote("it's") == "'it''s'"

    def test_accepts_pathlib(self, tmp_path):
        assert _ps_quote(tmp_path) == "'" + str(tmp_path) + "'"


# ===========================================================================
# TestSafeExtractZip
# ===========================================================================


class TestSafeExtractZip:
    def test_extracts_flat_layout(self, tmp_path):
        payload = _write_zip(tmp_path, {"Neloaica.exe": b"\x00", "data.txt": "hi"})
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(payload) as zf:
            _safe_extract_zip(zf, dest)
        assert (dest / "Neloaica.exe").exists()
        assert (dest / "data.txt").read_text() == "hi"

    def test_blocks_path_traversal(self, tmp_path):
        payload = _write_zip(tmp_path, {"../evil.txt": "bad"})
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(payload) as zf, pytest.raises(UpdateApplyError):
            _safe_extract_zip(zf, dest)


# ===========================================================================
# TestBuildPlan
# ===========================================================================


class TestBuildPlan:
    def test_missing_archive_raises(self, tmp_path):
        applier = _make_applier(tmp_path)
        with pytest.raises(UpdateApplyError) as ei:
            applier._build_plan(tmp_path / "missing.zip", _info())
        assert "not found" in str(ei.value).lower()

    def test_directory_argument_raises(self, tmp_path):
        applier = _make_applier(tmp_path)
        d = tmp_path / "adir"
        d.mkdir()
        with pytest.raises(UpdateApplyError):
            applier._build_plan(d, _info())

    def test_plan_has_expected_paths(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        assert plan.install_dir == tmp_path / "Neloaica"
        assert plan.staging_dir == tmp_path / "staging" / "Neloaica-v1.2.3"
        assert plan.executable_path == plan.install_dir / "Neloaica.exe"
        assert plan.backup_dir.name.startswith("Neloaica.old.")
        assert plan.helper_script_path.name == HELPER_SCRIPT_NAME
        assert plan.helper_script_path.parent == applier.resolve_staging_root()
        assert plan.info.version.major == 1
        assert plan.current_pid > 0
        assert plan.task_name.startswith(SCHEDULED_TASK_PREFIX)
        assert "1.2.3" in plan.task_name
        assert str(plan.current_pid) in plan.task_name


# ===========================================================================
# TestStageArchive
# ===========================================================================


class TestStageArchive:
    def test_flat_archive_stages_correctly(self, tmp_path):
        archive = _write_zip(
            tmp_path,
            {
                "Neloaica.exe": b"\x00",
                "data/templates/x.xlsx": b"X",
            },
        )
        applier = _make_applier(tmp_path)
        plan = applier._build_plan(archive, _info())
        applier._stage_archive(plan)
        applier._validate_staged_tree(plan)
        assert (plan.staging_dir / "Neloaica.exe").exists()
        assert (plan.staging_dir / "data" / "templates" / "x.xlsx").exists()

    def test_wrapped_archive_is_flattened(self, tmp_path):
        # ``dist/Neloaica/...`` layout (the default PyInstaller output
        # when zipping the folder by itself).
        archive = _write_zip(
            tmp_path,
            {
                "Neloaica/Neloaica.exe": b"\x00",
                "Neloaica/data/x.txt": "ok",
            },
        )
        applier = _make_applier(tmp_path)
        plan = applier._build_plan(archive, _info())
        applier._stage_archive(plan)
        applier._validate_staged_tree(plan)
        assert (plan.staging_dir / "Neloaica.exe").exists()
        assert (plan.staging_dir / "data" / "x.txt").exists()
        # The inner folder must be promoted away, not kept as a sibling.
        assert not (plan.staging_dir / "Neloaica").exists()

    def test_missing_executable_raises(self, tmp_path):
        archive = _write_zip(tmp_path, {"data/only.txt": "no exe here"})
        applier = _make_applier(tmp_path)
        plan = applier._build_plan(archive, _info())
        applier._stage_archive(plan)
        with pytest.raises(UpdateApplyError) as ei:
            applier._validate_staged_tree(plan)
        assert "does not contain" in str(ei.value)

    def test_corrupt_zip_raises(self, tmp_path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not-a-zip-file")
        applier = _make_applier(tmp_path)
        plan = applier._build_plan(bad, _info())
        with pytest.raises(UpdateApplyError) as ei:
            applier._stage_archive(plan)
        assert "corrupt" in str(ei.value).lower()

    def test_restages_overwrites_previous_attempt(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info())
        # Simulate a previous staging attempt with stale content.
        plan.staging_dir.mkdir(parents=True)
        (plan.staging_dir / "leftover.txt").write_text("stale")
        applier._stage_archive(plan)
        applier._validate_staged_tree(plan)
        assert not (plan.staging_dir / "leftover.txt").exists()
        assert (plan.staging_dir / "Neloaica.exe").exists()

    def test_path_traversal_blocked(self, tmp_path):
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00", "../escape.txt": "bad"})
        applier = _make_applier(tmp_path)
        plan = applier._build_plan(archive, _info())
        with pytest.raises(UpdateApplyError):
            applier._stage_archive(plan)


# ===========================================================================
# TestHelperScript
# ===========================================================================


class TestHelperScript:
    def test_renders_without_unresolved_placeholders(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        script = UpdateApplier.build_helper_script(plan)
        # Spot-check: every interpolated value must appear and the
        # template-level placeholders must all be substituted.
        assert "{install_dir}" not in script
        assert "{staging_dir}" not in script
        assert "{pid}" not in script
        assert "{executable}" not in script
        assert "{task_name}" not in script

    def test_helper_script_contains_task_cleanup(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        script = UpdateApplier.build_helper_script(plan)
        # The helper must self-clean its Scheduled Task on completion.
        assert "$TaskName" in script
        assert "schtasks.exe /Delete" in script
        assert _ps_quote(plan.task_name) in script

    def test_paths_are_single_quoted(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        script = UpdateApplier.build_helper_script(plan)
        assert _ps_quote(plan.install_dir) in script
        assert _ps_quote(plan.staging_dir) in script
        assert _ps_quote(plan.backup_dir) in script
        assert _ps_quote(plan.executable_path) in script
        assert str(plan.current_pid) in script

    def test_template_keeps_powershell_format_operator(self, tmp_path):
        # Sanity: the inner ``"{0}" -f $stamp, $msg`` segment is kept
        # intact even though we use ``str.format`` on the template.
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info())
        script = UpdateApplier.build_helper_script(plan)
        assert '"[{0}] {1}" -f $stamp, $msg' in script

    def test_quotes_paths_containing_apostrophes(self, tmp_path):
        applier = UpdateApplier(
            install_dir=tmp_path / "user's app",
            staging_root=tmp_path / "stage",
        )
        applier._popen = lambda argv: None  # type: ignore[method-assign]
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info())
        script = UpdateApplier.build_helper_script(plan)
        # PowerShell single-quoted-string escape is a doubled quote.
        assert "user''s app" in script


# ===========================================================================
# TestSpawnArgv
# ===========================================================================


class TestSpawnArgv:
    def test_argv_shape(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info())
        argv = UpdateApplier.build_spawn_argv(plan)
        assert argv[0] == "powershell.exe"
        assert "-NoProfile" in argv
        assert "-WindowStyle" in argv and "Hidden" in argv
        assert "-ExecutionPolicy" in argv and "Bypass" in argv
        assert "-File" in argv
        assert argv[-1] == str(plan.helper_script_path)


# ===========================================================================
# TestApplyEndToEnd
# ===========================================================================


class TestApplyEndToEnd:
    def test_apply_runs_full_pipeline(self, tmp_path):
        spawn: list = []
        applier = _make_applier(tmp_path, spawn=spawn)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        plan = applier.apply(archive, _info("1.2.3"))

        assert isinstance(plan, ApplyPlan)
        assert plan.staging_dir.exists()
        assert (plan.staging_dir / "Neloaica.exe").exists()
        assert plan.helper_script_path.exists()
        helper_text = plan.helper_script_path.read_text(encoding="utf-8")
        assert "Update helper" not in helper_text  # sanity for casing
        assert "Neloaica auto-update helper" in helper_text
        assert len(spawn) == 1
        assert spawn[0][0] == "powershell.exe"
        assert spawn[0][-1] == str(plan.helper_script_path)

    def test_apply_failure_does_not_spawn_helper(self, tmp_path):
        spawn: list = []
        applier = _make_applier(tmp_path, spawn=spawn)
        # Archive that lacks the executable -> validation fails after
        # staging but BEFORE writing/launching the helper.
        archive = _write_zip(tmp_path, {"data/x.txt": "no exe"})

        with pytest.raises(UpdateApplyError):
            applier.apply(archive, _info())

        assert spawn == []

    def test_apply_propagates_popen_failure(self, tmp_path):
        applier = _make_applier(tmp_path)

        def failing_popen(argv):
            raise OSError("permission denied")

        applier._popen = failing_popen  # type: ignore[method-assign]
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        with pytest.raises(UpdateApplyError) as ei:
            applier.apply(archive, _info())
        assert "Cannot launch helper" in str(ei.value)

    def test_apply_writes_helper_log_path_into_script(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier.apply(archive, _info())

        expected_log = plan.helper_script_path.with_suffix(".log")
        assert _ps_quote(expected_log) in plan.helper_script_path.read_text(encoding="utf-8")

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only assertion")
    def test_popen_argv_does_not_use_windows_flags_on_posix(self):
        # On non-Windows the default ``_popen`` should not use
        # ``DETACHED_PROCESS`` / ``CREATE_NEW_PROCESS_GROUP``. We re-read
        # the production implementation via the source to make sure the
        # ``sys.platform == "win32"`` guard is in place.
        from src.services.updater import apply as apply_mod

        source = Path(apply_mod.__file__).read_text(encoding="utf-8")
        assert 'sys.platform == "win32"' in source


# ===========================================================================
# TestWinQuoteArg
# ===========================================================================


class TestWinQuoteArg:
    def test_plain_arg_unchanged(self):
        assert _win_quote_arg("powershell.exe") == "powershell.exe"
        assert _win_quote_arg("-NoProfile") == "-NoProfile"

    def test_empty_arg_quoted(self):
        assert _win_quote_arg("") == '""'

    def test_arg_with_space_quoted(self):
        assert _win_quote_arg("C:\\Program Files\\app") == '"C:\\Program Files\\app"'

    def test_embedded_quote_escaped(self):
        assert _win_quote_arg('say "hi"') == '"say \\"hi\\""'

    def test_trailing_backslash_doubled_inside_quotes(self):
        # MSVCRT rule: ``N`` backslashes before the closing quote
        # become ``2N`` so the closing quote stays literal-quote.
        assert _win_quote_arg("path\\with space\\") == '"path\\with space\\\\"'


# ===========================================================================
# TestSchtasksArgv
# ===========================================================================


class TestSchtasksArgv:
    def test_tr_value_contains_powershell_and_script_path(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        tr = UpdateApplier.build_schtasks_tr_value(plan)
        assert "powershell.exe" in tr
        assert "-NoProfile" in tr
        assert "-File" in tr
        assert str(plan.helper_script_path) in tr

    def test_create_argv_shape(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        argv = list(UpdateApplier.build_schtasks_create_argv(plan))
        assert argv[0] == "schtasks"
        assert argv[1] == "/Create"
        assert "/TN" in argv and plan.task_name in argv
        assert "/TR" in argv
        assert "/SC" in argv and "ONCE" in argv
        assert "/F" in argv

    def test_run_argv_shape(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        argv = list(UpdateApplier.build_schtasks_run_argv(plan))
        assert argv == ["schtasks", "/Run", "/TN", plan.task_name]

    def test_delete_argv_shape(self, tmp_path):
        applier = _make_applier(tmp_path)
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})
        plan = applier._build_plan(archive, _info("1.2.3"))
        argv = list(UpdateApplier.build_schtasks_delete_argv(plan))
        assert argv == ["schtasks", "/Delete", "/TN", plan.task_name, "/F"]


# ===========================================================================
# TestSpawnViaSchtasks
# ===========================================================================


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestSpawnViaSchtasks:
    def _make_schtasks_applier(self, tmp_path, results):
        """Build an applier that uses schtasks with a scripted result queue.

        ``results`` is a list of ``_FakeCompletedProcess`` instances
        returned in order, one per ``_run_schtasks`` invocation. The
        list of recorded argvs is exposed on the applier as
        ``_captured_schtasks``.
        """
        applier = UpdateApplier(
            install_dir=tmp_path / "Neloaica",
            staging_root=tmp_path / "staging",
            executable_name=DEFAULT_EXECUTABLE_NAME,
            use_schtasks=True,
        )
        captured: list[list[str]] = []
        queue = list(results)

        def fake_run_schtasks(argv):
            captured.append(list(argv))
            if queue:
                return queue.pop(0)
            return _FakeCompletedProcess(0)

        applier._run_schtasks = fake_run_schtasks  # type: ignore[method-assign]

        def fail_popen(_argv):
            raise AssertionError("_popen must not be reached when schtasks succeeds")

        applier._popen = fail_popen  # type: ignore[method-assign]
        applier._captured_schtasks = captured  # type: ignore[attr-defined]
        return applier

    def test_apply_uses_schtasks_create_then_run(self, tmp_path):
        applier = self._make_schtasks_applier(
            tmp_path,
            results=[_FakeCompletedProcess(0), _FakeCompletedProcess(0)],
        )
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        plan = applier.apply(archive, _info("1.2.3"))

        calls = applier._captured_schtasks  # type: ignore[attr-defined]
        assert len(calls) == 2
        assert calls[0][:2] == ["schtasks", "/Create"]
        assert plan.task_name in calls[0]
        assert calls[1] == ["schtasks", "/Run", "/TN", plan.task_name]

    def test_create_failure_raises_and_skips_run(self, tmp_path):
        applier = self._make_schtasks_applier(
            tmp_path,
            results=[_FakeCompletedProcess(1, stderr="ACCESS DENIED")],
        )
        # We don't want the fallback _popen to swallow the failure
        # silently, so make it raise too.
        applier._popen = lambda argv: (_ for _ in ()).throw(  # type: ignore[method-assign]
            OSError("popen also unavailable")
        )
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        with pytest.raises(UpdateApplyError) as ei:
            applier.apply(archive, _info())

        assert "Cannot launch helper" in str(ei.value)
        calls = applier._captured_schtasks  # type: ignore[attr-defined]
        # /Create was attempted, /Run never reached.
        assert calls[0][:2] == ["schtasks", "/Create"]
        assert not any(c[:2] == ["schtasks", "/Run"] for c in calls)

    def test_run_failure_cleans_up_and_falls_back(self, tmp_path):
        applier = self._make_schtasks_applier(
            tmp_path,
            results=[
                _FakeCompletedProcess(0),  # /Create succeeds
                _FakeCompletedProcess(1, stderr="task could not be run"),  # /Run
                _FakeCompletedProcess(0),  # /Delete cleanup
            ],
        )
        # Track that the Popen fallback is exercised after schtasks
        # fails on /Run.
        popen_calls: list = []
        applier._popen = lambda argv: popen_calls.append(list(argv))  # type: ignore[method-assign]
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        plan = applier.apply(archive, _info())

        calls = applier._captured_schtasks  # type: ignore[attr-defined]
        # /Delete must have been called for cleanup.
        assert any(c[:2] == ["schtasks", "/Delete"] for c in calls)
        # Fallback Popen must have been invoked with the helper.
        assert len(popen_calls) == 1
        assert popen_calls[0][0] == "powershell.exe"
        assert popen_calls[0][-1] == str(plan.helper_script_path)

    def test_oserror_from_run_schtasks_falls_back_to_popen(self, tmp_path):
        applier = UpdateApplier(
            install_dir=tmp_path / "Neloaica",
            staging_root=tmp_path / "staging",
            executable_name=DEFAULT_EXECUTABLE_NAME,
            use_schtasks=True,
        )

        def boom(_argv):
            raise OSError("schtasks not found")

        applier._run_schtasks = boom  # type: ignore[method-assign]
        popen_calls: list = []
        applier._popen = lambda argv: popen_calls.append(list(argv))  # type: ignore[method-assign]
        archive = _write_zip(tmp_path, {"Neloaica.exe": b"\x00"})

        plan = applier.apply(archive, _info())

        assert len(popen_calls) == 1
        assert popen_calls[0][0] == "powershell.exe"
        assert popen_calls[0][-1] == str(plan.helper_script_path)
