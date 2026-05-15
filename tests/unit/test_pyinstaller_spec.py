"""Tests for ``Neloaica.spec``.

PyInstaller spec files are Python — but executing them outside of
PyInstaller pulls in undefined globals (``Analysis``, ``PYZ``,
``EXE``, ``COLLECT``). Instead of running the file, we parse it and
walk the AST so the contract (entry point, bundled assets, exe name,
windowed mode) is asserted without spinning up PyInstaller.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SPEC_PATH = Path(__file__).resolve().parent.parent.parent / "Neloaica.spec"


@pytest.fixture(scope="module")
def spec_text() -> str:
    if not SPEC_PATH.is_file():
        pytest.fail(f"Missing PyInstaller spec: {SPEC_PATH}")
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec_ast(spec_text: str) -> ast.Module:
    return ast.parse(spec_text)


def _find_call(tree: ast.Module, func_name: str) -> ast.Call:
    """Locate the first call expression like ``EXE(...)`` in the spec."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func_name:
                return node
    raise AssertionError(f"No {func_name}(...) call found in spec")


def _kw(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    raise AssertionError(f"{call.func.id} call has no kwarg {name!r}")


# ===========================================================================
# TestFileExists
# ===========================================================================


class TestFileExists:
    def test_spec_file_exists(self):
        assert SPEC_PATH.is_file()

    def test_spec_is_valid_python(self, spec_ast):
        # Successful ast.parse already proves it. Add an explicit assert
        # so the test reads naturally.
        assert isinstance(spec_ast, ast.Module)


# ===========================================================================
# TestAnalysis
# ===========================================================================


class TestAnalysis:
    def test_entry_point_is_src_main(self, spec_ast, spec_text):
        # Make sure the spec actually has an Analysis() call before doing
        # string matching on its body — guards against a future refactor
        # that drops Analysis entirely.
        _find_call(spec_ast, "Analysis")
        # The first positional arg is built from a function call
        # (``str(PROJECT_ROOT / "src" / "main.py")``) so we cannot
        # ast.literal_eval it. String matching is enough.
        assert "src" in spec_text and "main.py" in spec_text

    def test_has_datas_kwarg(self, spec_ast):
        analysis = _find_call(spec_ast, "Analysis")
        _kw(analysis, "datas")  # raises if missing

    def test_template_is_bundled(self, spec_text):
        # The Excel template path is built from PROJECT_ROOT — assert on
        # the raw text since the spec relies on runtime path joining.
        assert "Template-deviz.xlsx" in spec_text
        assert "templates" in spec_text

    def test_template_lands_in_templates_subdir(self, spec_text):
        # `paths.get_bundle_dir() / "templates" / "Template-deviz.xlsx"`
        # is what runtime code looks up; the spec must place the file
        # under "templates" (the second tuple element).
        assert '"templates"' in spec_text or "'templates'" in spec_text

    def test_pathex_includes_project_root(self, spec_ast, spec_text):
        analysis = _find_call(spec_ast, "Analysis")
        _kw(analysis, "pathex")
        assert "PROJECT_ROOT" in spec_text


# ===========================================================================
# TestExe
# ===========================================================================


class TestExe:
    def test_exe_name_is_neloaica(self, spec_ast):
        exe = _find_call(spec_ast, "EXE")
        name = _kw(exe, "name")
        assert isinstance(name, ast.Constant)
        assert name.value == "Neloaica"

    def test_exe_is_windowed_not_console(self, spec_ast):
        exe = _find_call(spec_ast, "EXE")
        console = _kw(exe, "console")
        assert isinstance(console, ast.Constant)
        assert console.value is False, "Desktop app must build as windowed (.exe without a console)"

    def test_exe_excludes_binaries_for_onedir(self, spec_ast):
        # exclude_binaries=True is what makes COLLECT pick them up — i.e.
        # the spec is a onedir build, which the auto-update PRs depend on.
        exe = _find_call(spec_ast, "EXE")
        excl = _kw(exe, "exclude_binaries")
        assert isinstance(excl, ast.Constant)
        assert excl.value is True

    def test_exe_does_not_enable_debug(self, spec_ast):
        exe = _find_call(spec_ast, "EXE")
        debug = _kw(exe, "debug")
        assert isinstance(debug, ast.Constant)
        assert debug.value is False


# ===========================================================================
# TestCollect
# ===========================================================================


class TestCollect:
    def test_collect_produces_neloaica_dir(self, spec_ast):
        collect = _find_call(spec_ast, "COLLECT")
        name = _kw(collect, "name")
        assert isinstance(name, ast.Constant)
        # PyInstaller writes the bundle to ``dist/<name>/``. The release
        # workflow zips ``dist/Neloaica/`` so the dir name must match.
        assert name.value == "Neloaica"


# ===========================================================================
# TestRawText
# ===========================================================================


class TestRawText:
    def test_documents_onedir_choice(self, spec_text):
        # Future-us reading the file should know why onedir was picked.
        assert "onedir" in spec_text.lower() or "onefile" in spec_text.lower()

    def test_does_not_use_upx_compression(self, spec_text):
        # UPX-compressed binaries trip Windows Defender heuristics on a
        # surprisingly large fraction of machines. Onedir without UPX is
        # the safest default for end-user laptops.
        assert "upx=False" in spec_text
        assert "upx=True" not in spec_text
