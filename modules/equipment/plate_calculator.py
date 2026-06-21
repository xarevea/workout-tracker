# modules/equipment/plate_calculator.py
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class CalculationResult:
    target_weight: float
    actual_weight: float
    plates_per_side: List[float]
    weight_difference: float  # Negative means actual is lower than target
    needs_rep_adjustment: bool

class PlateCalculator:
    def __init__(self, barbell_weight: float = 45.0, inventory: Optional[Dict[float, int]] = None):
        """
        :param inventory: Dictionary mapping plate weight to total available quantity.
                          e.g., {45.0: 6, 25.0: 2, 10.0: 4, 5.0: 2}
        """
        self.barbell_weight = barbell_weight
        # Default fallback inventory if none provided from DB
        self.inventory = inventory or {
            45.0: 6, 35.0: 2, 25.0: 2, 
            10.0: 4, 5.0: 2, 2.5: 2
        }
        
    def calculate_load(self, target_weight: float) -> CalculationResult:
        """Calculates the best plate distribution for a target weight."""
        if target_weight <= self.barbell_weight:
            return CalculationResult(
                target_weight=target_weight,
                actual_weight=self.barbell_weight,
                plates_per_side=[],
                weight_difference=self.barbell_weight - target_weight,
                needs_rep_adjustment=(self.barbell_weight != target_weight)
            )

        weight_to_add_per_side = (target_weight - self.barbell_weight) / 2.0
        plates_per_side: List[float] = []
        
        # Sort available plates descending
        available_plates = sorted(self.inventory.keys(), reverse=True)
        temp_inventory = self.inventory.copy()

        for plate in available_plates:
            # We need pairs (1 for each side)
            while weight_to_add_per_side >= plate and temp_inventory[plate] >= 2:
                plates_per_side.append(plate)
                weight_to_add_per_side -= plate
                temp_inventory[plate] -= 2

        actual_weight = self.barbell_weight + (sum(plates_per_side) * 2)
        weight_difference = actual_weight - target_weight
        
        return CalculationResult(
            target_weight=target_weight,
            actual_weight=actual_weight,
            plates_per_side=plates_per_side,
            weight_difference=weight_difference,
            needs_rep_adjustment=abs(weight_difference) > 0.01
        )