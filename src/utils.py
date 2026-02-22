"""Shared UI utilities."""

from PySide6.QtWidgets import QMessageBox

from src.styles import theme


def show_warning(parent, title: str, text: str):
    """Show a styled warning message box."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet(theme.message_box_confirm())
    msg.exec()


def show_info(parent, title: str, text: str):
    """Show a styled information message box."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet(theme.message_box_confirm())
    msg.exec()


def show_critical(parent, title: str, text: str):
    """Show a styled critical error message box."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet(theme.message_box_confirm())
    msg.exec()
