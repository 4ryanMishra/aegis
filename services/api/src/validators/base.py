"""
Pluggable Validator Strategy Base Interface.
Rule #6: Do not hard-code research methodologies before research team approves.
Rule #7: Every method must expose methodology name, input window, output estimate, uncertainty/confidence.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models.schema import ValidatorObservation, DataStatus


class ReferenceContext(BaseModel):
    """Context provided to a validator strategy during a verification window."""
    asset: str
    p_osm: float
    window_start_ts: int
    current_ts: int
    expected_market_hint: Optional[float] = None
    seed: int = 42
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidatorStrategy(ABC):
    """Abstract base class for all independent validator forecasting strategies."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique machine identifier for this strategy."""
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy implementation version / hash."""
        pass

    @property
    @abstractmethod
    def default_source_ids(self) -> List[str]:
        """Data sources this strategy relies on."""
        pass

    @abstractmethod
    def generate(self, validator_id: str, context: ReferenceContext) -> ValidatorObservation:
        """
        Produce a deterministic validator observation for the given context.
        Must return a valid ValidatorObservation.
        """
        pass
