"""Smoke test: execute ``Neloaica.spec`` in a sandbox.

The static AST tests in ``test_pyinstaller_spec.py`` only check the
*shape* of the spec. This file goes one step further: it actually
runs the spec with stubbed PyInstaller globals and verifies that

  * ``_data_files()`` returns absolute paths that exist on disk,
  * the entry point passed to ``Analysis`` resolves to ``src/main.py``,
  * the bundled template is the same file ``src.paths.get_bundle_dir()``
    will look up at runtime.

If someone bumps the spec but forgets to keep the template path in
sync, this test fails before CI ever spends a minute on PyInstaller.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = REPO_ROOT / "Neloaica.spec"


def _run_spec_in_sandbox():
    """Execute ``Neloaica.spec`` with the PyInstaller globals stubbed.

    PyInstaller's ``Analysis`` returns an object whose attributes
    (``pure``, ``zipped_data``, ``scripts``, ``binaries``, ``zipfiles``,
    ``datas``) are then passed into ``PYZ`` / ``EXE`` / ``COLLECT``.
    A ``MagicMock`` swallows arbitrary attribute access so we don't
    have to fake every internal field.

    Returns ``(spec_globals, captured)`` where ``captured`` records
    each stage's call args.
    """
    captured = {"Analysis": None, "PYZ": None, "EXE": None, "COLLECT": None}

    def make_stub(name):
        def stub(*args, **kwargs):
            captured[name] = {"args": args, "kwargs": kwargs}
            return MagicMock(name=name)

        return stub

    spec_globals: dict = {
        "__file__": str(SPEC_PATH),
        "__name__": "__main__",
        "Analysis": make_stub("Analysis"),
        "PYZ": make_stub("PYZ"),
        "EXE": make_stub("EXE"),
        "COLLECT": make_stub("COLLECT"),
    }

    exec(SPEC_PATH.read_text(encoding="utf-8"), spec_globals)
    return spec_globals, captured


@pytest.fixture(scope="module")
def sandboxed():
    return _run_spec_in_sandbox()


# ===========================================================================
# TestExecution
# ===========================================================================


class TestExecution:
    def test_spec_executes_without_error(self, sandboxed):
        spec_globals, captured = sandboxed
        # All four PyInstaller stages must have been called.
        for stage in ("Analysis", "PYZ", "EXE", "COLLECT"):
            assert captured[stage] is not None, f"{stage} was never called"

    def test_data_files_helper_runs(self, sandboxed):
        spec_globals, _ = sandboxed
        helper = spec_globals.get("_data_files")
        assert callable(helper)
        items = helper()
        assert isinstance(items, list)
        assert len(items) >= 1


# ===========================================================================
# TestAnalysisCall
# ===========================================================================


class TestAnalysisCall:
    def test_first_arg_is_main_py(self, sandboxed):
        _, captured = sandboxed
        scripts = captured["Analysis"]["args"][0]
        # First positional arg is a list of scripts.
        assert isinstance(scripts, list)
        assert len(scripts) == 1
        entry = Path(scripts[0]).resolve()
        assert entry.name == "main.py"
        assert entry.parent.name == "src"
        assert entry.is_file(), f"Entry point does not exist: {entry}"

    def test_pathex_contains_project_root(self, sandboxed):
        _, captured = sandboxed
        pathex = captured["Analysis"]["kwargs"]["pathex"]
        assert isinstance(pathex, list)
        resolved = {Path(p).resolve() for p in pathex}
        assert REPO_ROOT in resolved

    def test_datas_paths_exist_on_disk(self, sandboxed):
        _, captured = sandboxed
        datas = captured["Analysis"]["kwargs"]["datas"]
        assert datas, "Analysis.datas must include the Excel template"
        for src, dest in datas:
            assert Path(src).exists(), f"datas references missing source: {src}"
            assert isinstance(dest, str) and dest.startswith(
                "templates"
            ), f"datas dest must live under templates/, got {dest!r}"

    def test_template_path_matches_runtime_lookup(self, sandboxed):
        """The bundled template is exactly the one runtime code reads.

        ``src.paths.get_bundle_dir() / "templates" / "Template-deviz.xlsx"``
        is what runtime code expects. The spec must include the same
        absolute file under that relative subpath, otherwise the frozen
        binary would crash on receipt generation.
        """
        from src.paths import get_bundle_dir

        runtime_template = get_bundle_dir() / "templates" / "Template-deviz.xlsx"
        assert runtime_template.is_file()

        _, captured = sandboxed
        datas = captured["Analysis"]["kwargs"]["datas"]
        bundled = [s for s, _ in datas if s.endswith("Template-deviz.xlsx")]
        assert len(bundled) == 1
        assert Path(bundled[0]).resolve() == runtime_template.resolve()


# ===========================================================================
# TestExeKwargs
# ===========================================================================


class TestExeKwargs:
    def test_name(self, sandboxed):
        _, captured = sandboxed
        assert captured["EXE"]["kwargs"]["name"] == "Neloaica"

    def test_console_false(self, sandboxed):
        _, captured = sandboxed
        assert captured["EXE"]["kwargs"]["console"] is False

    def test_exclude_binaries_true(self, sandboxed):
        _, captured = sandboxed
        assert captured["EXE"]["kwargs"]["exclude_binaries"] is True


# ===========================================================================
# TestCollectKwargs
# ===========================================================================


class TestCollectKwargs:
    def test_bundle_directory_is_neloaica(self, sandboxed):
        _, captured = sandboxed
        assert captured["COLLECT"]["kwargs"]["name"] == "Neloaica"
