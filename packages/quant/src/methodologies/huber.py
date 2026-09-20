"""
Methodology Lane 2: Huber M-Estimation via Iteratively Reweighted Least Squares (IRLS).
Provides outlier-resistant robust location estimation by transitioning smoothly
from quadratic loss (Gaussian center) to linear loss (heavy tails).

Mathematical Integrity:
- Huber M-estimator bounds influence via linear loss tails.
- It does NOT have a 50% breakdown point in joint location/scale estimation without high-breakdown auxiliary initializers.
- Outliers have bounded non-zero influence, not literally zero influence.
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np
from pydantic import BaseModel, Field


class HuberWeightRecord(BaseModel):
    price: float
    residual: float
    std_residual: float
    weight: float
    is_outlier: bool


class HuberResult(BaseModel):
    raw_observations: List[float]
    initial_median: float
    mad: float
    scale_s: float
    huber_k: float
    iterations: int
    converged: bool
    weights_table: List[HuberWeightRecord]
    final_estimate: float
    robust_dispersion: float
    standard_error: float
    outlier_count: int
    decision: str
    reason_code: str
    uncertainty_lower: float
    uncertainty_upper: float
    anomaly_score: float


class HuberMEstimator:
    """
    Deterministic Huber M-Estimator for robust location estimation using IRLS.
    """

    def __init__(
        self,
        k: float = 1.345,  # 95% efficiency for normal distribution
        max_iter: int = 50,
        tol: float = 1e-6,
    ):
        self.k = k
        self.max_iter = max_iter
        self.tol = tol

    def estimate(self, observations: List[float]) -> HuberResult:
        if not observations:
            raise ValueError("Observations list cannot be empty for Huber estimation.")

        z = np.array(observations, dtype=np.float64)
        n = len(z)

        if n == 1:
            val = float(z[0])
            record = HuberWeightRecord(
                price=val,
                residual=0.0,
                std_residual=0.0,
                weight=1.0,
                is_outlier=False,
            )
            return HuberResult(
                raw_observations=[val],
                initial_median=val,
                mad=0.0,
                scale_s=0.01 * val,
                huber_k=self.k,
                iterations=0,
                converged=True,
                weights_table=[record],
                final_estimate=val,
                robust_dispersion=0.01 * val,
                standard_error=0.01 * val,
                outlier_count=0,
                decision="SINGLE_OBSERVATION",
                reason_code="EXACT_SINGLE_OBSERVATION",
                uncertainty_lower=val * 0.99,
                uncertainty_upper=val * 1.01,
                anomaly_score=0.0,
            )

        # 1. Median initialization
        initial_median = float(np.median(z))

        # 2. MAD scale estimate
        abs_dev = np.abs(z - initial_median)
        mad = float(np.median(abs_dev))
        scale_s = 1.4826 * mad

        # Edge case: zero MAD (e.g. repeated quotes or identical feeds)
        if scale_s < 1e-8:
            mean_abs_dev = float(np.mean(abs_dev))
            if mean_abs_dev > 1e-8:
                scale_s = mean_abs_dev * 1.2533
            else:
                scale_s = max(abs(initial_median) * 1e-4, 1e-6)

        # 3. IRLS iterations
        mu = initial_median
        converged = False
        iteration_count = 0
        weights = np.ones(n, dtype=np.float64)
        std_residuals = np.zeros(n, dtype=np.float64)

        for it in range(self.max_iter):
            iteration_count = it + 1
            residuals = z - mu
            std_residuals = residuals / scale_s

            # Huber weight function: w(r) = 1 if |r| <= k else k / |r|
            abs_r = np.abs(std_residuals)
            weights = np.where(abs_r <= self.k, 1.0, self.k / np.maximum(abs_r, 1e-12))

            sum_w = np.sum(weights)
            if sum_w < 1e-12:
                mu_next = initial_median
                break

            mu_next = float(np.sum(weights * z) / sum_w)

            if abs(mu_next - mu) < self.tol:
                mu = mu_next
                converged = True
                break
            mu = mu_next

        # 4. Compute final weights and diagnostic table
        final_residuals = z - mu
        final_std_residuals = final_residuals / scale_s
        abs_final_r = np.abs(final_std_residuals)
        # Huber weight function attenuates weights linearly when |r| > k (k=1.345 for 95% Gaussian efficiency).
        final_weights = np.where(abs_final_r <= self.k, 1.0, self.k / np.maximum(abs_final_r, 1e-12))
        # An observation is classified as a severe statistical outlier when standardized residual |r| > 2.5.
        is_outlier_arr = abs_final_r > 2.5
        outlier_count = int(np.sum(is_outlier_arr))

        weights_table = [
            HuberWeightRecord(
                price=round(float(z[i]), 4),
                residual=round(float(final_residuals[i]), 4),
                std_residual=round(float(final_std_residuals[i]), 4),
                weight=round(float(final_weights[i]), 4),
                is_outlier=bool(is_outlier_arr[i]),
            )
            for i in range(n)
        ]

        # 5. Robust standard error calculation
        # Asymptotic variance approximation for Huber M-estimator:
        # Var(mu) = s^2 * (1/n * sum(psi^2)) / (1/n * sum(psi'))^2 / n
        psi = np.clip(final_std_residuals, -self.k, self.k)
        psi_prime = np.where(abs_final_r <= self.k, 1.0, 0.0)
        mean_psi2 = np.mean(psi ** 2)
        mean_psi_prime = np.mean(psi_prime)

        if mean_psi_prime > 1e-4:
            asymp_var = (scale_s ** 2) * (mean_psi2 / (mean_psi_prime ** 2)) / n
            se = math.sqrt(max(asymp_var, 1e-12))
        else:
            se = scale_s / math.sqrt(n)

        # Decision classification
        if outlier_count == 0:
            decision = "ROBUST_LOCATION_CONVERGED"
            reason_code = "GAUSSIAN_EFFICIENCY_MAINTAINED"
            anomaly_score = 0.05
        elif outlier_count <= n // 3:
            decision = "OUTLIERS_DOWNWEIGHTED"
            reason_code = "HUBER_LINEAR_LOSS_ATTENUATION"
            anomaly_score = min(0.6, 0.2 + 0.15 * outlier_count)
        else:
            decision = "HEAVY_TAIL_DISPERSION"
            reason_code = "MULTIPLE_ANOMALOUS_OBSERVATIONS"
            anomaly_score = min(1.0, 0.4 + 0.2 * outlier_count)

        lower = round(mu - 1.96 * se, 4)
        upper = round(mu + 1.96 * se, 4)

        return HuberResult(
            raw_observations=[round(float(x), 4) for x in z],
            initial_median=round(initial_median, 4),
            mad=round(mad, 4),
            scale_s=round(scale_s, 4),
            huber_k=round(self.k, 4),
            iterations=iteration_count,
            converged=converged,
            weights_table=weights_table,
            final_estimate=round(mu, 4),
            robust_dispersion=round(scale_s, 4),
            standard_error=round(se, 4),
            outlier_count=outlier_count,
            decision=decision,
            reason_code=reason_code,
            uncertainty_lower=lower,
            uncertainty_upper=upper,
            anomaly_score=round(anomaly_score, 4),
        )
