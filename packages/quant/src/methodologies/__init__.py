"""
AEGIS Quantitative Methodologies.
Five Canonical Methodology Lanes:
1. Recursive 1D Kalman Filter + Mahalanobis Innovation Gating
2. Huber M-Estimation via IRLS
3. Pairwise Jensen-Shannon Divergence on uncertainty distributions
4. Ornstein-Uhlenbeck RWA Residual Analysis
5. Page CUSUM Sequential Drift Detection
"""

from .kalman import KalmanFilter1D, KalmanResult
from .huber import HuberMEstimator, HuberResult
from .jsd import JensenShannonDivergence, JSDResult
from .ou import OrnsteinUhlenbeckAnalyzer, OUResult
from .cusum import PageCUSUM, CUSUMResult

__all__ = [
    "KalmanFilter1D",
    "KalmanResult",
    "HuberMEstimator",
    "HuberResult",
    "JensenShannonDivergence",
    "JSDResult",
    "OrnsteinUhlenbeckAnalyzer",
    "OUResult",
    "PageCUSUM",
    "CUSUMResult",
]
