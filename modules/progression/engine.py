from modules.equipment.plate_calculator import PlateCalculator

class ProgressionEngine:
    def evaluate_exercise_progression(self, target_sets: int, target_rep_range: tuple, current_weight: float, completed_logs: list) -> dict:
        min_reps, max_reps = target_rep_range
        successful_sets = [log for log in completed_logs if log['reps'] >= max_reps]
        
        if len(successful_sets) >= target_sets:
            ideal_new_weight = current_weight + 5.0
            # Fallback to reps if micro-plates are missing
            if PlateCalculator.calculate_loadout(ideal_new_weight) is not None:
                return {"action": "INCREASE_WEIGHT", "new_weight": ideal_new_weight, "new_reps": f"{min_reps}-{max_reps}"}
            else:
                return {"action": "INCREASE_REPS (Lacking Plates)", "new_weight": current_weight, "new_reps": f"{min_reps+1}-{max_reps+1}"}
        else:
            return {"action": "MAINTAIN", "new_weight": current_weight, "new_reps": f"{min_reps}-{max_reps}"}