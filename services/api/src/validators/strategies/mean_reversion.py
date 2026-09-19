"""
Placeholder Strategy 1: Statistical Mean Reversion.
Simulates an independent quant node using historical equilibrium reversion estimation.
"""

from typing import List
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorObservation, DataStatus


class MeanReversionStrategy(ValidatorStrategy):
    @property
    def strategy_id(self) -> str:
        return "strat_mean_reversion_placeholder"

    @property
    def strategy_name(self) -> str:
        return "Statistical Mean-Reversion Model (Placeholder)"

    @property
    def version(self) -> str:
        return "0.1.0-alpha"

    @property
    def default_source_ids(self) -> List[str]:
        return ["sim_orderbook_depth_feed_a", "sim_historical_ticks_b"]

    def generate(self, validator_id: str, context: ReferenceContext) -> ValidatorObservation:
        # Deterministic formula based on expected market or context
        target = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm * 0.94
        # Add slight deterministic offset based on seed and validator ID
        offset = ((hash(validator_id + str(context.seed)) % 100) - 50) / 500.0  # [-0.10, +0.10]
        estimate = round(target + offset, 2)
        lower = round(estimate - (estimate * 0.018), 2)
        upper = round(estimate + (estimate * 0.019), 2)

        return ValidatorObservation(
            validator_id=validator_id,
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            estimated_price=estimate,
            uncertainty_lower=lower,
            uncertainty_upper=upper,
            observed_at=context.window_start_ts + 900,  # T+15m
            source_ids=self.default_source_ids,
            method_version=self.version,
            status=DataStatus.SIMULATED,
            metadata={"sampling_window_sec": 900, "confidence_interval": "90%"}
        )
