# modules/progression/engine.py
from typing import List, Dict, Tuple

class ProgressionEngine:
    def __init__(self, weight_increment: float = 5.0):
        # Default jump is 5 lbs (2.5 lbs per side). 
        # For upper body/OHP, you might dynamically pass 2.5 lbs instead.
        self.weight_increment = weight_increment

    def evaluate_exercise_progression(
        self, 
        target_sets: int, 
        target_rep_range: Tuple[int, int], 
        current_weight: float, 
        completed_logs: List[Dict]
    ) -> Dict:
        """
        Analyzes a completed exercise and determines the target for the NEXT session.
        completed_logs format: [{'set': 1, 'reps': 6, 'weight': 225}, ...]
        """
        min_reps, max_reps = target_rep_range
        
        # Did they complete the required number of sets?
        if len(completed_logs) < target_sets:
            return self._maintain_status(current_weight, target_rep_range, "Incomplete sets. Keep current target.")

        all_sets_hit_max = True
        for log in completed_logs:
            if log['reps'] < max_reps:
                all_sets_hit_max = False
                break
            
        if all_sets_hit_max:
            # They maxed out the rep range on every set. Time to add weight!
            new_weight = current_weight + self.weight_increment
            return {
                "action": "INCREASE_WEIGHT",
                "new_weight": new_weight,
                "new_rep_range": target_rep_range, # Start back at the bottom of the rep range
                "message": f"Progression achieved! Increase weight to {new_weight} lbs."
            }
        else:
            # They are still building volume within the rep range
            return self._maintain_status(current_weight, target_rep_range, "Building volume. Try to add reps next time.")

    def _maintain_status(self, weight: float, rep_range: Tuple[int, int], message: str) -> Dict:
        return {
            "action": "MAINTAIN",
            "new_weight": weight,
            "new_rep_range": rep_range,
            "message": message
        }