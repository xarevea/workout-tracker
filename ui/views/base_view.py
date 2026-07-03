# ui/views/base_view.py
from PyQt6.QtWidgets import QWidget
from core.events import event_bus

class BaseView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user_id = 1
        self.current_program_id = None
        
        # Correct PyQt6 syntax to connect slots to signals
        event_bus.USER_CHANGED.connect(self.on_user_changed)
        event_bus.PROGRAM_CHANGED.connect(self.on_program_changed)

    def on_user_changed(self, user_id: int):
        self.current_user_id = user_id
        self.refresh_data()

    def on_program_changed(self, program_id: int):
        self.current_program_id = program_id
        self.refresh_data()

    def refresh_data(self):
        """
        Abstract method to be overridden by child classes (Dashboard, etc.)
        to reload their specific charts and tables using the IDs above.
        """
        pass