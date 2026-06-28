# modules/progression/engine.py
from modules.equipment.plate_calculator import PlateCalculator

class ProgressionEngine:
    def evaluate_exercise_progression(self, target_sets: int, min_reps: int, max_reps: int, current_weight: float, completed_logs: list) -> dict:
        # Filter out warmups
        working_sets = [log for log in completed_logs if not log.get('is_warmup', False)]
        successful_sets = [log for log in working_sets if log['reps'] >= max_reps]
        
        if len(successful_sets) >= target_sets:
            return self._calculate_progression(current_weight, min_reps, max_reps)
        else:
            return self._maintain_status(current_weight, min_reps, max_reps)

    def _calculate_progression(self, current_weight: float, min_reps: int, max_reps: int) -> dict:
        ideal_new_weight = current_weight + 5.0
        # Equipment Check
        if PlateCalculator.calculate_loadout(ideal_new_weight) is not None:
            return {
                "action": "INCREASE_WEIGHT", 
                "new_weight": ideal_new_weight, 
                "new_min": min_reps, 
                "new_max": max_reps
            }
        else:
            # Fallback to rep progression if micro-plates are missing
            return {
                "action": "INCREASE_REPS (Lacking Plates)", 
                "new_weight": current_weight, 
                "new_min": min_reps + 1, 
                "new_max": max_reps + 1
            }

    def _maintain_status(self, current_weight: float, min_reps: int, max_reps: int) -> dict:
        return {
            "action": "MAINTAIN", 
            "new_weight": current_weight, 
            "new_min": min_reps, 
            "new_max": max_reps
        }