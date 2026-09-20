"""
Pluggable Validator Strategy Base Interface (Phase 4A).
Defines the canonical methodology interface for independent validator nodes.

Decouples:
- methodology: quantitative algorithm (Lane 1-5)
- validator_id: logical node identity
- operator_id: independent entity operating the node
- lane_id: 1..5
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..models.schema import ValidatorResult, DataStatus


class ReferenceContext(BaseModel):
    """Context provided to a validator strategy during a verification window."""
    asset: str
    p_osm: float
    window_start_ts: int
    current_ts: int
    expected_market_hint: Optional[float] = None
    anchor_price: Optional[float] = None
    is_rwa: bool = True
    history_prices: Optional[List[float]] = None
    peer_estimates: Optional[List[Dict[str, Any]]] = None
    scenario_type: str = "NORMAL"
    adversarial_node_id: Optional[str] = None
    seed: int = 42
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidatorStrategy(ABC):
    """Abstract base class for all independent validator methodology lanes."""

    @property
    @abstractmethod
    def lane_id(self) -> int:
        """Methodology lane number (1-5)."""
        pass

    @property
    @abstractmethod
    def methodology(self) -> str:
        """Machine identifier (e.g. KALMAN_1D, HUBER_IRLS, JSD, OU_RESIDUAL, CUSUM)."""
        pass

    @property
    @abstractmethod
    def methodology_name(self) -> str:
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

    # Backward compatibility properties
    @property
    def strategy_id(self) -> str:
        return self.methodology.lower()

    @property
    def strategy_name(self) -> str:
        return self.methodology_name

    @abstractmethod
    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        """
        Produce a deterministic ValidatorResult with full forensic intermediate metrics.
        """
        pass
