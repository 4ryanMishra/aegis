"""
Methodology Lane 2: Huber M-Estimation via IRLS.
"""

from typing import List, Dict, Any
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorResult, DataStatus, MethodologyRole
from packages.quant.src.methodologies.huber import HuberMEstimator


class HuberStrategy(ValidatorStrategy):
    @property
    def lane_id(self) -> int:
        return 2

    @property
    def methodology(self) -> str:
        return "HUBER_IRLS"

    @property
    def methodology_name(self) -> str:
        return "Huber M-Estimation via IRLS"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def default_source_ids(self) -> List[str]:
        return ["binance_l1_depth", "bybit_spot", "coinbase_vwap", "kraken_trades", "uniswap3_twap"]

    def __init__(self, k: float = 1.345, max_iter: int = 50):
        self.estimator = HuberMEstimator(k=k, max_iter=max_iter)

    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        p_base = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm

        # Generate realistic multi-venue quotes based on scenario
        quotes = [
            round(p_base - 0.15, 2),
            round(p_base + 0.10, 2),
            round(p_base - 0.05, 2),
            round(p_base + 0.20, 2),
            round(p_base, 2),
        ]

        if context.scenario_type == "POISONED_VALIDATOR":
            # One feed injects severe rogue outlier ($500.0)
            quotes[0] = 500.0
        elif context.scenario_type == "FLASH_SPIKE":
            # Temporary single-exchange flash spike (+12%)
            quotes[1] = round(p_base * 1.12, 2)
        elif context.scenario_type == "FLASH_CRASH":
            # Genuine market real move around p_base ($93.50)
            quotes = [
                round(p_base - 0.15, 2),
                round(p_base + 0.10, 2),
                round(p_base - 0.05, 2),
                round(p_base + 0.20, 2),
                round(p_base, 2),
            ]
        elif context.scenario_type == "SLOW_DRIFT":
            # All quotes drift slightly upwards (+0.9%)
            quotes = [round(q * 1.009, 2) for q in quotes]
        elif context.scenario_type == "RWA_DEPEG":
            # Spot quotes reflect secondary market discount around p_base
            quotes = [
                round(p_base - 0.08, 2),
                round(p_base + 0.05, 2),
                round(p_base - 0.02, 2),
                round(p_base + 0.10, 2),
                round(p_base, 2),
            ]

        # Execute deterministic Huber IRLS estimation
        res = self.estimator.estimate(quotes)

        intermediate = {
            "raw_observations": res.raw_observations,
            "initial_median": res.initial_median,
            "mad": res.mad,
            "scale_s": res.scale_s,
            "huber_k": res.huber_k,
            "iterations": res.iterations,
            "converged": res.converged,
            "weights_table": [w.model_dump() for w in res.weights_table],
            "final_estimate": res.final_estimate,
            "robust_dispersion": res.robust_dispersion,
            "standard_error": res.standard_error,
            "outlier_count": res.outlier_count,
        }

        diagnostic_evidence = {
            "outlier_count": res.outlier_count,
            "robust_dispersion": res.robust_dispersion,
            "scale_s": res.scale_s,
            "converged": res.converged,
            "iterations": res.iterations,
            "decision": res.decision,
        }

        return ValidatorResult(
            validator_id=validator_id,
            methodology=self.methodology,
            methodology_name=self.methodology_name,
            methodology_version=self.version,
            lane_id=self.lane_id,
            operator_id=operator_id,
            timestamp=context.window_start_ts + 1200,  # T+20m
            input_sources=self.default_source_ids,
            input_values={"venue_quotes": quotes},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=res.final_estimate,
            uncertainty_lower=res.uncertainty_lower,
            uncertainty_upper=res.uncertainty_upper,
            confidence=0.92 if res.outlier_count <= 1 else 0.70,
            diagnostic_evidence=diagnostic_evidence,
            intermediate_metrics=intermediate,
            anomaly_score=res.anomaly_score,
            decision=res.decision,
            reason_code=res.reason_code,
            provenance={
                "estimator": "HUBER_LOCATION_IRLS",
                "loss_transition": "QUADRATIC_TO_LINEAR",
                "scale": "NORMALIZED_MAD",
            },
            computation_metadata={"iterations": res.iterations, "runtime_ms": 0.8},
            status=DataStatus.SIMULATED,
        )
