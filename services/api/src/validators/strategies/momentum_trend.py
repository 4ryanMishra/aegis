"""
Placeholder Strategy 2: Order-Flow Momentum & Trend.
Simulates a validator calculating directional intraday trend indicators.
"""

from typing import List
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorObservation, DataStatus


class MomentumTrendStrategy(ValidatorStrategy):
    @property
    def strategy_id(self) -> str:
        return "strat_momentum_trend_placeholder"

    @property
    def strategy_name(self) -> str:
        return "Order-Flow Momentum Indicator (Placeholder)"

    @property
    def version(self) -> str:
        return "0.1.0-alpha"

    @property
    def default_source_ids(self) -> List[str]:
        return ["sim_cex_order_flow_c", "sim_deriv_funding_rate_d"]

    def generate(self, validator_id: str, context: ReferenceContext) -> ValidatorObservation:
        target = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm * 0.935
        offset = ((hash(validator_id + str(context.seed) + "mom") % 100) - 50) / 400.0
        estimate = round(target + offset, 2)
        lower = round(estimate - (estimate * 0.022), 2)
        upper = round(estimate + (estimate * 0.020), 2)

        return ValidatorObservation(
            validator_id=validator_id,
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            estimated_price=estimate,
            uncertainty_lower=lower,
            uncertainty_upper=upper,
            observed_at=context.window_start_ts + 1800,  # T+30m
            source_ids=self.default_source_ids,
            method_version=self.version,
            status=DataStatus.SIMULATED,
            metadata={"sampling_window_sec": 1800, "momentum_decay": 0.85}
        )
