from core.db_operations import WorkoutDatabaseManager

class PlateCalculator:
    @staticmethod
    def calculate_loadout(target_weight: float, user_id: int) -> tuple:
        """Returns a tuple of two lists: (left_plates, right_plates)"""
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        bar = inv.get('barbell', 45.0)
        if target_weight <= bar: return ([], [])

        target_plate_weight = round(target_weight - bar, 2)
        plates = inv.get('plates', [])

        # Subset Sum logic to find the exact combination
        memo = {0.0: []}
        for p in plates:
            new_memo = {}
            for current_sum, used_plates in memo.items():
                new_sum = round(current_sum + p, 2)
                # Cap search to prevent memory bloat
                if new_sum <= target_plate_weight:
                    if new_sum not in memo or len(used_plates) + 1 < len(memo.get(new_sum, [])):
                        new_memo[new_sum] = used_plates + [p]
            memo.update(new_memo)

        if target_plate_weight not in memo:
            return None

        # Distribute the selected plates to left and right sides as evenly as possible
        selected_plates = sorted(memo[target_plate_weight], reverse=True)
        left, right = [], []
        sum_left, sum_right = 0.0, 0.0

        for p in selected_plates:
            if sum_left <= sum_right:
                left.append(p)
                sum_left += p
            else:
                right.append(p)
                sum_right += p

        return (left, right)

    @staticmethod
    def get_closest_valid_weight(target_weight: float, user_id: int) -> float:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        barbell = inv.get('barbell', 45.0)
        plates = inv.get('plates', [])

        if target_weight <= barbell: return barbell

        possible_sums = {0.0}
        max_useful = target_weight - barbell + 100

        for plate in plates:
            new_sums = {round(s + plate, 2) for s in possible_sums if s <= max_useful}
            possible_sums.update(new_sums)

        possible_weights = {barbell + s for s in possible_sums}
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