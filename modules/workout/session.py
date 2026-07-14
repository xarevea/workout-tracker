# modules/workout/session.py
import time
from collections import defaultdict
from typing import Dict, Optional
from PyQt6.QtCore import QRunnable, QThreadPool, pyqtSlot

from core.db_operations import WorkoutDatabaseManager
from core.events import event_bus
from core.models import ExerciseMode
from modules.integrations.fitbit_client import FitbitClient

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

        self.exercises = []
        self.queue = []
        self.queue_index = 0

        self.session_logs = []
        self.template_name = ""

        event_bus.USER_CHANGED.connect(self._update_active_user)
        event_bus.PROGRAM_CHANGED.connect(self._update_active_program)

    def _update_active_user(self, user_id: int):
        self.current_user_id = user_id

    def _update_active_program(self, program_id: int):
        self.current_program_id = program_id

    def undo_last_set(self) -> bool:
        if not self.session_logs: return False

        last_log = self.session_logs.pop()
        if not last_log.get('is_warmup', False):
            self.queue_index = max(0, self.queue_index - 1)

        return True

    def load_template(self, template_id: int):
        self.exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        self.workout_id = template_id

        # Build the Unrolled Queue
        self.queue = []
        groups = defaultdict(list)

        # Group exercises (Standard goes in their own unique group, Circuits share groups)
        for i, ex in enumerate(self.exercises):
            mode = ex.get('mode', 'Standard')
            if mode == ExerciseMode.STANDARD:
                groups[f"Std_{i}"].append(ex)
            else:
                groups[f"{mode.name}_{ex.get('circuit_group', 0)}"].append(ex)

        for gid, group_exs in groups.items():
            mode = group_exs[0].get('mode', ExerciseMode.STANDARD)
            max_sets = max([ex['target_sets'] for ex in group_exs])

            if mode in [ExerciseMode.CIRCUIT, ExerciseMode.EMOM]:
                for set_idx in range(1, max_sets + 1):
                    for ex in group_exs:
                        if set_idx <= ex['target_sets']:
                            self.queue.append({
                                'exercise': ex,
                                'set_number': set_idx,
                                'is_emom': mode == ExerciseMode.EMOM
                            })
            else:
                # Sequential sets
                for ex in group_exs:
                    for set_idx in range(1, ex['target_sets'] + 1):
                        self.queue.append({'exercise': ex, 'set_number': set_idx, 'is_emom': False})

        self.queue_index = 0
        self.session_logs = []
        self.is_active = False

    def toggle_workout_state(self):
        if self.start_time is None or self.start_time == 0: self.start_time = time.time()
        self.is_active = not self.is_active

    def get_current_task(self) -> Dict:
        """Returns the current queue item containing the exercise and set number."""
        if self.queue_index < len(self.queue):
            return self.queue[self.queue_index]
        return {}

    def get_current_exercise(self) -> Dict:
        task = self.get_current_task()
        return task.get('exercise', {})

    def log_set(self, reps: int, weight: float, rpe: float, is_warmup: bool = False):
        task = self.get_current_task()
        exercise = task['exercise']

        log_entry = {
            "exercise": exercise['name'],
            "set": task['set_number'] if not is_warmup else "W",
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

            self.queue_index += 1

    def finish_workout(self) -> dict:
        if not self.session_logs: return None
        self.is_active = False
        duration_minutes = int((time.time() - self.start_time) / 60.0) if self.start_time else 0
        return {"duration_minutes": duration_minutes, "logs": self.session_logs}