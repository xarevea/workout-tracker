# modules/integrations/health_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Optional

class HealthProvider(ABC):
    """
    Abstract base class for all health wearable integrations.
    Ensures the main app doesn't care if you use Fitbit, Garmin, or Apple.
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Handles OAuth or token refreshing."""
        pass

    @abstractmethod
    def get_daily_readiness(self, date_str: str) -> Dict[str, any]:
        """
        Fetches daily metrics. 
        Returns dict like: {'sleep_score': 85, 'resting_hr': 55}
        """
        pass

    @abstractmethod
    def get_workout_metrics(self, start_timestamp: float, end_timestamp: float) -> Dict[str, any]:
        """
        Fetches specific data for the duration of a workout.
        Returns dict like: {'avg_hr': 140, 'max_hr': 175, 'calories': 450}
        """
        pass