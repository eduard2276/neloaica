"""Theme manager for centralized styling."""

from .colors import THEMES, LIGHT_THEME


class ThemeManager:
    """Manages application theming with style generators."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_theme = "light"
        self._colors = LIGHT_THEME.copy()
    
    @property
    def current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme
    
    def set_theme(self, theme_name: str):
        """Set the current theme."""
        if theme_name in THEMES:
            self._current_theme = theme_name
            self._colors = THEMES[theme_name].copy()
    
    def get_color(self, color_name: str) -> str:
        """Get a color value by name."""
        return self._colors.get(color_name, "#000000")
    
    # ==================== Component Styles ====================
    
    def page_title(self) -> str:
        """Style for page titles."""
        return f"""
            font-size: 28px;
            font-weight: bold;
            color: {self._colors['text_primary']};
        """
    
    def combobox(self) -> str:
        """Style for comboboxes."""
        return f"""
            QComboBox {{
                background-color: {self._colors['bg_primary']};
                border: 2px solid {self._colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: {self._colors['text_primary']};
                min-height: 30px;
            }}
            QComboBox:disabled {{
                background-color: {self._colors['bg_secondary']};
                color: {self._colors['text_secondary']};
            }}
            QComboBox:focus {{
                border-color: {self._colors['border_focus']};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self._colors['bg_primary']};
                color: {self._colors['text_primary']};
                selection-background-color: {self._colors['primary']};
                selection-color: {self._colors['text_light']};
            }}
        """
    
    def line_edit(self) -> str:
        """Style for line edit inputs."""
        return f"""
            QLineEdit {{
                padding: 8px;
                border: 2px solid {self._colors['border']};
                border-radius: 6px;
                background-color: {self._colors['bg_primary']};
                color: {self._colors['text_primary']};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {self._colors['border_focus']};
            }}
            QLineEdit:disabled {{
                background-color: {self._colors['bg_secondary']};
                color: {self._colors['text_secondary']};
            }}
        """
    
    def line_edit_dialog(self) -> str:
        """Style for line edit inputs in dialogs (thinner border)."""
        return f"""
            QLineEdit {{
                padding: 8px;
                border: 1px solid {self._colors['border']};
                border-radius: 4px;
                background-color: {self._colors['bg_primary']};
                color: {self._colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self._colors['border_focus']};
            }}
        """
    
    def search_input(self) -> str:
        """Style for search inputs."""
        return f"""
            QLineEdit {{
                border: 2px solid {self._colors['border']};
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
                background-color: {self._colors['bg_primary']};
                color: {self._colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self._colors['border_focus']};
            }}
        """
    
    def groupbox(self) -> str:
        """Style for group boxes."""
        return f"""
            QGroupBox {{
                font-size: 16px;
                font-weight: bold;
                color: {self._colors['text_primary']};
                border: 2px solid {self._colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 20px;
                background-color: {self._colors['bg_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                background-color: {self._colors['bg_primary']};
            }}
        """
    
    def list_widget(self) -> str:
        """Style for list widgets."""
        return f"""
            QListWidget {{
                background-color: {self._colors['bg_tertiary']};
                border: 2px solid {self._colors['border']};
                border-radius: 6px;
                padding: 5px;
                min-height: 150px;
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {self._colors['bg_secondary']};
            }}
            QListWidget::item:hover {{
                background-color: {self._colors['bg_secondary']};
            }}
        """
    
    def table(self) -> str:
        """Style for table widgets."""
        return f"""
            QTableWidget {{
                background-color: {self._colors['bg_primary']};
                alternate-background-color: {self._colors['table_alternate']};
                gridline-color: {self._colors['table_gridline']};
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {self._colors['text_primary']};
            }}
            QTableWidget::item:selected {{
                background-color: {self._colors['table_selection']};
                color: {self._colors['text_light']};
            }}
            QHeaderView::section {{
                background-color: {self._colors['table_header']};
                color: {self._colors['text_light']};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }}
        """
    
    def dialog(self) -> str:
        """Style for dialogs."""
        return f"""
            QDialog {{
                background-color: {self._colors['bg_secondary']};
            }}
            QLabel {{
                color: {self._colors['text_primary']};
                font-weight: bold;
            }}
        """
    
    def button(self, variant: str = "primary") -> str:
        """Style for buttons. Variants: primary, success, danger, gray, cancel."""
        colors = {
            "primary": (self._colors['primary'], self._colors['primary_hover']),
            "success": (self._colors['success'], self._colors['success_hover']),
            "danger": (self._colors['danger'], self._colors['danger_hover']),
            "gray": (self._colors['gray'], self._colors['gray_hover']),
            "cancel": (self._colors['gray'], self._colors['gray_hover']),
        }
        bg, hover = colors.get(variant, colors["primary"])
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {self._colors['text_light']};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """
    
    def button_icon(self, variant: str = "primary") -> str:
        """Style for icon buttons (emoji buttons in tables). Variants: edit, delete."""
        if variant == "delete":
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    padding: 5px;
                }}
                QPushButton:hover {{
                    background-color: {self._colors['danger']};
                    border-radius: 4px;
                }}
            """
        else:  # edit
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    font-size: 18px;
                    padding: 5px;
                }}
                QPushButton:hover {{
                    background-color: {self._colors['primary']};
                    border-radius: 4px;
                }}
            """
    
    def button_add(self) -> str:
        """Style for add/plus buttons."""
        return f"""
            QPushButton {{
                background-color: {self._colors['success_hover']};
                color: {self._colors['text_light']};
                border: none;
                border-radius: 6px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._colors['success']};
            }}
            QPushButton:pressed {{
                background-color: {self._colors['success_dark']};
            }}
        """
    
    def button_remove(self) -> str:
        """Style for remove/delete buttons in lists."""
        return f"""
            QPushButton {{
                background-color: {self._colors['danger']};
                color: {self._colors['text_light']};
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self._colors['danger_hover']};
            }}
        """
    
    def message_box_confirm(self) -> str:
        """Style for confirmation message boxes."""
        return f"""
            QMessageBox {{
                background-color: {self._colors['sidebar_bg']};
            }}
            QMessageBox QLabel {{
                color: {self._colors['text_light']};
                font-size: 14px;
                padding: 10px;
            }}
            QMessageBox QPushButton {{
                background-color: {self._colors['primary']};
                color: {self._colors['text_light']};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self._colors['primary_hover']};
            }}
        """
    
    def sidebar(self) -> str:
        """Style for sidebar."""
        return f"""
            background-color: {self._colors['sidebar_bg']};
        """
    
    def sidebar_title(self) -> str:
        """Style for sidebar title."""
        return f"""
            background-color: {self._colors['sidebar_title_bg']};
            color: {self._colors['text_light']};
            font-size: 24px;
            font-weight: bold;
            padding: 20px;
        """
    
    def sidebar_button(self) -> str:
        """Style for sidebar navigation buttons."""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self._colors['text_light']};
                border: none;
                padding: 15px 20px;
                text-align: left;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {self._colors['sidebar_hover']};
            }}
            QPushButton:checked {{
                background-color: {self._colors['sidebar_selected']};
                border-left: 4px solid {self._colors['primary']};
            }}
        """
    
    def content_area(self) -> str:
        """Style for main content area."""
        return f"""
            background-color: {self._colors['bg_secondary']};
        """
    
    def scroll_area(self) -> str:
        """Style for scroll areas."""
        return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """
    
    def label_item(self) -> str:
        """Style for item labels in lists."""
        return f"""
            color: {self._colors['text_primary']};
            font-size: 14px;
        """
