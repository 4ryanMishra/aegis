"""
Validator Strategy Registry.
Provides pluggable discovery, registration, and invocation of validator strategies.
Allows Quant team to dynamically register new research methodologies.
"""

from typing import Dict, List, Optional
from .base import ValidatorStrategy, ReferenceContext
from .strategies import (
    MeanReversionStrategy,
    MomentumTrendStrategy,
    CrossDexVWAPStrategy,
    RobustDispersionStrategy,
)
from ..models.schema import ValidatorObservation


class StrategyRegistry:
    def __init__(self):
        self._strategies: Dict[str, ValidatorStrategy] = {}
        # Pre-register initial default placeholder strategies
        self.register(MeanReversionStrategy())
        self.register(MomentumTrendStrategy())
        self.register(CrossDexVWAPStrategy())
        self.register(RobustDispersionStrategy())

    def register(self, strategy: ValidatorStrategy) -> None:
        """Register a new or custom quant strategy."""
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> Optional[ValidatorStrategy]:
        """Retrieve strategy by ID."""
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Dict[str, str]]:
        """List all available strategies with metadata."""
        return [
            {
                "strategy_id": s.strategy_id,
                "strategy_name": s.strategy_name,
                "version": s.version,
                "default_sources": s.default_source_ids,
            }
            for s in self._strategies.values()
        ]

    def generate_all(self, context: ReferenceContext) -> List[ValidatorObservation]:
        """Execute all registered strategies for a logical set of simulated validators."""
        validator_ids = [
            ("val_alpha", "strat_mean_reversion_placeholder"),
            ("val_beta", "strat_momentum_trend_placeholder"),
            ("val_gamma", "strat_cross_dex_vwap_placeholder"),
            ("val_delta", "strat_robust_dispersion_placeholder"),
        ]
        
        observations: List[ValidatorObservation] = []
        for val_id, strat_id in validator_ids:
            strategy = self._strategies.get(strat_id)
            if strategy:
                obs = strategy.generate(validator_id=val_id, context=context)
                observations.append(obs)
                
        return observations


# Global default registry instance
default_registry = StrategyRegistry()
