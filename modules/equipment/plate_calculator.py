from core.db_operations import WorkoutDatabaseManager

class PlateCalculator:
    @staticmethod
    def calculate_loadout(target_weight: float) -> list:
        """Returns a list of plates needed PER SIDE, or None if impossible."""
        inv = WorkoutDatabaseManager.get_equipment_inventory()
        bar = inv['barbell']
        
        if target_weight < bar: return []
            
        per_side_target = (target_weight - bar) / 2.0
        loadout = []
        
        for plate in inv['plates']:
            if per_side_target >= plate:
                loadout.append(plate)
                per_side_target -= plate
                
        return loadout if per_side_target == 0 else None

    @staticmethod
    def get_closest_valid_weight(target_weight: float) -> float:
        """Finds the closest weight achievable with available inventory."""
        inv = WorkoutDatabaseManager.get_equipment_inventory()
        barbell = inv.get('barbell', 45.0)
        plates = inv.get('plates', [])
        
        if target_weight <= barbell:
            return barbell
            
        # Determine all possible weights (Barbell + pairs of available plates)
        possible_weights = {barbell}
        def find_combinations(index, current_weight):
            possible_weights.add(current_weight)
            for i in range(index, len(plates), 2): # Iterate by pairs
                find_combinations(i + 2, current_weight + (plates[i] * 2))
                
        find_combinations(0, barbell)
        
        # Return the achievable weight closest to the target
        return min(possible_weights, key=lambda x: abs(x - target_weight))

    @staticmethod
    def generate_warmup_sets(target_weight: float) -> list:
        """TASK 6: Generates equipment-aware warmup sets based on working weight."""
        inv = WorkoutDatabaseManager.get_equipment_inventory()
        bar = inv.get('barbell', 45.0)
        
        if target_weight <= bar:
            return [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar"}]
            
        warmups = [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar"}]
        
        # 50%, 70%, 90% logic
        progression = [(0.5, 8, "50%"), (0.7, 5, "70%"), (0.9, 3, "90%")]
        
        for percent, reps, label in progression:
            # Snap the calculation to the closest plate combination
            valid_weight = PlateCalculator.get_closest_valid_weight(target_weight * percent)
            
            # Prevent duplicate warm-up sets if the jumps are too small
            if valid_weight > bar and valid_weight not in [w['weight'] for w in warmups]:
                warmups.append({"reps": reps, "weight": valid_weight, "is_warmup": True, "label": label})
                
        return warmups