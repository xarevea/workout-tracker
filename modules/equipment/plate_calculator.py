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
                
        if per_side_target > 0: return None 
        return loadout