# modules/workout/session.py
import time
from typing import Dict, Optional
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSlot

from core.db_operations import WorkoutDatabaseManager
from modules.integrations.fitbit_client import FitbitClient
from core.database import get_connection
from core.events import event_bus

class FitbitSyncWorker(QRunnable):
    """Background task to fetch Fitbit API data without freezing GUI."""
    def __init__(self, workout_id, duration):
        super().__init__()
        self.workout_id = workout_id
        self.duration = duration
        self.client = FitbitClient()

    @pyqtSlot()
    def run(self):
        try:
            metrics = self.client.get_workout_metrics(self.duration)
            if metrics:
                event_bus.FITBIT_SYNC_SUCCESS.emit({'id': self.workout_id, 'metrics': metrics})
            else:
                event_bus.FITBIT_SYNC_FAILED.emit("No metrics returned.")
        except Exception as e:
            event_bus.FITBIT_SYNC_FAILED.emit(str(e))

class WorkoutSessionController:
    def __init__(self):
        self.workout_id = None
        self.current_user_id = 1
        self.is_active = False
        self.start_time = 0
        self.current_exercise_index = 0
        self.current_set = 1
        self.exercises = []
        self.session_logs = []
        self.template_name = ""

        event_bus.USER_CHANGED.connect(self._update_active_user)

    def _update_active_user(self, user_id: int):
        """Keeps the session controller aware of the active user."""
        self.current_user_id = user_id

    def undo_last_set(self) -> bool:
        """TASK 1: Pops the last log and safely rewinds the session state."""
        if not self.session_logs:
            return False # Nothing to undo
            
        last_log = self.session_logs.pop()
        
        # Step back the set counter
        if self.current_set > 1:
            self.current_set -= 1
        else:
            # If we were on set 1, we need to revert to the previous exercise entirely
            if self.current_exercise_index > 0:
                self.current_exercise_index -= 1
                prev_ex_name = self.exercises[self.current_exercise_index]['name']
                # Count how many logs belong to the previous exercise to set the proper set number
                prev_logs = [log for log in self.session_logs if log['exercise'] == prev_ex_name]
                self.current_set = len(prev_logs) + 1
        return True

    def load_template(self, template_id: int):
        self.exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        self.workout_id = template_id
        self.current_exercise_index = 0
        self.current_set = 1
        self.session_logs = []
        self.is_active = False

    def toggle_workout_state(self):
        if self.start_time is None: self.start_time = time.time()
        self.is_active = not self.is_active

    def get_current_exercise(self) -> Dict:
        if self.current_exercise_index < len(self.exercises): return self.exercises[self.current_exercise_index]
        return {}

    def log_set(self, reps: int, weight: float, rpe: float, is_warmup: bool = False):
        exercise = self.get_current_exercise()
        log_entry = {
            "exercise": exercise['name'],
            "set": self.current_set if not is_warmup else "W",
            "reps": reps,
            "weight": weight,
            "rpe": rpe,
            "timestamp": time.time(),
            "is_warmup": is_warmup
        }
        self.session_logs.append(log_entry)
        
        if not is_warmup:
            if reps < exercise['target_reps_min']:
                new_target = round((weight * 0.9) / 2.5) * 2.5
                exercise['target_weight'] = new_target
            
            if self.current_set < exercise['target_sets']:
                self.current_set += 1
            else:
                self._advance_exercise()

    def _advance_exercise(self):
        self.current_exercise_index += 1
        self.current_set = 1

    def finish_workout(self) -> dict:
        if not self.session_logs:
            return None
            
        self.is_active = False
        duration_minutes = int((time.time() - self.start_time) / 60.0)
        
        # Use the class-tracked current_user_id to save to DB
        self.workout_id = WorkoutDatabaseManager.create_workout(
            user_id=self.current_user_id, 
            name=self.template_name, 
            duration=duration_minutes
        )
        
        for log in self.session_logs:
            WorkoutDatabaseManager.log_set(
                workout_id=self.workout_id,
                exercise_name=log['exercise'],
                set_number=log['set_number'],
                reps=log['reps'],
                weight=log['weight'],
                rpe=log['rpe'],
                target_hit=log['target_hit'],
                is_warmup=log.get('is_warmup', False)
            )

        # Offload network API to thread
        worker = FitbitSyncWorker(self.workout_id, duration_minutes)
        QThreadPool.globalInstance().start(worker)
        
        # Fire signal to prompt Review Dialog
        event_bus.WORKOUT_COMPLETED.emit(self.workout_id)
        
        return self.workout_id