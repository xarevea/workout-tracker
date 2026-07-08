from core.db_operations import WorkoutDatabaseManager

class PlateCalculator:
    @staticmethod
    def calculate_loadout(target_weight: float, user_id: int) -> list:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
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
    def get_closest_valid_weight(target_weight: float, user_id: int) -> float:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        barbell = inv.get('barbell', 45.0)
        plates = inv.get('plates', [])
        
        if target_weight <= barbell: return barbell
            
        possible_weights = {barbell}
        def find_combinations(index, current_weight):
            possible_weights.add(current_weight)
            for i in range(index, len(plates), 2): 
                find_combinations(i + 2, current_weight + (plates[i] * 2))
                
        find_combinations(0, barbell)
        return min(possible_weights, key=lambda x: abs(x - target_weight))

    @staticmethod
    def generate_warmup_sets(target_weight: float, user_id: int) -> list:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        bar = inv.get('barbell', 45.0)
        if target_weight <= bar:
            return [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar"}]
            
        warmups = [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar"}]
        progression = [(0.5, 8, "50%"), (0.7, 5, "70%"), (0.9, 3, "90%")]
        
        for percent, reps, label in progression:
            valid_weight = PlateCalculator.get_closest_valid_weight(target_weight * percent, user_id)
            if valid_weight > bar and valid_weight not in [w['weight'] for w in warmups]:
                warmups.append({"reps": reps, "weight": valid_weight, "is_warmup": True, "label": label})
        return warmups