# modules/workout/session.py
import time
from typing import Dict, Optional
from core.db_operations import WorkoutDatabaseManager
from modules.integrations.fitbit_client import FitbitClient
from core.database import get_connection

class WorkoutSessionController:
    def __init__(self):
        self.workout_id = None
        self.start_time: Optional[float] = None
        self.is_active: bool = False
        self.exercises = []
        self.current_exercise_index = 0
        self.current_set = 1
        self.session_logs = []

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
        self.is_active = False
        duration_minutes = int((time.time() - self.start_time) // 60) if self.start_time else 0
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_token, refresh_token FROM api_integrations WHERE provider_name='Fitbit'")
        api_keys = cursor.fetchone()
        conn.close()

        if api_keys and api_keys['access_token']:
            try:
                health_api = FitbitClient(client_id=api_keys['access_token'], client_secret=api_keys['refresh_token'])
                if health_api.authenticate():
                    metrics = health_api.get_workout_metrics(self.start_time, time.time())
                    print(f"Fitbit Synced! Avg HR: {metrics['avg_hr']} bpm, Calories: {metrics['calories']}")
            except Exception as e:
                print(f"Fitbit API Error: {e}")

        return {"duration_minutes": duration_minutes, "logs": self.session_logs}