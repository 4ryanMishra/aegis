"""
Methodology Lane 4: Ornstein-Uhlenbeck (OU) RWA Residual Analysis.
Continuous-time mean-reverting stochastic spread process for applicable RWA assets
with a defensible redemption, parity, or NAV anchor.

Applicability Criteria:
- Defensible NAV / redemption / parity anchor exists.
- Anchor price is positive and available.
- If no anchor exists: returns explicit NOT_APPLICABLE status.

Terminology Invariant:
Do NOT claim 'low diffusion likelihood proves a Poisson jump occurred'.
Use: 'jump candidate', 'diffusion-model inconsistency', or 'structural residual alert'.
"""

from typing import Optional, Dict, Any
import math
from pydantic import BaseModel, Field


class OUResult(BaseModel):
    is_applicable: bool
    spot_price: float
    anchor_price: Optional[float]
    log_spread: Optional[float]
    theta: float
    mu: float
    sigma: float
    dt: float
    expected_spread: Optional[float]
    conditional_variance: Optional[float]
    conditional_std: Optional[float]
    standardized_residual: Optional[float]
    jump_threshold: float = 3.5
    jump_candidate: bool
    decision: str
    reason_code: str
    estimated_price: float
    uncertainty_lower: float
    uncertainty_upper: float
    anomaly_score: float

    @property
    def is_jump_candidate(self) -> bool:
        return self.jump_candidate


class OrnsteinUhlenbeckAnalyzer:
    """
    Deterministic Ornstein-Uhlenbeck Residual & Jump-Diffusion Analyzer.
    dS_t = theta * (mu - S_t) * dt + sigma * dW_t
    """

    def __init__(
        self,
        theta: float = 0.5,       # Mean-reversion speed parameter
        mu: float = 0.0,          # Long-term equilibrium log-spread (0.0 = parity)
        sigma: float = 0.02,      # Volatility of spread diffusion
        dt: float = 1.0,          # Observation interval horizon (normalized 1 hr)
        jump_threshold: float = 3.5,  # Standard deviations for jump candidate (|z_OU| >= 3.5)
    ):
        self.theta = theta
        self.mu = mu
        self.sigma = sigma
        self.dt = dt
        self.jump_threshold = jump_threshold

    def evaluate(
        self,
        spot_price: float,
        anchor_price: Optional[float] = None,
        prior_spread: Optional[float] = None,
        is_rwa: bool = True,
        theta_override: Optional[float] = None,
        mu_override: Optional[float] = None,
        sigma_override: Optional[float] = None,
        dt_override: Optional[float] = None,
    ) -> OUResult:
        spot = float(spot_price)
        theta = float(theta_override if theta_override is not None else self.theta)
        mu = float(mu_override if mu_override is not None else self.mu)
        sigma = float(sigma_override if sigma_override is not None else self.sigma)
        dt = float(dt_override if dt_override is not None else self.dt)

        # 1. Applicability Verification
        if not is_rwa or anchor_price is None or anchor_price <= 0.0 or spot <= 0.0:
            return OUResult(
                is_applicable=False,
                spot_price=spot,
                anchor_price=anchor_price,
                log_spread=None,
                theta=theta,
                mu=mu,
                sigma=sigma,
                dt=dt,
                expected_spread=None,
                conditional_variance=None,
                conditional_std=None,
                standardized_residual=None,
                jump_threshold=self.jump_threshold,
                jump_candidate=False,
                decision="NOT_APPLICABLE",
                reason_code="RWA_ANCHOR_NOT_AVAILABLE",
                estimated_price=spot,
                uncertainty_lower=round(spot * 0.98, 4),
                uncertainty_upper=round(spot * 1.02, 4),
                anomaly_score=0.0,
            )

        anchor = float(anchor_price)

        # 2. Log-spread computation: S_t = ln(P_spot) - ln(P_anchor)
        log_spread = math.log(spot) - math.log(anchor)

        # 3. Conditional OU Distribution relative to prior spread / baseline equilibrium:
        # E[S_t | S_{prior}] = mu + (S_{prior} - mu) * exp(-theta * dt)
        s_prev = float(prior_spread if prior_spread is not None else mu)
        decay = math.exp(-theta * dt)
        expected_spread = mu + (s_prev - mu) * decay

        # Var(S_t | S_{prior}) = (sigma^2 / (2 * theta)) * (1 - exp(-2 * theta * dt))
        if theta > 1e-6:
            cond_variance = ((sigma ** 2) / (2.0 * theta)) * (1.0 - math.exp(-2.0 * theta * dt))
        else:
            cond_variance = (sigma ** 2) * dt
        cond_variance = max(cond_variance, 1e-12)
        cond_std = math.sqrt(cond_variance)

        # 4. Standardized residual: difference from conditional equilibrium expectation
        # Standardized residual: z_OU = (observed_spread - expected_spread) / sqrt(conditional_variance)
        std_residual = (log_spread - expected_spread) / cond_std

        # 5. Jump Candidate Flag under configured threshold (|z_OU| >= jump_threshold)
        is_jump_candidate = abs(std_residual) >= self.jump_threshold

        if is_jump_candidate:
            decision = "DIFFUSION_MODEL_INCONSISTENCY"
            reason_code = "STRUCTURAL_RESIDUAL_ALERT"
            excess = abs(std_residual) / self.jump_threshold
            anomaly_score = min(1.0, 0.6 + min(0.4, (excess - 1.0) / 3.0))
        elif abs(std_residual) >= self.jump_threshold * 0.6:
            decision = "ELEVATED_SPREAD_RESIDUAL"
            reason_code = "OU_MEAN_REVERSION_STRESS"
            anomaly_score = 0.35
        else:
            decision = "DIFFUSION_CONSISTENT"
            reason_code = "OU_SPREAD_EQUILIBRIUM"
            anomaly_score = min(0.2, abs(std_residual) / self.jump_threshold * 0.2)

        # Implied expected spot price from expected spread
        est_price = anchor * math.exp(expected_spread)
        lower_bound = anchor * math.exp(expected_spread - 1.96 * cond_std)
        upper_bound = anchor * math.exp(expected_spread + 1.96 * cond_std)

        return OUResult(
            is_applicable=True,
            spot_price=round(spot, 4),
            anchor_price=round(anchor, 4),
            log_spread=round(log_spread, 6),
            theta=round(theta, 4),
            mu=round(mu, 4),
            sigma=round(sigma, 6),
            dt=round(dt, 4),
            expected_spread=round(expected_spread, 6),
            conditional_variance=round(cond_variance, 8),
            conditional_std=round(cond_std, 6),
            standardized_residual=round(std_residual, 4),
            jump_threshold=round(self.jump_threshold, 2),
            jump_candidate=is_jump_candidate,
            decision=decision,
            reason_code=reason_code,
            estimated_price=round(est_price, 4),
            uncertainty_lower=round(lower_bound, 4),
            uncertainty_upper=round(upper_bound, 4),
            anomaly_score=round(anomaly_score, 4),
        )
