# core/events.py
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    # Signals
    data_changed = pyqtSignal()
    workout_completed = pyqtSignal()

# Global Singleton
event_bus = EventBus()