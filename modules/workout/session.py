import time
from collections import defaultdict
from typing import Dict
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
            if not self.client.authenticate(): return
            metrics = self.client.get_workout_metrics(self.duration, time.time())
            if metrics:
                event_bus.FITBIT_SYNC_SUCCESS.emit({'id': self.workout_id, 'metrics': metrics})
        except Exception as e:
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

        # Pull the log
        self.session_logs.pop()

        # Step back the queue
        self.queue_index = max(0, self.queue_index - 1)
        return True

    def skip_current_set(self):
        if self.queue_index < len(self.queue):
            self.queue_index += 1

    def load_template(self, template_id: int):
        self.exercises = WorkoutDatabaseManager.get_routine_exercises(template_id)
        self.workout_id = template_id

        self.queue = []
        groups = defaultdict(list)

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
                                'is_emom': mode == ExerciseMode.EMOM,
                                'is_warmup': False,
                                'target_weight': ex['target_weight'],
                                'target_reps': ex['target_reps_max']
                            })
            else:
                for ex in group_exs:
                    for set_idx in range(1, ex['target_sets'] + 1):
                        self.queue.append({
                            'exercise': ex,
                            'set_number': set_idx,
                            'is_emom': False,
                            'is_warmup': False,
                            'target_weight': ex['target_weight'],
                            'target_reps': ex['target_reps_max']
                        })

        self.queue_index = 0
        self.session_logs = []
        self.is_active = False

    def insert_warmups(self, warmups_list):
        """Injects generated warmups directly into the queue so they can be tracked properly."""
        task = self.get_current_task()
        if not task: return
        ex = task['exercise']

        new_tasks = []
        for i, w in enumerate(warmups_list):
            new_tasks.append({
                'exercise': ex,
                'set_number': f"W{i+1}",
                'is_emom': False,
                'is_warmup': True,
                'target_weight': w['weight'],
                'target_reps': w['reps']
            })

        self.queue = self.queue[:self.queue_index] + new_tasks + self.queue[self.queue_index:]

    def toggle_workout_state(self):
        if self.start_time is None or self.start_time == 0: self.start_time = time.time()
        self.is_active = not self.is_active

    def get_current_task(self) -> Dict:
        if self.queue_index < len(self.queue):
            return self.queue[self.queue_index]
        return {}

    def get_current_exercise(self) -> Dict:
        task = self.get_current_task()
        return task.get('exercise', {})

    def log_set(self, reps: int, weight: float, rpe: float, is_warmup: bool = False, notes: str = ""):
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
            "target_hit": reps >= exercise['target_reps_min'] if not is_warmup else True,
            "notes": notes
        }
        self.session_logs.append(log_entry)

        if not is_warmup:
            if reps < exercise['target_reps_min']:
                new_target = round((weight * 0.9) / 2.5) * 2.5
                exercise['target_weight'] = new_target

        self.queue_index += 1

    def finish_workout(self) -> dict:
        self.is_active = False
        duration_minutes = int((time.time() - self.start_time) / 60.0) if self.start_time else 0
        return {"duration_minutes": duration_minutes, "logs": self.session_logs}