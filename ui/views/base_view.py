# ui/views/base_view.py
from PyQt6.QtWidgets import QWidget
from core.events import event_bus

class BaseView(QWidget):
    """
    Base view that lazy-loads to prevent UI freezing. 
    It only queries the database when the tab is actually visible on screen.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user_id = 1
        self.current_program_id = None
        
        self._is_stale = True
        self._is_visible = False
        
        event_bus.USER_CHANGED.connect(self.on_user_changed)
        event_bus.PROGRAM_CHANGED.connect(self.on_program_changed)

    def on_user_changed(self, user_id: int):
        self.current_user_id = user_id
        self.mark_stale()

    def on_program_changed(self, program_id: int):
        self.current_program_id = program_id
        self.mark_stale()

    def mark_stale(self):
        self._is_stale = True
        if self._is_visible:
            self._do_refresh()

    def set_active_view(self, is_active: bool):
        self._is_visible = is_active
        if is_active and self._is_stale:
            self._do_refresh()

    def _do_refresh(self):
        self._is_stale = False
        self.refresh_data()

    def refresh_data(self):
        pass