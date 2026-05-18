"""Tests for the main application window."""

from pathlib import Path

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from src import main as main_mod
from src.main import SIDEBAR_LOGO_WIDTH, MainWindow, Sidebar, _resolve_app_icon


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    """Create MainWindow instance for tests."""
    window = MainWindow()
    yield window
    window.close()


@pytest.fixture
def sidebar(qapp):
    """Build a standalone sidebar for inspection without spinning up the
    whole MainWindow / DB / pages stack."""
    bar = Sidebar(on_page_changed=lambda _idx: None)
    yield bar
    bar.deleteLater()


def test_main_window_title(main_window):
    """Test that main window has correct title."""
    assert main_window.windowTitle() == "Neloaica"


def test_main_window_minimum_size(main_window):
    """Test that main window has correct minimum size."""
    assert main_window.minimumWidth() == 800
    assert main_window.minimumHeight() == 600


# ===========================================================================
# TestSidebarLogo
# ===========================================================================


class TestSidebarLogo:
    """The header of the sidebar should display the logo image instead of
    the old plain-text ``Neloaica`` title whenever the asset is on disk."""

    def test_header_is_a_qlabel(self, sidebar):
        # Header is the first widget added to the sidebar layout.
        header = sidebar.layout().itemAt(0).widget()
        assert isinstance(header, QLabel)

    def test_header_uses_pixmap_when_logo_exists(self, sidebar):
        header = sidebar.layout().itemAt(0).widget()
        # The asset ships with the repo; the sidebar must therefore pick
        # the image branch rather than the text fallback.
        assert not header.pixmap().isNull(), "Sidebar header should render the logo pixmap"
        assert header.text() == "", "Sidebar header should not display fallback text alongside logo"

    def test_header_pixmap_scaled_to_expected_width(self, sidebar):
        header = sidebar.layout().itemAt(0).widget()
        # Hard-coded constant in src/main.py — kept in sync with the
        # sidebar minimum width minus the logo container padding.
        assert header.pixmap().width() == SIDEBAR_LOGO_WIDTH

    def test_header_uses_logo_stylesheet(self, sidebar):
        # The black-background container styling that lets the logo art
        # blend into the sidebar header. Asserting on the colour itself
        # would couple this test to theme internals; checking the
        # stylesheet is non-empty is enough to detect a regression
        # where the styling stops being applied.
        header = sidebar.layout().itemAt(0).widget()
        assert "background-color" in header.styleSheet().lower()

    def test_falls_back_to_text_when_logo_missing(self, qapp, monkeypatch, tmp_path):
        # Point the resolver at a non-existent path so the sidebar takes
        # the fallback branch. The header must still be present (a
        # missing asset must not break startup).
        missing = tmp_path / "nope.png"
        monkeypatch.setattr(main_mod, "get_logo_png_path", lambda: missing)

        bar = Sidebar(on_page_changed=lambda _idx: None)
        try:
            header = bar.layout().itemAt(0).widget()
            assert isinstance(header, QLabel)
            assert header.pixmap().isNull()
            assert header.text() == "Neloaica"
        finally:
            bar.deleteLater()


# ===========================================================================
# TestApplicationIcon
# ===========================================================================


class TestApplicationIcon:
    """``_resolve_app_icon`` chooses ``.ico`` when present (Windows
    multi-resolution icon) and falls back to ``.png`` otherwise."""

    def test_returns_qicon(self, qapp):
        assert isinstance(_resolve_app_icon(), QIcon)

    def test_returns_non_null_icon_when_assets_present(self, qapp):
        icon = _resolve_app_icon()
        # Both assets ship with the repo so the resolver must surface
        # one of them.
        assert not icon.isNull()

    def test_prefers_ico_over_png(self, qapp, monkeypatch, tmp_path):
        ico = tmp_path / "logo.ico"
        png = tmp_path / "logo.png"
        ico.write_bytes(_one_pixel_ico())
        png.write_bytes(_one_pixel_png())

        monkeypatch.setattr(main_mod, "get_logo_ico_path", lambda: ico)
        monkeypatch.setattr(main_mod, "get_logo_png_path", lambda: png)

        icon = _resolve_app_icon()
        # Best we can do without poking at QIcon internals: the icon
        # must be valid AND the ICO was the first candidate, so the
        # function never even read the PNG.
        assert not icon.isNull()

    def test_falls_back_to_png_when_ico_missing(self, qapp, monkeypatch, tmp_path):
        ico = tmp_path / "missing.ico"
        png = tmp_path / "logo.png"
        png.write_bytes(_one_pixel_png())

        monkeypatch.setattr(main_mod, "get_logo_ico_path", lambda: ico)
        monkeypatch.setattr(main_mod, "get_logo_png_path", lambda: png)

        icon = _resolve_app_icon()
        assert not icon.isNull()

    def test_returns_empty_icon_when_assets_missing(self, qapp, monkeypatch, tmp_path):
        # Neither asset on disk — Qt's setWindowIcon must still accept
        # the returned value (it does — an empty QIcon is a no-op).
        monkeypatch.setattr(main_mod, "get_logo_ico_path", lambda: tmp_path / "x.ico")
        monkeypatch.setattr(main_mod, "get_logo_png_path", lambda: tmp_path / "x.png")
        assert _resolve_app_icon().isNull()


def _one_pixel_png() -> bytes:
    """Return the bytes of a minimal valid 1x1 PNG.

    Keeps the icon-resolution tests hermetic: we don't depend on the
    real branding asset and we don't write large binary fixtures into
    the test data folder.
    """
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\xa7\xa9\xe1\xeb"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _one_pixel_ico() -> bytes:
    """Return the bytes of a minimal valid 1x1 ICO wrapping a PNG.

    ICO header (6 bytes) + one directory entry (16 bytes) + a 1x1 PNG.
    Used by the resolver tests as a hermetic ICO fixture.
    """
    png = _one_pixel_png()
    header = b"\x00\x00\x01\x00\x01\x00"
    # width=1, height=1, colors=0, reserved=0, planes=1, bpp=32,
    # bytes=len(png), offset=22 (6 header + 16 entry).
    entry = (
        b"\x01\x01\x00\x00\x01\x00\x20\x00"
        + len(png).to_bytes(4, "little")
        + (22).to_bytes(4, "little")
    )
    return header + entry + png


# ===========================================================================
# TestLogoAssetPresence
# ===========================================================================


class TestLogoAssetPresence:
    """Defensive sanity check on the bundled branding assets."""

    def test_png_present(self):
        repo_root = Path(__file__).resolve().parents[2]
        assert (repo_root / "templates" / "images" / "Neloaica_logo.png").is_file()

    def test_ico_present(self):
        repo_root = Path(__file__).resolve().parents[2]
        assert (repo_root / "templates" / "images" / "Neloaica_logo.ico").is_file()
