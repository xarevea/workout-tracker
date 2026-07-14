from core.db_operations import WorkoutDatabaseManager

class PlateCalculator:
    @staticmethod
    def calculate_loadout(target_weight: float, user_id: int, is_barbell: bool = True, current_side_loadout: list = None) -> tuple:
        """Returns a tuple of two lists: (left_plates, right_plates), optimized for fewest plate changes."""
        if current_side_loadout is None:
            current_side_loadout = []

        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)

        if is_barbell:
            bar = inv.get('barbell', 45.0)
            if target_weight <= bar: return ([], [])

            target_per_side = round((target_weight - bar) / 2.0, 2)
            plates = inv.get('paired_plates', [])

            # Helper to calculate the "cost" of changing the bar (adds + removals)
            def get_cost(candidate_loadout):
                c = list(current_side_loadout)
                adds = 0
                for p in candidate_loadout:
                    if p in c: c.remove(p)
                    else: adds += 1
                return adds + len(c)

            # DP Subset Sum
            memo = {0.0: []}
            for p in plates:
                new_memo = {}
                for current_sum, used_plates in memo.items():
                    new_sum = round(current_sum + p, 2)
                    if new_sum <= target_per_side:
                        cand = used_plates + [p]
                        if new_sum not in memo:
                            new_memo[new_sum] = cand
                        else:
                            # If weight is achievable multiple ways, pick the one with the least plate swapping!
                            cost_new = get_cost(cand)
                            cost_old = get_cost(memo[new_sum])
                            if cost_new < cost_old or (cost_new == cost_old and len(cand) < len(memo[new_sum])):
                                new_memo[new_sum] = cand
                memo.update(new_memo)

            if target_per_side not in memo:
                return None

            side_loadout = sorted(memo[target_per_side], reverse=True)
            return (side_loadout, side_loadout)

        else:
            # Non-barbell logic
            plates = inv.get('plates', [])
            target = round(target_weight, 2)
            if target <= 0: return ([], [])

            def get_cost_center(candidate_loadout):
                c = list(current_side_loadout)
                adds = 0
                for p in candidate_loadout:
                    if p in c: c.remove(p)
                    else: adds += 1
                return adds + len(c)

            memo = {0.0: []}
            for p in plates:
                new_memo = {}
                for current_sum, used_plates in memo.items():
                    new_sum = round(current_sum + p, 2)
                    if new_sum <= target:
                        cand = used_plates + [p]
                        if new_sum not in memo:
                            new_memo[new_sum] = cand
                        else:
                            cost_new = get_cost_center(cand)
                            cost_old = get_cost_center(memo[new_sum])
                            if cost_new < cost_old or (cost_new == cost_old and len(cand) < len(memo[new_sum])):
                                new_memo[new_sum] = cand
                memo.update(new_memo)

            if target not in memo: return None
            center_loadout = sorted(memo[target], reverse=True)
            return ([], center_loadout)

    @staticmethod
    def get_closest_valid_weight(target_weight: float, user_id: int, is_barbell: bool = True) -> float:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        if is_barbell:
            barbell = inv.get('barbell', 45.0)
            plates = inv.get('paired_plates', [])
            if target_weight <= barbell: return barbell

            possible_sums = {0.0}
            max_useful = (target_weight - barbell)/2.0 + 100
            for plate in plates:
                new_sums = {round(s + plate, 2) for s in possible_sums if s <= max_useful}
                possible_sums.update(new_sums)

            possible_weights = {round(barbell + (s * 2), 2) for s in possible_sums}
            return min(possible_weights, key=lambda x: abs(x - target_weight))
        else:
            plates = inv.get('plates', [])
            if target_weight <= 0: return 0.0

            possible_sums = {0.0}
            max_useful = target_weight + 100
            for plate in plates:
                new_sums = {round(s + plate, 2) for s in possible_sums if s <= max_useful}
                possible_sums.update(new_sums)
            return min(possible_sums, key=lambda x: abs(x - target_weight))

    @staticmethod
    def generate_warmup_sets(target_weight: float, user_id: int, is_barbell: bool = True) -> list:
        inv = WorkoutDatabaseManager.get_equipment_inventory(user_id)
        bar = inv.get('barbell', 45.0) if is_barbell else 0.0

        if target_weight <= bar:
            return [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar" if is_barbell else "Bodyweight"}]

        warmups = [{"reps": 10, "weight": bar, "is_warmup": True, "label": "Empty Bar" if is_barbell else "Bodyweight"}]
        progression = [(0.5, 8, "50%"), (0.7, 5, "70%"), (0.9, 3, "90%")]

        for percent, reps, label in progression:
            valid_weight = PlateCalculator.get_closest_valid_weight(target_weight * percent, user_id, is_barbell)
            if valid_weight > bar and valid_weight not in [w['weight'] for w in warmups]:
                warmups.append({"reps": reps, "weight": valid_weight, "is_warmup": True, "label": label})
        return warmups