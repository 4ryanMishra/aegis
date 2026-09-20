"""
Methodology Lane 5: Page CUSUM Sequential Drift Detection.
"""

from typing import List, Dict, Any, Optional
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorResult, DataStatus, MethodologyRole
from packages.quant.src.methodologies.cusum import PageCUSUM


class CUSUMStrategy(ValidatorStrategy):
    @property
    def lane_id(self) -> int:
        return 5

    @property
    def methodology(self) -> str:
        return "CUSUM"

    @property
    def methodology_name(self) -> str:
        return "Page CUSUM Sequential Drift Detection"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def default_source_ids(self) -> List[str]:
        return ["continuous_trade_stream", "sequential_drift_monitor"]

    def __init__(self, kappa: float = 0.5, threshold_h: float = 4.0):
        self.cusum = PageCUSUM(kappa=kappa, threshold_h=threshold_h)

    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        p_base = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm

        # Build synthetic tick series leading up to current verification timestamp
        # Length ~ 10 steps representing progress across the window
        steps = 10
        base_vol = p_base * 0.003  # 0.3% baseline volatility

        if context.scenario_type == "SLOW_DRIFT":
            # Subtle cumulative upward drift (+0.4% per step)
            # Individual steps pass single-tick threshold, but CUSUM accumulates standardized increments and trips
            series = [
                round(p_base + (i * 0.42 * base_vol / 0.3) + (((hash(str(i) + str(context.seed)) % 5) - 2) / 30.0), 2)
                for i in range(steps)
            ]
        elif context.scenario_type == "FLASH_SPIKE":
            # Transient flash spike at end
            series = [round(p_base + (((hash(str(i)) % 5) - 2) / 20.0), 2) for i in range(steps - 1)]
            series.append(round(p_base * 1.11, 2))
        elif context.scenario_type == "RWA_DEPEG":
            # Continuous downward slide
            series = [round(p_base - (i * 0.8), 2) for i in range(steps)]
        else:
            # Stationary baseline series
            series = [
                round(p_base + (((hash(str(i) + str(context.seed)) % 11) - 5) / 50.0), 2)
                for i in range(steps)
            ]

        res = self.cusum.evaluate_series(
            prices=series,
            baseline_price=p_base,
            baseline_volatility=base_vol,
        )

        intermediate = {
            "current_increment": res.current_increment,
            "standardized_increment": res.current_increment,
            "s_plus": res.s_plus,
            "s_minus": res.s_minus,
            "s_pos": res.s_plus,
            "s_neg": res.s_minus,
            "kappa": res.kappa,
            "drift_kappa": res.kappa,
            "threshold_h": res.threshold_h,
            "tick_volatility": res.tick_volatility,
            "trip_state": res.trip_state,
            "direction": res.direction,
            "drift_detected": res.trip_state in ("TRIP", "DRIFT"),
            "history_length": len(res.history_series),
            "recent_trajectory": [h.s_plus for h in res.history_series],
            "history_series": [h.model_dump() for h in res.history_series],
        }

        diagnostic_evidence = {
            "trip_state": res.trip_state,
            "direction": res.direction,
            "s_plus": res.s_plus,
            "s_minus": res.s_minus,
            "s_pos": res.s_plus,
            "s_neg": res.s_minus,
            "threshold_h": res.threshold_h,
            "kappa": res.kappa,
            "drift_kappa": res.kappa,
            "tick_volatility": res.tick_volatility,
            "current_increment": res.current_increment,
            "standardized_increment": res.current_increment,
            "drift_detected": res.trip_state in ("TRIP", "DRIFT"),
            "latest_price_hint": res.estimated_price,
            "decision": res.decision,
        }

        return ValidatorResult(
            validator_id=validator_id,
            methodology=self.methodology,
            methodology_name=self.methodology_name,
            methodology_version=self.version,
            lane_id=self.lane_id,
            operator_id=operator_id,
            timestamp=context.window_start_ts + 2100,  # T+35m
            input_sources=self.default_source_ids,
            input_values={"sample_count": len(series), "latest_price": series[-1]},
            role=MethodologyRole.SEQUENTIAL_DRIFT_DETECTOR,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            confidence=0.95 if res.trip_state == "NORMAL" else 0.45,
            diagnostic_evidence=diagnostic_evidence,
            intermediate_metrics=intermediate,
            anomaly_score=res.anomaly_score,
            decision=res.decision,
            reason_code=res.reason_code,
            provenance={
                "detector": "PAGE_TWO_SIDED_CUSUM",
                "drift_slack_kappa": res.kappa,
                "decision_bound_h": res.threshold_h,
            },
            computation_metadata={"tick_count": len(series), "runtime_ms": 0.6},
            status=DataStatus.SIMULATED,
        )
