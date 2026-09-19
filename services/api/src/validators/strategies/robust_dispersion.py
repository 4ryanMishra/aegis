"""
Placeholder Strategy 4: Robust Inter-Venue Dispersion Filter.
Simulates an independent quant node using trimmed inter-quartile filtering across synthetic CEX/DEX quotes.
"""

from typing import List
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorObservation, DataStatus


class RobustDispersionStrategy(ValidatorStrategy):
    @property
    def strategy_id(self) -> str:
        return "strat_robust_dispersion_placeholder"

    @property
    def strategy_name(self) -> str:
        return "Trimmed Inter-Venue Dispersion Filter (Placeholder)"

    @property
    def version(self) -> str:
        return "0.1.0-alpha"

    @property
    def default_source_ids(self) -> List[str]:
        return ["sim_lmax_feed_h", "sim_kraken_feed_i", "sim_pyth_mock_j"]

    def generate(self, validator_id: str, context: ReferenceContext) -> ValidatorObservation:
        target = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm * 0.938
        offset = ((hash(validator_id + str(context.seed) + "disp") % 100) - 50) / 450.0
        estimate = round(target + offset, 2)
        lower = round(estimate - (estimate * 0.014), 2)
        upper = round(estimate + (estimate * 0.015), 2)

        return ValidatorObservation(
            validator_id=validator_id,
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            estimated_price=estimate,
            uncertainty_lower=lower,
            uncertainty_upper=upper,
            observed_at=context.window_start_ts + 2700,  # T+45m
            source_ids=self.default_source_ids,
            method_version=self.version,
            status=DataStatus.SIMULATED,
            metadata={"venues_sampled": 3, "trim_percentage": "10%"}
        )
