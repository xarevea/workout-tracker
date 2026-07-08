# ========================================
# FILE PATH: utils/threads.py
# ========================================
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot
import traceback

class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    result = pyqtSignal(object)
    error = pyqtSignal(tuple)
    finished = pyqtSignal()

class Worker(QRunnable):
    """
    Reusable Threading Worker.
    Pass in any function and its arguments to run it in the background.
    """
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit((e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()