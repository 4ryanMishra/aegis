"""
Methodology Lane 4: Ornstein-Uhlenbeck RWA Residual Analysis.
"""

from typing import List, Dict, Any, Optional
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorResult, DataStatus
from packages.quant.src.methodologies.ou import OrnsteinUhlenbeckAnalyzer


class OUStrategy(ValidatorStrategy):
    @property
    def lane_id(self) -> int:
        return 4

    @property
    def methodology(self) -> str:
        return "OU_RESIDUAL"

    @property
    def methodology_name(self) -> str:
        return "Ornstein-Uhlenbeck RWA Residual Analysis"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def default_source_ids(self) -> List[str]:
        return ["rwa_redemption_anchor", "secondary_clob_spot"]

    def __init__(self, theta: float = 0.5, mu: float = 0.0, sigma: float = 0.02):
        self.analyzer = OrnsteinUhlenbeckAnalyzer(theta=theta, mu=mu, sigma=sigma)

    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        # Check applicability: default to p_osm as anchor or explicit anchor
        is_rwa = context.is_rwa
        anchor = context.anchor_price if context.anchor_price is not None else context.p_osm

        p_base = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm
        spot = p_base

        if context.scenario_type == "RWA_DEPEG":
            # Significant real-world decoupling between spot and redemption anchor
            # Spot collapses by -9% while anchor remains $100
            spot = round(anchor * 0.91, 2)
        elif context.scenario_type == "FLASH_SPIKE":
            spot = round(p_base * 1.10, 2)
        elif context.scenario_type == "SLOW_DRIFT":
            spot = round(p_base * 1.008, 2)

        res = self.analyzer.evaluate(
            spot_price=spot,
            anchor_price=anchor if is_rwa else None,
            is_rwa=is_rwa,
        )

        intermediate = {
            "is_applicable": res.is_applicable,
            "spot_price": res.spot_price,
            "anchor_price": res.anchor_price,
            "log_spread": res.log_spread,
            "theta": res.theta,
            "mu": res.mu,
            "sigma": res.sigma,
            "dt": res.dt,
            "expected_spread": res.expected_spread,
            "conditional_variance": res.conditional_variance,
            "conditional_std": res.conditional_std,
            "standardized_residual": res.standardized_residual,
            "jump_candidate": res.jump_candidate,
        }

        return ValidatorResult(
            validator_id=validator_id,
            methodology=self.methodology,
            methodology_name=self.methodology_name,
            methodology_version=self.version,
            lane_id=self.lane_id,
            operator_id=operator_id,
            timestamp=context.window_start_ts + 1800,  # T+30m
            input_sources=self.default_source_ids,
            input_values={"spot": spot, "anchor": anchor, "is_rwa": is_rwa},
            estimated_price=res.estimated_price,
            uncertainty_lower=res.uncertainty_lower,
            uncertainty_upper=res.uncertainty_upper,
            confidence=0.90 if (res.is_applicable and not res.jump_candidate) else 0.50,
            intermediate_metrics=intermediate,
            anomaly_score=res.anomaly_score,
            decision=res.decision,
            reason_code=res.reason_code,
            provenance={
                "process": "ORNSTEIN_UHLENBECK_CONTINUOUS_SPREAD",
                "anchor_type": "PARITY_REDEMPTION_OR_NAV",
            },
            computation_metadata={"model_sde": "dS_t = theta(mu - S_t)dt + sigma*dW_t", "runtime_ms": 0.5},
            status=DataStatus.SIMULATED,
        )
