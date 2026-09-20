"""
Methodology Lane 3: Pairwise Jensen-Shannon Divergence on Uncertainty Distributions.
"""

from typing import List, Dict, Any
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorResult, DataStatus, MethodologyRole
from packages.quant.src.methodologies.jsd import JensenShannonDivergence, JSDLaneInput


class JSDStrategy(ValidatorStrategy):
    @property
    def lane_id(self) -> int:
        return 3

    @property
    def methodology(self) -> str:
        return "JSD"

    @property
    def methodology_name(self) -> str:
        return "Pairwise Jensen-Shannon Divergence"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def default_source_ids(self) -> List[str]:
        return ["dex_pool_reserves", "clob_depth_uncertainty", "options_implied_pdf"]

    def __init__(self, grid_bins: int = 150):
        self.jsd = JensenShannonDivergence(grid_bins=grid_bins)

    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        p_base = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm

        # Construct three distinct source distributions for uncertainty comparison
        p1 = round(p_base - 0.08, 2)
        p2 = round(p_base + 0.12, 2)
        p3 = round(p_base, 2)

        if context.scenario_type == "POISONED_VALIDATOR":
            p1 = round(p_base * 1.18, 2)  # Severe distribution shift in source 1
        elif context.scenario_type == "FLASH_SPIKE":
            p2 = round(p_base * 1.10, 2)
        elif context.scenario_type == "SLOW_DRIFT":
            p1, p2, p3 = round(p1 * 1.008, 2), round(p2 * 1.008, 2), round(p3 * 1.008, 2)
        elif context.scenario_type == "RWA_DEPEG":
            p1, p2, p3 = round(p1 * 0.91, 2), round(p2 * 0.91, 2), round(p3 * 0.91, 2)

        inputs = [
            JSDLaneInput(lane_id="src_dex_reserves", estimate=p1, lower_bound=p1 - 0.8, upper_bound=p1 + 0.8),
            JSDLaneInput(lane_id="src_clob_depth", estimate=p2, lower_bound=p2 - 0.9, upper_bound=p2 + 0.9),
            JSDLaneInput(lane_id="src_options_pdf", estimate=p3, lower_bound=p3 - 0.7, upper_bound=p3 + 0.7),
        ]

        res = self.jsd.evaluate(inputs)

        intermediate = {
            "grid_min": res.grid_min,
            "grid_max": res.grid_max,
            "grid_bins": res.grid_bins,
            "log_base": res.log_base,
            "jsd_bound": res.jsd_bound,
            "lane_ids": res.lane_ids,
            "pairwise_jsd_matrix": res.pairwise_jsd_matrix,
            "mean_divergence_per_lane": res.mean_divergence_per_lane,
            "lane_weights": res.lane_weights,
            "informational_disagreement": res.informational_disagreement,
            "consensus_price": res.consensus_price,
        }

        diagnostic_evidence = {
            "informational_disagreement": res.informational_disagreement,
            "mean_divergence_per_lane": res.mean_divergence_per_lane,
            "pairwise_jsd_matrix": res.pairwise_jsd_matrix,
            "lane_weights": res.lane_weights,
            "consensus_price_hint": res.consensus_price,
            "uncertainty_lower_hint": res.uncertainty_lower,
            "uncertainty_upper_hint": res.uncertainty_upper,
            "decision": res.decision,
        }

        return ValidatorResult(
            validator_id=validator_id,
            methodology=self.methodology,
            methodology_name=self.methodology_name,
            methodology_version=self.version,
            lane_id=self.lane_id,
            operator_id=operator_id,
            timestamp=context.window_start_ts + 1500,  # T+25m
            input_sources=self.default_source_ids,
            input_values={"source_estimates": [p1, p2, p3]},
            role=MethodologyRole.UNCERTAINTY_CONSENSUS_MEASURE,
            is_price_estimator=False,
            estimated_price=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            confidence=max(0.2, 1.0 - min(0.8, res.informational_disagreement * 2.0)),
            diagnostic_evidence=diagnostic_evidence,
            intermediate_metrics=intermediate,
            anomaly_score=res.anomaly_score,
            decision=res.decision,
            reason_code=res.reason_code,
            provenance={
                "metric": "PAIRWISE_JENSEN_SHANNON_DIVERGENCE",
                "space": "DISCRETE_PROBABILITY_GRID",
                "base": "LOG2",
            },
            computation_metadata={"bins": res.grid_bins, "runtime_ms": 1.2},
            status=DataStatus.SIMULATED,
        )
