from modules.equipment.plate_calculator import PlateCalculator

class ProgressionEngine:
    def evaluate_exercise_progression(self, user_id: int, target_sets: int, min_reps: int, max_reps: int, current_weight: float, completed_logs: list, is_barbell: bool = True) -> dict:
        working_sets = [log for log in completed_logs if not log.get('is_warmup', False)]
        if not working_sets:
            return self._maintain_status(current_weight, min_reps, max_reps)

        # 1. Find the best set (Highest theoretical impact)
        best_log = max(working_sets, key=lambda l: l['reps'] + (10.0 - l.get('rpe', 10.0)))
        best_reps = best_log['reps']
        best_rpe = best_log.get('rpe', 10.0)

        # 2. DOUBLE PROGRESSION LOGIC

        # Scenario A: Maxed out the rep range easily (RPE 9 or under)
        if best_reps >= max_reps and best_rpe <= 9.0:
            ideal_target = current_weight * 1.05 if current_weight > 0 else 0 # Suggest 5% bump
            if ideal_target > 0:
                closest_valid = PlateCalculator.get_closest_valid_weight(ideal_target, user_id, is_barbell)
                if closest_valid > current_weight:
                    return {
                        "action": "INCREASE WEIGHT",
                        "new_weight": closest_valid,
                        "new_min": min_reps,
                        "new_max": max_reps
                    }

        # Scenario B: Middle of the rep range -> Suggest increasing Reps before Weight
        if best_reps >= min_reps and best_reps < max_reps:
            return {
                "action": f"INCREASE REPS (Target: {best_reps + 1})",
                "new_weight": current_weight,
                "new_min": best_reps + 1, # Seeds the UI to lock in the progression target
                "new_max": max_reps
            }

        # Scenario C: Didn't hit minimum reps (Struggling) -> Recommend maintaining or dropping
        if best_reps < min_reps:
            return {
                "action": "MAINTAIN / DELOAD (Missed Min Reps)",
                "new_weight": current_weight,
                "new_min": min_reps,
                "new_max": max_reps
            }

        return self._maintain_status(current_weight, min_reps, max_reps)

    def _maintain_status(self, current_weight: float, min_reps: int, max_reps: int) -> dict:
        return {
            "action": "MAINTAIN",
            "new_weight": current_weight,
            "new_min": min_reps,
            "new_max": max_reps
        }