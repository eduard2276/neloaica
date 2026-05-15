"""Tests for `src/styles/theme_manager.ThemeManager`.

Covers:
  * TestSingleton          — same instance everywhere
  * TestThemeSwitching     — set_theme toggles light <-> dark; unknown theme is ignored
  * TestColors             — get_color returns expected values, unknown → black
  * TestStyleGenerators    — every generator returns a non-empty string
  * TestButtonVariants     — `button("primary"/"success"/"danger"/"cancel"/"gray")`
"""

import pytest

from src.styles.theme_manager import ThemeManager
from src.styles.colors import LIGHT_THEME, DARK_THEME
from src.styles import theme as global_theme


# ===========================================================================
# TestSingleton
# ===========================================================================

class TestSingleton:
    def test_two_instances_are_the_same_object(self):
        a = ThemeManager()
        b = ThemeManager()
        assert a is b

    def test_global_theme_is_thememanager(self):
        assert isinstance(global_theme, ThemeManager)
        assert global_theme is ThemeManager()


# ===========================================================================
# TestThemeSwitching
# ===========================================================================

class TestThemeSwitching:
    def teardown_method(self):
        # Always restore the default for the rest of the suite
        ThemeManager().set_theme("light")

    def test_default_is_light(self):
        # Reset to a known state
        ThemeManager().set_theme("light")
        assert ThemeManager().current_theme == "light"

    def test_switch_to_dark(self):
        ThemeManager().set_theme("dark")
        assert ThemeManager().current_theme == "dark"
        assert ThemeManager().get_color("bg_primary") == DARK_THEME["bg_primary"]

    def test_switch_back_to_light(self):
        ThemeManager().set_theme("dark")
        ThemeManager().set_theme("light")
        assert ThemeManager().current_theme == "light"
        assert ThemeManager().get_color("bg_primary") == LIGHT_THEME["bg_primary"]

    def test_unknown_theme_is_ignored(self):
        before = ThemeManager().current_theme
        ThemeManager().set_theme("rainbow")
        assert ThemeManager().current_theme == before


# ===========================================================================
# TestColors
# ===========================================================================

class TestColors:
    def test_known_color_returns_palette_value(self):
        ThemeManager().set_theme("light")
        assert ThemeManager().get_color("primary") == LIGHT_THEME["primary"]

    def test_unknown_color_returns_black(self):
        assert ThemeManager().get_color("not_a_color") == "#000000"


# ===========================================================================
# TestStyleGenerators
# ===========================================================================

# A representative subset; verify every generator is callable and returns a
# non-empty CSS-like string (no exception, no None).
_GENERATORS = [
    "page_title", "combobox", "line_edit", "line_edit_dialog",
    "search_input", "groupbox", "groupbox_inactive", "list_widget",
    "list_widget_with_items", "tab_widget", "table", "dialog",
    "button_add", "button_remove", "message_box_confirm",
    "sidebar", "sidebar_title", "sidebar_button", "content_area",
    "scroll_area", "label_item", "form_label", "line_edit_readonly",
    "calendar_dialog", "calendar",
]


class TestStyleGenerators:
    @pytest.mark.parametrize("name", _GENERATORS)
    def test_returns_non_empty_string(self, name):
        tm = ThemeManager()
        fn = getattr(tm, name)
        out = fn()
        assert isinstance(out, str)
        assert out.strip() != ""


# ===========================================================================
# TestButtonVariants
# ===========================================================================

class TestButtonVariants:
    @pytest.mark.parametrize("variant", ["primary", "success", "danger", "cancel", "gray"])
    def test_button_returns_string(self, variant):
        out = ThemeManager().button(variant)
        assert isinstance(out, str) and out

    @pytest.mark.parametrize("variant", ["edit", "delete", "primary"])
    def test_button_icon_returns_string(self, variant):
        out = ThemeManager().button_icon(variant)
        assert isinstance(out, str) and out

    def test_button_default_variant_is_primary(self):
        a = ThemeManager().button()
        b = ThemeManager().button("primary")
        assert a == b


# ===========================================================================
# TestPaletteFidelity
# ===========================================================================

class TestPaletteFidelity:
    @pytest.mark.parametrize("color_name", LIGHT_THEME.keys())
    def test_light_palette_complete(self, color_name):
        ThemeManager().set_theme("light")
        assert ThemeManager().get_color(color_name) == LIGHT_THEME[color_name]

    @pytest.mark.parametrize("color_name", DARK_THEME.keys())
    def test_dark_palette_complete(self, color_name):
        ThemeManager().set_theme("dark")
        try:
            assert ThemeManager().get_color(color_name) == DARK_THEME[color_name]
        finally:
            ThemeManager().set_theme("light")
