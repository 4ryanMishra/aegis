"""
Comprehensive Mathematical Tests for AEGIS Five Methodology Lanes (Phase 4A Task 17).
Tests:
- Kalman Filter & Mahalanobis Innovation Gating
- Huber M-Estimation via IRLS
- Pairwise Jensen-Shannon Divergence on discrete uncertainty distributions
- Ornstein-Uhlenbeck RWA Residual Analysis
- Page CUSUM Sequential Drift Detection
"""

import pytest
import math
import numpy as np
from packages.quant.src.methodologies.kalman import KalmanFilter1D
from packages.quant.src.methodologies.huber import HuberMEstimator
from packages.quant.src.methodologies.jsd import JensenShannonDivergence, JSDLaneInput
from packages.quant.src.methodologies.ou import OrnsteinUhlenbeckAnalyzer
from packages.quant.src.methodologies.cusum import PageCUSUM


# ==============================================================================
# 1. KALMAN FILTER TESTS
# ==============================================================================

def test_kalman_normal_observation_accepted():
    """Normal observation within chi-squared threshold should be accepted."""
    kf = KalmanFilter1D(default_q=0.25, default_r=1.0, chi2_threshold=6.635)
    res = kf.step(observation=100.2, prior_state=100.0, prior_covariance=1.0)
    assert res.is_accepted is True
    assert res.decision == "ACCEPTED"
    assert res.reason_code == "INNOVATION_ACCEPTED_CONSISTENT"
    assert res.mahalanobis_d2 < 6.635
    assert res.posterior_state > 100.0
    assert res.posterior_covariance < res.prior_covariance


def test_kalman_strong_innovation_gated():
    """Anomalous innovation exceeding chi-squared threshold must be gated and prior retained."""
    kf = KalmanFilter1D(default_q=0.25, default_r=1.0, chi2_threshold=6.635)
    # Huge spike: +15 when variance is ~2.0 -> D^2 ~ 225 / 2.25 = 100 >> 6.635
    res = kf.step(observation=115.0, prior_state=100.0, prior_covariance=1.0)
    assert res.is_accepted is False
    assert res.decision == "INNOVATION_GATED"
    assert res.reason_code == "STATISTICAL_ANOMALY_GATED"
    assert res.mahalanobis_d2 > 6.635
    assert res.posterior_state == 100.0  # Retains prior
    assert res.anomaly_score > 0.5


def test_kalman_deterministic_replay():
    """Identical inputs must yield identical bit-exact outputs."""
    kf1 = KalmanFilter1D()
    kf2 = KalmanFilter1D()
    res1 = kf1.step(observation=98.5, prior_state=98.0, prior_covariance=0.75)
    res2 = kf2.step(observation=98.5, prior_state=98.0, prior_covariance=0.75)
    assert res1.posterior_state == res2.posterior_state
    assert res1.mahalanobis_d2 == res2.mahalanobis_d2
    assert res1.posterior_covariance == res2.posterior_covariance


# ==============================================================================
# 2. HUBER M-ESTIMATION TESTS
# ==============================================================================

def test_huber_central_cluster():
    """Under clean Gaussian data, Huber M-estimator behaves like sample mean."""
    estimator = HuberMEstimator(k=1.345)
    obs = [100.05, 99.95, 100.0, 100.06, 99.94]
    res = estimator.estimate(obs)
    assert res.final_estimate == pytest.approx(100.0, abs=0.05)
    assert res.outlier_count == 0
    assert res.converged is True
    assert all(w.weight == 1.0 for w in res.weights_table)


def test_huber_single_outlier_downweighting():
    """A severe single outlier must receive significantly reduced weight."""
    estimator = HuberMEstimator(k=1.345)
    # 4 normal observations around 100, one massive outlier at 130
    obs = [99.8, 100.0, 100.1, 100.2, 130.0]
    res = estimator.estimate(obs)
    # Robust location remains anchored near 100, NOT dragged to 106
    assert res.final_estimate < 102.0
    assert res.outlier_count == 1
    # Check that outlier weight is strictly < 1.0
    outlier_rec = [w for w in res.weights_table if w.price == 130.0][0]
    assert outlier_rec.weight < 0.25
    assert outlier_rec.is_outlier is True


def test_huber_zero_mad_handling():
    """Zero MAD (e.g. repeated quotes) must not trigger division by zero."""
    estimator = HuberMEstimator(k=1.345)
    obs = [100.0, 100.0, 100.0, 100.0]
    res = estimator.estimate(obs)
    assert res.final_estimate == 100.0
    assert res.scale_s > 0.0
    assert res.converged is True


# ==============================================================================
# 3. JENSEN-SHANNON DIVERGENCE TESTS
# ==============================================================================

def test_jsd_identical_distributions():
    """JSD between identical distributions must be zero."""
    jsd = JensenShannonDivergence(grid_bins=100)
    inputs = [
        JSDLaneInput(lane_id="l1", estimate=100.0, lower_bound=98.0, upper_bound=102.0),
        JSDLaneInput(lane_id="l2", estimate=100.0, lower_bound=98.0, upper_bound=102.0),
    ]
    res = jsd.evaluate(inputs)
    assert res.pairwise_jsd_matrix[0][1] == pytest.approx(0.0, abs=1e-5)
    assert res.informational_disagreement == pytest.approx(0.0, abs=1e-5)
    assert res.decision == "INFORMATIONAL_CONSENSUS"


def test_jsd_symmetry_and_boundedness():
    """JSD must be symmetric: JSD(P, Q) = JSD(Q, P) and strictly bounded in [0, 1]."""
    jsd = JensenShannonDivergence(grid_bins=150)
    inputs = [
        JSDLaneInput(lane_id="l1", estimate=95.0, lower_bound=93.0, upper_bound=97.0),
        JSDLaneInput(lane_id="l2", estimate=108.0, lower_bound=106.0, upper_bound=110.0),
    ]
    res = jsd.evaluate(inputs)
    val_12 = res.pairwise_jsd_matrix[0][1]
    val_21 = res.pairwise_jsd_matrix[1][0]
    assert val_12 == pytest.approx(val_21, abs=1e-6)
    assert 0.0 <= val_12 <= 1.0
    assert val_12 > 0.5  # Distinct distributions have high divergence


# ==============================================================================
# 4. ORNSTEIN-UHLENBECK RWA RESIDUAL TESTS
# ==============================================================================

def test_ou_not_applicable_without_anchor():
    """When no anchor is available, OU must return explicit NOT_APPLICABLE."""
    ou = OrnsteinUhlenbeckAnalyzer()
    res = ou.evaluate(spot_price=100.0, anchor_price=None, is_rwa=False)
    assert res.is_applicable is False
    assert res.decision == "NOT_APPLICABLE"
    assert res.reason_code == "RWA_ANCHOR_NOT_AVAILABLE"


def test_ou_valid_anchor_equilibrium():
    """Spot aligned with anchor should yield low residual and no jump flag."""
    ou = OrnsteinUhlenbeckAnalyzer()
    res = ou.evaluate(spot_price=100.05, anchor_price=100.0, is_rwa=True)
    assert res.is_applicable is True
    assert res.jump_candidate is False
    assert res.decision == "DIFFUSION_CONSISTENT"
    assert abs(res.standardized_residual) < 1.0


def test_ou_extreme_residual_jump_candidate():
    """Extreme depeg relative to anchor triggers jump candidate flag."""
    ou = OrnsteinUhlenbeckAnalyzer(jump_threshold=3.5)
    # Severe depeg: spot drops from 100 to 90
    res = ou.evaluate(spot_price=90.0, anchor_price=100.0, is_rwa=True)
    assert res.is_applicable is True
    assert res.jump_candidate is True
    assert res.decision == "DIFFUSION_MODEL_INCONSISTENCY"
    assert res.reason_code == "STRUCTURAL_RESIDUAL_ALERT"
    assert abs(res.standardized_residual) > 3.5


# ==============================================================================
# 5. PAGE CUSUM SEQUENTIAL DRIFT TESTS
# ==============================================================================

def test_cusum_stationary_series():
    """Stationary series around baseline remains in NORMAL regime."""
    cusum = PageCUSUM(kappa=0.5, threshold_h=4.0)
    prices = [100.0, 100.1, 99.9, 100.0, 100.2, 99.8, 100.1]
    res = cusum.evaluate_series(prices, baseline_price=100.0, baseline_volatility=0.5)
    assert res.trip_state == "NORMAL"
    assert res.decision == "BASELINE_STATIONARY"
    assert res.s_plus < 4.0
    assert res.s_minus < 4.0


def test_cusum_positive_drift_trips():
    """Persistent upward increments accumulate and trip threshold."""
    cusum = PageCUSUM(kappa=0.5, threshold_h=3.0)
    # Consecutive upward steps: y_k = (P_k - 100) / 0.5 = 2.0 per step
    # S_plus increases by (2.0 - 0.5) = 1.5 per step -> trips in 2-3 steps
    prices = [100.0, 101.0, 101.5, 102.0, 102.5]
    res = cusum.evaluate_series(prices, baseline_price=100.0, baseline_volatility=0.5)
    assert res.trip_state == "TRIP"
    assert res.decision == "SEQUENTIAL_DRIFT_DETECTED"
    assert res.reason_code == "CUSUM_ACCUMULATOR_TRIPPED"
    assert res.direction == "POSITIVE_DRIFT"
    assert res.s_plus >= 3.0


# ==============================================================================
# 6. MATHEMATICAL AUDIT & ROLE CLASSIFICATION TESTS (PHASE 4A.1)
# ==============================================================================

def test_kalman_threshold_comparison_alpha_01_vs_05():
    """
    Verify that a moderate innovation (D^2 ~ 5.0) is accepted under chi2(1, 0.99) = 6.635 (alpha=0.01)
    to prevent false alarms during volatile market conditions, but rejected under chi2(1, 0.95) = 3.841 (alpha=0.05).
    """
    # System: prior = 100.0, prior_cov = 1.0, q = 0.25, r = 1.0
    # Innovation variance S = (1.0 + 0.25) + 1.0 = 2.25. sqrt(S) = 1.5.
    # To get D^2 = 5.0: residual y = sqrt(5.0 * 2.25) = sqrt(11.25) ~ 3.3541
    obs = 100.0 + math.sqrt(11.25)

    # 99% confidence gate (alpha=0.01)
    kf_99 = KalmanFilter1D(default_q=0.25, default_r=1.0, chi2_threshold=6.635, alpha=0.01)
    res_99 = kf_99.step(observation=obs, prior_state=100.0, prior_covariance=1.0)
    assert res_99.mahalanobis_d2 == pytest.approx(5.0, abs=1e-4)
    assert res_99.is_accepted is True
    assert res_99.decision == "ACCEPTED"
    assert res_99.alpha == 0.01
    assert res_99.confidence_level == 0.99

    # 95% confidence gate (alpha=0.05)
    kf_95 = KalmanFilter1D(default_q=0.25, default_r=1.0, chi2_threshold=3.841, alpha=0.05)
    res_95 = kf_95.step(observation=obs, prior_state=100.0, prior_covariance=1.0)
    assert res_95.mahalanobis_d2 == pytest.approx(5.0, abs=1e-4)
    assert res_95.is_accepted is False
    assert res_95.decision == "INNOVATION_GATED"
    assert res_95.alpha == 0.05
    assert res_95.confidence_level == 0.95


def test_methodology_strategy_roles_and_diagnostic_separation():
    """
    Verify that all 5 validator strategy implementations correctly decouple
    price estimation from diagnostic evidence evaluation:
    - Lanes 1 & 2: Price Estimators (numeric estimated_price, is_price_estimator=True)
    - Lanes 3, 4, 5: Diagnostic Evidence (estimated_price=None, is_price_estimator=False, rich diagnostic_evidence)
    """
    from services.api.src.validators.strategies.kalman_strategy import KalmanStrategy
    from services.api.src.validators.strategies.huber_strategy import HuberStrategy
    from services.api.src.validators.strategies.jsd_strategy import JSDStrategy
    from services.api.src.validators.strategies.ou_strategy import OUStrategy
    from services.api.src.validators.strategies.cusum_strategy import CUSUMStrategy
    from services.api.src.validators.base import ReferenceContext
    from services.api.src.models.schema import MethodologyRole

    ctx = ReferenceContext(
        asset="ETH/USD",
        p_osm=100.0,
        window_start_ts=1700000000,
        current_ts=1700001800,
        expected_market_hint=100.0,
        anchor_price=100.0,
        is_rwa=True,
        scenario_type="NORMAL"
    )

    # Lane 1: Kalman
    kalman_strat = KalmanStrategy()
    r1 = kalman_strat.generate("val_1", ctx)
    assert r1.role == MethodologyRole.PRICE_ESTIMATOR
    assert r1.is_price_estimator is True
    assert r1.estimated_price is not None
    assert "mahalanobis_d2" in r1.diagnostic_evidence
    assert r1.diagnostic_evidence["alpha"] == 0.01
    assert r1.diagnostic_evidence["chi2_threshold"] == 6.635

    # Lane 2: Huber
    huber_strat = HuberStrategy()
    r2 = huber_strat.generate("val_2", ctx)
    assert r2.role == MethodologyRole.PRICE_ESTIMATOR
    assert r2.is_price_estimator is True
    assert r2.estimated_price is not None
    assert "outlier_count" in r2.diagnostic_evidence

    # Lane 3: JSD
    jsd_strat = JSDStrategy()
    r3 = jsd_strat.generate("val_3", ctx)
    assert r3.role == MethodologyRole.UNCERTAINTY_CONSENSUS_MEASURE
    assert r3.is_price_estimator is False
    assert r3.estimated_price is None
    assert r3.uncertainty_lower is None
    assert r3.uncertainty_upper is None
    assert "pairwise_jsd_matrix" in r3.diagnostic_evidence
    assert "informational_disagreement" in r3.diagnostic_evidence

    # Lane 4: OU Residual
    ou_strat = OUStrategy()
    r4 = ou_strat.generate("val_4", ctx)
    assert r4.role == MethodologyRole.RWA_STRUCTURAL_CHECK
    assert r4.is_price_estimator is False
    assert r4.estimated_price is None
    assert r4.uncertainty_lower is None
    assert r4.uncertainty_upper is None
    assert "jump_candidate" in r4.diagnostic_evidence
    assert "standardized_residual" in r4.diagnostic_evidence

    # Lane 5: Page CUSUM
    cusum_strat = CUSUMStrategy()
    r5 = cusum_strat.generate("val_5", ctx)
    assert r5.role == MethodologyRole.SEQUENTIAL_DRIFT_DETECTOR
    assert r5.is_price_estimator is False
    assert r5.estimated_price is None
    assert r5.uncertainty_lower is None
    assert r5.uncertainty_upper is None
    assert "trip_state" in r5.diagnostic_evidence
    assert "s_plus" in r5.diagnostic_evidence
    assert "s_minus" in r5.diagnostic_evidence

