from PyQt6.QtWidgets import QWidget

from core.events import event_bus

class BaseView(QWidget):
    """
    Base class for all main views in the stacked widget.
    Ensures a consistent interface for lifecycle events like data refreshing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Subscribe all inheriting views to context changes globally
        event_bus.subscribe('USER_CHANGED', self.on_user_changed)
        event_bus.subscribe('PROGRAM_CHANGED', self.on_program_changed)

    def on_user_changed(self, user_id: int):
        """
        Triggered when the global user dropdown changes.
        By default, triggers a generic data refresh. Override in child classes for specific logic.
        """
        self.current_user_id = user_id
        self.refresh_data()

    def on_program_changed(self, program_id: int):
        """
        Triggered when the global program dropdown changes.
        """
        self.current_program_id = program_id
        self.refresh_data()

    def refresh_data(self):
        """
        Called by MainWindow whenever the view is navigated to. 
        Override this method in subclasses to update UI elements 
        (dropdowns, tables, lists) with the latest database values.
        """
        pass  # Safe default: does nothing if the subclass doesn't need to refresh