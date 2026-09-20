"""
Methodology Lane 1: Recursive 1D Kalman Filter + Mahalanobis Innovation Gating.
"""

from typing import List, Dict, Any, Optional
import math
from ..base import ValidatorStrategy, ReferenceContext
from ...models.schema import ValidatorResult, DataStatus, MethodologyRole
from packages.quant.src.methodologies.kalman import KalmanFilter1D


class KalmanStrategy(ValidatorStrategy):
    @property
    def lane_id(self) -> int:
        return 1

    @property
    def methodology(self) -> str:
        return "KALMAN_1D"

    @property
    def methodology_name(self) -> str:
        return "Recursive 1D Kalman + Mahalanobis Innovation Gating"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def default_source_ids(self) -> List[str]:
        return ["cex_spot_tick_stream", "recursive_state_estimator"]

    def __init__(self, default_q: float = 0.25, default_r: float = 1.0, chi2_threshold: float = 6.635):
        self.filter = KalmanFilter1D(default_q=default_q, default_r=default_r, chi2_threshold=chi2_threshold)

    def generate(
        self,
        validator_id: str,
        context: ReferenceContext,
        operator_id: str = "operator_node_1",
    ) -> ValidatorResult:
        # Determine prior and observation based on context and scenario
        p_base = context.expected_market_hint if context.expected_market_hint is not None else context.p_osm
        prior_state = p_base

        # Scenario adjustments
        if context.scenario_type == "FLASH_SPIKE":
            # Sudden transient spike in observation (e.g. +12%)
            observation = round(p_base * 1.12, 2)
        elif context.scenario_type == "POISONED_VALIDATOR" and context.adversarial_node_id == validator_id:
            # Adversarial poison attempt
            observation = round(p_base * 1.25, 2)
        elif context.scenario_type == "SLOW_DRIFT":
            # Small, gradual incremental drift (e.g. +0.8%)
            observation = round(p_base * 1.008, 2)
        elif context.scenario_type == "RWA_DEPEG":
            # Spot decoupled from anchor
            observation = round(p_base * 0.91, 2)
        else:
            # Normal condition with slight empirical observation jitter (deterministic from seed)
            jitter = (((hash(validator_id + str(context.seed) + "kalman") % 41) - 20) / 100.0)
            observation = round(p_base + jitter, 2)

        # Execute deterministic Kalman step
        res = self.filter.step(
            observation=observation,
            prior_state=prior_state,
            prior_covariance=0.5,
            q=0.25,
            r=1.0,
        )

        intermediate = {
            "prior_state": res.prior_state,
            "prior_covariance": res.prior_covariance,
            "observation": res.observation,
            "observation_variance": res.observation_variance,
            "innovation": res.innovation,
            "innovation_covariance": res.innovation_covariance,
            "mahalanobis_d2": res.mahalanobis_d2,
            "chi2_threshold": res.chi2_threshold,
            "alpha": res.alpha,
            "confidence_level": res.confidence_level,
            "is_accepted": res.is_accepted,
            "kalman_gain": res.kalman_gain,
            "posterior_state": res.posterior_state,
            "posterior_covariance": res.posterior_covariance,
        }

        diagnostic_evidence = {
            "is_accepted": res.is_accepted,
            "mahalanobis_d2": res.mahalanobis_d2,
            "chi2_threshold": res.chi2_threshold,
            "alpha": res.alpha,
            "confidence_level": res.confidence_level,
            "innovation": res.innovation,
            "innovation_covariance": res.innovation_covariance,
            "decision": res.decision,
        }

        return ValidatorResult(
            validator_id=validator_id,
            methodology=self.methodology,
            methodology_name=self.methodology_name,
            methodology_version=self.version,
            lane_id=self.lane_id,
            operator_id=operator_id,
            timestamp=context.window_start_ts + 900,  # T+15m
            input_sources=self.default_source_ids,
            input_values={"prior": prior_state, "observation": observation},
            role=MethodologyRole.PRICE_ESTIMATOR,
            is_price_estimator=True,
            estimated_price=res.posterior_state,
            uncertainty_lower=res.uncertainty_lower,
            uncertainty_upper=res.uncertainty_upper,
            confidence=0.95 if res.is_accepted else 0.40,
            diagnostic_evidence=diagnostic_evidence,
            intermediate_metrics=intermediate,
            anomaly_score=res.anomaly_score,
            decision=res.decision,
            reason_code=res.reason_code,
            provenance={
                "filter_type": "1D_DISCRETE_KALMAN",
                "innovation_gate": "MAHALANOBIS_CHI2",
                "df": 1,
            },
            computation_metadata={"iterations": 1, "runtime_ms": 0.4},
            status=DataStatus.SIMULATED,
        )
