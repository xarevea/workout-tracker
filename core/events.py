# core/events.py
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    # Original Signals
    data_changed = pyqtSignal()
    
    # New Context Switching Signals (Passes an integer ID)
    USER_CHANGED = pyqtSignal(int)
    PROGRAM_CHANGED = pyqtSignal(int)
    
    # New Workout & Integration Signals
    WORKOUT_COMPLETED = pyqtSignal(int, list) 
    FITBIT_SYNC_SUCCESS = pyqtSignal(int, dict)
    FITBIT_SYNC_FAILED = pyqtSignal(int, str)

# Global Singleton
event_bus = EventBus()