# modules/progression/engine.py
from modules.equipment.plate_calculator import PlateCalculator

class ProgressionEngine:
    def evaluate_exercise_progression(self, user_id: int, target_sets: int, min_reps: int, max_reps: int, current_weight: float, completed_logs: list) -> dict:
        working_sets = [log for log in completed_logs if not log.get('is_warmup', False)]
        if not working_sets:
            return self._maintain_status(current_weight, min_reps, max_reps)

        # 1. Find the best set (Highest e1RM based on RPE formula)
        # RIR = Reps in Reserve. e.g., RPE 8 = 2 RIR.
        best_e1rm = 0.0
        for log in working_sets:
            rir = 10.0 - log.get('rpe', 10.0)
            effective_reps = log['reps'] + rir
            e1rm = log['weight'] * (1 + (effective_reps / 30.0))
            if e1rm > best_e1rm: best_e1rm = e1rm

        # 2. Calculate ideal weight for the top end of the rep range
        ideal_target = best_e1rm / (1 + (max_reps / 30.0))
        
        # 3. Get achievable equipment weight for this user
        closest_valid = PlateCalculator.get_closest_valid_weight(ideal_target, user_id)

        # 4. Suggestion Logic
        if closest_valid >= current_weight + 2.5:
            return {
                "action": "INCREASE_WEIGHT (RPE Based)", 
                "new_weight": closest_valid, 
                "new_min": min_reps, 
                "new_max": max_reps
            }
        else:
            return self._maintain_status(current_weight, min_reps, max_reps)

    def _maintain_status(self, current_weight: float, min_reps: int, max_reps: int) -> dict:
        return {
            "action": "MAINTAIN", 
            "new_weight": current_weight, 
            "new_min": min_reps, 
            "new_max": max_reps
        }