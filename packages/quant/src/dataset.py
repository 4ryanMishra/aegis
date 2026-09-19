"""
Historical Replay Dataset Interface & Deterministic Synthetic Data Generator.
Ensures zero future-leakage data access and reproducible evaluation.
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .models import TimestampedObservation


class HistoricalReplayDataset:
    """
    Standard interface for historical market replay data.
    Provides strict point-in-time querying up to timestamp t.
    """

    def __init__(
        self,
        name: str,
        observations: List[TimestampedObservation],
        description: str = "",
        status: str = "SIMULATED"
    ):
        self.name = name
        # Ensure observations are sorted chronologically
        self.observations = sorted(observations, key=lambda x: x.timestamp)
        self.description = description
        self.status = status
        self._timestamps = [obs.timestamp for obs in self.observations]

    @property
    def start_ts(self) -> int:
        return self._timestamps[0] if self._timestamps else 0

    @property
    def end_ts(self) -> int:
        return self._timestamps[-1] if self._timestamps else 0

    def __len__(self) -> int:
        return len(self.observations)

    def get_observations_up_to(self, timestamp: int) -> List[TimestampedObservation]:
        """
        Returns all observations strictly up to and including timestamp.
        Guarantees that no future data (t > timestamp) is returned.
        """
        idx = np.searchsorted(self._timestamps, timestamp, side="right")
        return self.observations[:idx]

    def get_observation_at(
        self,
        timestamp: int,
        tolerance_sec: int = 180
    ) -> Optional[TimestampedObservation]:
        """
        Retrieves the observation closest to the target timestamp within tolerance_sec.
        Useful for evaluating realized value at t + 3600s.
        """
        if not self._timestamps:
            return None

        idx = np.searchsorted(self._timestamps, timestamp)
        candidates = []
        if idx < len(self.observations):
            candidates.append(self.observations[idx])
        if idx > 0:
            candidates.append(self.observations[idx - 1])

        if not candidates:
            return None

        best = min(candidates, key=lambda obs: abs(obs.timestamp - timestamp))
        if abs(best.timestamp - timestamp) <= tolerance_sec:
            return best
        return None


def generate_synthetic_rwa_series(
    dataset_name: str = "synthetic_gold_rwa_24h",
    start_ts: int = 1774000000,
    duration_seconds: int = 86400,  # 24 hours
    step_seconds: int = 60,         # 1 minute ticks
    base_price: float = 95.0,
    seed: int = 42,
    volatility: float = 0.08,
    mean_reversion_speed: float = 0.15
) -> HistoricalReplayDataset:
    """
    Generates a deterministic synthetic tick series using an Ornstein-Uhlenbeck
    mean-reverting process with fixed seed.
    Explicitly labeled as SIMULATED.
    """
    rng = np.random.RandomState(seed)
    n_steps = duration_seconds // step_seconds
    timestamps = [start_ts + i * step_seconds for i in range(n_steps)]

    dt = step_seconds / 86400.0  # Fraction of day
    prices = np.zeros(n_steps)
    prices[0] = base_price

    for t in range(1, n_steps):
        # Mean reversion towards base_price + deterministic Wiener increments
        drift = mean_reversion_speed * (base_price - prices[t - 1]) * dt
        shock = volatility * prices[t - 1] * np.sqrt(dt) * rng.randn()
        prices[t] = max(10.0, prices[t - 1] + drift + shock)

    observations = [
        TimestampedObservation(
            timestamp=timestamps[i],
            price=round(float(prices[i]), 4),
            volume=round(float(rng.uniform(10.0, 500.0)), 2),
            source_id="synthetic_rwa_depth_feed",
            status="SIMULATED",
            metadata={"step_sec": step_seconds, "seed": seed}
        )
        for i in range(n_steps)
    ]

    return HistoricalReplayDataset(
        name=dataset_name,
        observations=observations,
        description=f"Deterministic synthetic 24-hour RWA tick series generated with seed={seed}",
        status="SIMULATED"
    )
