# modules/workout/session.py
from typing import List, Dict, Optional
import time

from modules.integrations.fitbit_client import FitbitClient
from core.db_operations import WorkoutDatabaseManager

class WorkoutSessionController:
    def __init__(self, workout_id: int):
        self.workout_id = workout_id
        self.start_time: Optional[float] = None
        self.is_active: bool = False
        
        # Mocked data (would eventually come from DB)
        self.exercises = [
            {"name": "Bench Press", "target_sets": 3, "target_reps": "4-6", "target_weight": 225.0},
            {"name": "Weighted Pull-Ups", "target_sets": 4, "target_reps": "4-6", "target_weight": 45.0},
            {"name": "Barbell OHP", "target_sets": 4, "target_reps": "4-6", "target_weight": 135.0}
        ]
        
        self.current_exercise_index = 0
        self.current_set = 1
        
        # State tracking
        self.session_logs = []

    def toggle_workout_state(self):
        """Starts, pauses, or resumes the workout state."""
        # If this is the very first time we are hitting start, lock in the start time
        if self.start_time is None:
            self.start_time = time.time()
            
        self.is_active = not self.is_active

    def get_current_exercise(self) -> Dict:
        """Returns the data for the exercise currently being performed."""
        if self.current_exercise_index < len(self.exercises):
            return self.exercises[self.current_exercise_index]
        return {}

    def log_set(self, reps: int, weight: float, rpe: float):
        """Records the set, checks progression, applies autoregulation, and advances state."""
        exercise = self.get_current_exercise()
        
        log_entry = {
            "exercise": exercise['name'],
            "set": self.current_set,
            "reps": reps,
            "weight": weight,
            "rpe": rpe,
            "timestamp": time.time()
        }
        self.session_logs.append(log_entry)
        
        # --- Intra-Workout Autoregulation ---
        target_str = str(exercise['target_reps'])
        min_target_reps = int(target_str.split('-')[0]) if '-' in target_str else int(target_str)
        
        if reps < min_target_reps:
            # Failed to hit minimum reps. Drop target weight by 10% for remaining sets.
            # Rounding to nearest 2.5 lbs for micro-plates.
            new_target = round((weight * 0.9) / 2.5) * 2.5
            exercise['target_weight'] = new_target
            print(f"Autoregulation triggered: Dropping weight to {new_target} lbs for remaining sets.")
        # ------------------------------------
        
        # Advance the state
        if self.current_set < exercise['target_sets']:
            self.current_set += 1
        else:
            self._advance_exercise()

    def _advance_exercise(self):
        """Moves to the next exercise or finishes the workout."""
        self.current_exercise_index += 1
        self.current_set = 1
        if self.current_exercise_index >= len(self.exercises):
            self.finish_workout()

    def finish_workout(self):
        """Concludes the workout, triggers Health API, and prepares database saving."""
        self.is_active = False
        end_time = time.time()
        
        duration_seconds = end_time - self.start_time if self.start_time else 0
        duration_minutes = int(duration_seconds // 60)
        
        print(f"\n--- Workout Finished in {duration_minutes} minutes ---")
        
        # --- 1. Health API Integration ---
        health_api = FitbitClient(client_id="YOUR_ID", client_secret="YOUR_SECRET")
        if health_api.authenticate():
            metrics = health_api.get_workout_metrics(self.start_time, end_time)
            print(f"Watch Synced! Avg HR: {metrics['avg_hr']} bpm, Calories: {metrics['calories']}")
        
        # --- 2. Save to Database ---
        try:
            # Assuming bodyweight is 185 for demo purposes
            workout_id = WorkoutDatabaseManager.save_completed_workout(
                workout_name="Day 1 - Upper", 
                duration_minutes=duration_minutes, 
                bodyweight=185.0, 
                logs=self.session_logs
            )
            print(f"Workout successfully saved to database (ID: {workout_id}).")
        except Exception as e:
            print(f"Failed to save workout: {e}")

    def load_template(self, template_id: int):
        """Replaces the mock data with live exercises from the selected template."""
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get exercises AND their muscle data
        cursor.execute('''
            SELECT r.exercise_name as name, r.target_sets, r.target_reps, r.target_weight, 
                   e.primary_muscle, e.secondary_muscles
            FROM routine_exercises r
            JOIN exercises e ON r.exercise_name = e.name
            WHERE r.template_id = ?
        ''', (template_id,))
        self.exercises = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        self.current_exercise_index = 0
        self.current_set = 1
        self.session_logs = []