"""
AEGIS Methodology & Validator Registry (Phase 4A Task 8).
Replaces placeholder strategies with the Five Canonical Methodology Lanes:
Lane 1 -> KALMAN (Recursive 1D Kalman + Mahalanobis Innovation Gating)
Lane 2 -> HUBER (Huber M-Estimation via IRLS)
Lane 3 -> JSD (Pairwise Jensen-Shannon Divergence)
Lane 4 -> OU (Ornstein-Uhlenbeck RWA Residual Analysis)
Lane 5 -> CUSUM (Page CUSUM Sequential Drift Detection)

Architecture Decoupling:
- Methodology: Quantitative algorithm definition
- Lane ID: Canonical methodology lane (1-5)
- Validator ID: Logical node identity (e.g. val_lane_1_kalman)
- Operator ID: Independent entity operating the node (e.g. operator_alpha)

MVP Simulation Limitation:
Simulates one validator node per methodology lane for demonstration.
The registry natively supports multiple independent validator operators per lane.
"""

from typing import Dict, List, Optional, Tuple
from .base import ValidatorStrategy, ReferenceContext
from .strategies import (
    KalmanStrategy,
    HuberStrategy,
    JSDStrategy,
    OUStrategy,
    CUSUMStrategy,
)
from ..models.schema import ValidatorResult


class MethodologyRegistry:
    def __init__(self):
        self._lane_strategies: Dict[int, ValidatorStrategy] = {}
        self._strategy_by_id: Dict[str, ValidatorStrategy] = {}

        # Register the five canonical methodology lanes
        self.register(KalmanStrategy())
        self.register(HuberStrategy())
        self.register(JSDStrategy())
        self.register(OUStrategy())
        self.register(CUSUMStrategy())

    def register(self, strategy: ValidatorStrategy) -> None:
        """Register a methodology lane strategy."""
        self._lane_strategies[strategy.lane_id] = strategy
        self._strategy_by_id[strategy.methodology.lower()] = strategy
        self._strategy_by_id[strategy.strategy_id] = strategy

    def get_by_lane(self, lane_id: int) -> Optional[ValidatorStrategy]:
        """Retrieve strategy by lane ID (1-5)."""
        return self._lane_strategies.get(lane_id)

    def get(self, strategy_id: str) -> Optional[ValidatorStrategy]:
        """Retrieve strategy by machine ID."""
        return self._strategy_by_id.get(strategy_id.lower())

    def list_methodologies(self) -> List[Dict[str, Any]]:
        """List all five registered methodology lanes with metadata."""
        return [
            {
                "lane_id": s.lane_id,
                "methodology": s.methodology,
                "methodology_name": s.methodology_name,
                "version": s.version,
                "default_sources": s.default_source_ids,
            }
            for s in sorted(self._lane_strategies.values(), key=lambda x: x.lane_id)
        ]

    # Backward compatibility alias
    def list_strategies(self) -> List[Dict[str, Any]]:
        return self.list_methodologies()

    def generate_all(self, context: ReferenceContext) -> List[ValidatorResult]:
        """
        Execute all registered methodology lanes.
        For MVP demonstration, one simulated validator node operates per lane.
        Explicitly labeled as an MVP simulation limitation.
        """
        node_definitions = [
            ("val_node_1", 1, "operator_node_1"),
            ("val_node_2", 2, "operator_node_2"),
            ("val_node_3", 3, "operator_node_3"),
            ("val_node_4", 4, "operator_node_4"),
            ("val_node_5", 5, "operator_node_5"),
        ]

        # Handle VALIDATOR_OUTAGE scenario: nodes 4 and 5 fail to submit
        if context.scenario_type == "VALIDATOR_OUTAGE":
            node_definitions = node_definitions[:3]

        # Handle POISONED_VALIDATOR scenario: designate val_node_2 as adversarial
        if context.scenario_type == "POISONED_VALIDATOR":
            context.adversarial_node_id = "val_node_2"

        results: List[ValidatorResult] = []
        for val_id, lane_id, op_id in node_definitions:
            strategy = self._lane_strategies.get(lane_id)
            if strategy:
                res = strategy.generate(
                    validator_id=val_id,
                    context=context,
                    operator_id=op_id,
                )
                results.append(res)

        return results


# Backward compatibility alias
StrategyRegistry = MethodologyRegistry

# Global default registry instance
default_registry = MethodologyRegistry()
