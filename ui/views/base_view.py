# ui/views/base_view.py
from PyQt6.QtWidgets import QWidget

class BaseView(QWidget):
    """
    Base class for all main views in the stacked widget.
    Ensures a consistent interface for lifecycle events like data refreshing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def refresh_data(self):
        """
        Called by MainWindow whenever the view is navigated to. 
        Override this method in subclasses to update UI elements 
        (dropdowns, tables, lists) with the latest database values.
        """
        pass  # Safe default: does nothing if the subclass doesn't need to refresh