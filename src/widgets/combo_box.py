"""Custom widgets that ignore wheel events."""

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events to allow page scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow page scrolling."""
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores wheel events to allow page scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow page scrolling."""
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores wheel events to allow page scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow page scrolling."""
        event.ignore()
