"""Styles module for centralized theming."""

from .theme_manager import ThemeManager

# Global theme manager instance
theme = ThemeManager()

__all__ = ['theme', 'ThemeManager']
