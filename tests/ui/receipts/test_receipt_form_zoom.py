"""Tests for the receipt form text-zoom feature.

Covers:
  * ``scale_font_sizes`` pure helper (regex rewrite of ``font-size``)
  * zoom_in / zoom_out / zoom_reset state + clamping
  * the zoom level label tracking the scale
  * scaled widgets derive from their unscaled baseline (idempotent)
  * the zoom controls themselves are never scaled
"""

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from src.pages.receipts.receipt_form import (
    ZOOM_MAX,
    ZOOM_MIN,
    scale_pixel_sizes,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ===========================================================================
# scale_pixel_sizes (pure)
# ===========================================================================


class TestScalePixelSizes:
    def test_single_size_scaled(self):
        assert scale_pixel_sizes("font-size: 14px;", 1.5) == "font-size: 21px;"

    def test_multiple_sizes_scaled(self):
        qss = "QLabel { font-size: 10px; } QLineEdit { font-size: 20px; }"
        out = scale_pixel_sizes(qss, 2.0)
        assert "font-size: 20px" in out
        assert "font-size: 40px" in out

    def test_padding_is_scaled(self):
        # Both values of a shorthand padding are scaled (this is what lets
        # more rows fit when zooming out).
        assert scale_pixel_sizes("padding: 8px 12px;", 0.5) == "padding: 4px 6px;"

    def test_mixed_properties_scaled(self):
        qss = "QGroupBox { font-size: 16px; padding: 20px; margin-top: 10px; }"
        out = scale_pixel_sizes(qss, 0.5)
        assert "font-size: 8px" in out
        assert "padding: 10px" in out
        assert "margin-top: 5px" in out

    def test_no_px_unchanged(self):
        qss = "QLabel { color: red; font-weight: bold; }"
        assert scale_pixel_sizes(qss, 2.0) == qss

    def test_empty_unchanged(self):
        assert scale_pixel_sizes("", 2.0) == ""

    def test_never_below_one_pixel(self):
        # Even an aggressive shrink keeps at least 1px.
        assert scale_pixel_sizes("font-size: 2px;", 0.1) == "font-size: 1px;"

    def test_identity_at_scale_one(self):
        assert scale_pixel_sizes("font-size: 14px; padding: 8px;", 1.0) == (
            "font-size: 14px; padding: 8px;"
        )


# ===========================================================================
# Receipt form zoom integration
# ===========================================================================

_PATCHES = [
    ("src.pages.receipts.receipt_info.get_all_clients", []),
    ("src.pages.receipts.receipt_info.get_all_cars", []),
    ("src.pages.receipts.receipt_info.get_all_employees", []),
    ("src.pages.receipts.defects_section.get_all_defects", []),
    ("src.pages.receipts.parts_section.get_all_parts", []),
    ("src.pages.receipts.labor_section.get_all_labor", []),
    ("src.pages.receipts.billable_parts_section.get_all_parts", []),
]


@pytest.fixture
def form(qapp):
    from src.pages.receipts.receipt_form import ReceiptFormPage

    mgrs = [patch(target, return_value=list(val)) for target, val in _PATCHES]
    for m in mgrs:
        m.__enter__()
    try:
        page = ReceiptFormPage()
    finally:
        for m in mgrs:
            m.__exit__(None, None, None)
    return page


class TestZoomState:
    def test_default_scale_is_one(self, form):
        assert form._font_scale == 1.0
        assert form.zoom_level_label.text() == "100%"

    def test_zoom_in_increases_scale_and_label(self, form):
        form.zoom_in()
        assert form._font_scale == pytest.approx(1.1)
        assert form.zoom_level_label.text() == "110%"

    def test_zoom_out_decreases_scale(self, form):
        form.zoom_out()
        assert form._font_scale == pytest.approx(0.9)
        assert form.zoom_level_label.text() == "90%"

    def test_zoom_clamps_at_max(self, form):
        for _ in range(50):
            form.zoom_in()
        assert form._font_scale == pytest.approx(ZOOM_MAX)

    def test_zoom_clamps_at_min(self, form):
        for _ in range(50):
            form.zoom_out()
        assert form._font_scale == pytest.approx(ZOOM_MIN)

    def test_reset_returns_to_one(self, form):
        form.zoom_in()
        form.zoom_in()
        form.zoom_reset()
        assert form._font_scale == 1.0
        assert form.zoom_level_label.text() == "100%"


class TestZoomApplication:
    def test_title_font_scales_and_is_reversible(self, form):
        # Baseline 28px title.
        assert "font-size: 28px" in form.title_label.styleSheet()

        form.zoom_in()  # 1.1 -> round(28 * 1.1) = 31
        assert "font-size: 31px" in form.title_label.styleSheet()

        form.zoom_reset()  # derived from cached baseline, back to 28
        assert "font-size: 28px" in form.title_label.styleSheet()

    def test_zoom_controls_are_not_scaled(self, form):
        form.zoom_in()
        # Chrome widgets are skipped entirely, so no baseline is cached on them.
        assert form.zoom_in_btn.property("_base_qss") is None
        assert form.zoom_out_btn.property("_base_qss") is None
        assert form.zoom_level_label.property("_base_qss") is None
