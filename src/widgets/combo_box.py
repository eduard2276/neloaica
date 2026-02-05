"""Custom ComboBox widgets."""

from PySide6.QtWidgets import QComboBox


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events to allow page scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow page scrolling."""
        event.ignore()
