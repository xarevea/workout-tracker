# modules/workout/session.py
import time
from typing import Dict, Optional
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSlot

from core.db_operations import WorkoutDatabaseManager
from modules.integrations.fitbit_client import FitbitClient
from core.database import get_connection
from core.events import event_bus

class FitbitSyncWorker(QRunnable):
    def __init__(self, workout_id, duration):
        super().__init__()
        self.workout_id = workout_id
        self.duration = duration
        self.client = FitbitClient(client_id="mock", client_secret="mock")

    @pyqtSlot()
    def run(self):
        try:
            # Silently exit if Fitbit is not actually hooked up
            # Uncomment authentication check when API is ready
            if not self.client.authenticate(): return
            
            metrics = self.client.get_workout_metrics(self.duration, time.time())
            if metrics:
                event_bus.FITBIT_SYNC_SUCCESS.emit({'id': self.workout_id, 'metrics': metrics})
        except Exception as e:
            # Handle gracefully without disrupting app
            print(f"Fitbit Sync Skipped: API not configured ({str(e)})")
            pass

class WorkoutSessionController:
    def __init__(self):
        self.workout_id = None
        self.current_user_id = 1
        self.current_program_id = None
        self.is_active = False
        self.start_time = 0
        self.current_exercise_index = 0
        self.current_set = 1
        self.exercises = []
        self.session_logs = []
        self.template_name = ""

        event_bus.USER_CHANGED.connect(self._update_active_user)
        event_bus.PROGRAM_CHANGED.connect(self._update_active_program)

    def _update_active_user(self, user_id: int):
        self.current_user_id = user_id

    def _update_active_program(self, program_id: int):
        self.current_program_id = program_id

    def undo_last_set(self) -> bool:
        """Safely rewinds state by recalculating position from remaining logs."""
        if not self.session_logs:
            return False 
            
        self.session_logs.pop()
        
        # Rebuild state machine completely based on remaining valid logs
        self.current_exercise_index = 0
        self.current_set = 1
        
        for log in self.session_logs:
            if not log.get('is_warmup', False):
                if self.current_exercise_index < len(self.exercises):
                    ex = self.exercises[self.current_exercise_index]
                    if self.current_set < ex['target_sets']:
                        self.current_set += 1
                    else:
                        self.current_exercise_index += 1
                        self.current_set = 1
                        
        return True

    def load_template(self, template_id: int):
        self.exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        self.workout_id = template_id
        self.current_exercise_index = 0
        self.current_set = 1
        self.session_logs = []
        self.is_active = False

    def toggle_workout_state(self):
        if self.start_time is None or self.start_time == 0: self.start_time = time.time()
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
            "is_warmup": is_warmup,
            "target_hit": reps >= exercise['target_reps_min'] if not is_warmup else True
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
        if not self.session_logs: return None
        self.is_active = False
        duration_minutes = int((time.time() - self.start_time) / 60.0) if self.start_time else 0
        return {"duration_minutes": duration_minutes, "logs": self.session_logs}