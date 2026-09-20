"""
Clean ValidatorStrategy abstract base interface and input context.
Enables pluggable insertion, backtesting, and auditing of research methodologies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .models import HistoricalMarketObservation, TimestampedObservation, ValidatorPrediction, InputWindow


class InputContext(BaseModel):
    """
    Standard input context passed to a validator strategy.
    Contains strictly historical observations up to current_ts.
    Enforces no future-data leakage.
    """
    validator_id: str
    current_ts: int
    target_horizon_seconds: int = 3600  # Default 1 hour
    history: List[HistoricalMarketObservation]
    seed: int = 42
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def target_ts(self) -> int:
        return self.current_ts + self.target_horizon_seconds

    @property
    def latest_observation(self) -> Optional[HistoricalMarketObservation]:
        return self.history[-1] if self.history else None

    def get_input_window(self) -> InputWindow:
        if not self.history:
            return InputWindow(
                start_ts=self.current_ts,
                end_ts=self.current_ts,
                observation_count=0,
                sampling_interval_sec=0
            )
        start_ts = self.history[0].timestamp
        end_ts = self.history[-1].timestamp
        step = (end_ts - start_ts) // max(len(self.history) - 1, 1) if len(self.history) > 1 else 60
        return InputWindow(
            start_ts=start_ts,
            end_ts=end_ts,
            observation_count=len(self.history),
            sampling_interval_sec=max(int(step), 1)
        )


class ValidatorStrategy(ABC):
    """
    Abstract Base Class for all independent forecasting methodologies.
    Every research candidate (ARIMA, EWMA, GARCH, Order-Book depth, etc.)
    must implement this contract.
    """

    @property
    @abstractmethod
    def method_id(self) -> str:
        """Unique machine identifier for this methodology."""
        pass

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Methodology code version or parameter hash."""
        pass

    @property
    @abstractmethod
    def source_provenance(self) -> List[str]:
        """Underlying data feeds or sources assumed by this strategy."""
        pass

    @property
    def assumptions(self) -> List[str]:
        """Key mathematical or operational assumptions made by this methodology."""
        return []

    @property
    def limitations(self) -> List[str]:
        """Known failure modes or boundaries of validity."""
        return []

    @abstractmethod
    def predict(self, context: InputContext) -> ValidatorPrediction:
        """
        Produce a point forecast and uncertainty bounds for context.target_ts.
        Must strictly consume observations where timestamp <= context.current_ts.
        """
        pass
