"""
Methodology Lane 1: Recursive 1D Kalman Filter + Mahalanobis Innovation Gating.
Dynamic state estimation over time series with chi-squared innovation gating
to filter abrupt transient outliers and detect model-inconsistent observations.

Terminology Invariant:
Rejection is NOT described as proof of maliciousness, but as a
'model-inconsistent observation', 'statistical anomaly', or 'innovation-gated observation'.
"""

from typing import Dict, Any, Optional
import math
from pydantic import BaseModel, Field


class KalmanResult(BaseModel):
    prior_state: float
    prior_covariance: float
    observation: float
    observation_variance: float
    innovation: float
    innovation_covariance: float
    mahalanobis_d2: float
    chi2_threshold: float
    alpha: float = Field(default=0.01, description="Significance level of the innovation test (e.g. 0.01 for 99% confidence)")
    confidence_level: float = Field(default=0.99, description="Confidence level (1 - alpha)")
    is_accepted: bool
    decision: str
    reason_code: str
    posterior_state: float
    posterior_covariance: float
    kalman_gain: float
    uncertainty_lower: float
    uncertainty_upper: float
    anomaly_score: float


class KalmanFilter1D:
    """
    Deterministic 1D Recursive Kalman Filter with Mahalanobis Innovation Gating.
    Tracks scalar price state x_k with Gaussian innovation gating.
    Uses chi2(1, 0.99) = 6.635 by default (significance alpha = 0.01).
    """

    def __init__(
        self,
        default_q: float = 0.25,
        default_r: float = 1.0,
        chi2_threshold: float = 6.635,  # chi2(1) at alpha=0.01 (99% confidence)
        alpha: float = 0.01,
    ):
        self.default_q = default_q
        self.default_r = default_r
        self.chi2_threshold = chi2_threshold
        self.alpha = alpha
        self.confidence_level = 1.0 - alpha

    def step(
        self,
        observation: float,
        prior_state: Optional[float] = None,
        prior_covariance: Optional[float] = None,
        q: Optional[float] = None,
        r: Optional[float] = None,
    ) -> KalmanResult:
        z = float(observation)
        q_val = float(q if q is not None else self.default_q)
        r_val = float(r if r is not None else self.default_r)

        # 1. Prior state & covariance prediction
        if prior_state is None:
            x_prior = z
            p_prior = r_val + q_val
        else:
            x_prior = float(prior_state)
            p_prev = float(prior_covariance if prior_covariance is not None else r_val)
            p_prior = p_prev + q_val

        # 2. Innovation (measurement residual)
        y = z - x_prior

        # 3. Innovation covariance
        s = p_prior + r_val
        s_safe = max(s, 1e-12)

        # 4. Mahalanobis statistic D^2 = y^2 / S
        d2 = (y * y) / s_safe

        # 5. Chi-square innovation gating check
        is_accepted = bool(d2 <= self.chi2_threshold)

        if is_accepted:
            decision = "ACCEPTED"
            reason_code = "INNOVATION_ACCEPTED_CONSISTENT"
            # Standard Kalman update
            k = p_prior / s_safe
            x_post = x_prior + k * y
            p_post = max((1.0 - k) * p_prior, 1e-8)
            # Normalized anomaly score in [0.0, 0.5]
            anomaly_score = min(0.5, (d2 / (2.0 * self.chi2_threshold)) * 0.5)
        else:
            decision = "INNOVATION_GATED"
            reason_code = "STATISTICAL_ANOMALY_GATED"
            # Innovation-gated observation: reject or strictly damp update
            k = 0.0
            x_post = x_prior  # Retain prior estimate
            p_post = p_prior  # Retain prior uncertainty
            # Anomaly score in [0.5, 1.0]
            ratio = d2 / self.chi2_threshold
            anomaly_score = min(1.0, 0.5 + min(0.5, (ratio - 1.0) / 10.0))

        # 95% uncertainty interval: +/- 1.96 * sqrt(P_post)
        std_post = math.sqrt(p_post)
        lower_bound = x_post - 1.96 * std_post
        upper_bound = x_post + 1.96 * std_post

        return KalmanResult(
            prior_state=round(x_prior, 4),
            prior_covariance=round(p_prior, 6),
            observation=round(z, 4),
            observation_variance=round(r_val, 6),
            innovation=round(y, 4),
            innovation_covariance=round(s, 6),
            mahalanobis_d2=round(d2, 4),
            chi2_threshold=round(self.chi2_threshold, 4),
            alpha=self.alpha,
            confidence_level=self.confidence_level,
            is_accepted=is_accepted,
            decision=decision,
            reason_code=reason_code,
            posterior_state=round(x_post, 4),
            posterior_covariance=round(p_post, 6),
            kalman_gain=round(k, 6),
            uncertainty_lower=round(lower_bound, 4),
            uncertainty_upper=round(upper_bound, 4),
            anomaly_score=round(anomaly_score, 4),
        )
