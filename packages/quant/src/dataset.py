"""
Historical Replay Dataset Interface & Deterministic Synthetic Data Generator.
Ensures zero future-leakage data access and reproducible evaluation.
"""

from typing import List, Optional, Dict, Any
import numpy as np
from .models import (
    HistoricalMarketObservation,
    TimestampedObservation,
    DatasetManifest,
    DataQualityReport,
)


class HistoricalReplayDataset:
    """
    Standard interface for historical market replay data.
    Provides strict point-in-time querying up to timestamp t.
    """

    def __init__(
        self,
        name: str,
        observations: List[HistoricalMarketObservation],
        description: str = "",
        status: str = "SIMULATED",
        manifest: Optional[DatasetManifest] = None,
        quality_report: Optional[DataQualityReport] = None,
        sampling_interval_seconds: int = 60,
    ):
        self.name = name
        # Ensure observations are sorted chronologically
        self.observations = sorted(observations, key=lambda x: x.timestamp)
        self.description = description
        self.status = status
        self.manifest = manifest
        self.quality_report = quality_report
        self.sampling_interval_seconds = (
            manifest.sampling_interval_seconds if manifest else sampling_interval_seconds
        )
        self._timestamps = np.array([obs.timestamp for obs in self.observations], dtype=np.int64)

    @property
    def dataset_id(self) -> str:
        return self.manifest.dataset_id if self.manifest else self.name

    @property
    def source(self) -> str:
        if self.manifest:
            return self.manifest.source
        if self.observations:
            return self.observations[0].source
        return "unknown_source"

    @property
    def asset(self) -> str:
        if self.manifest:
            return self.manifest.asset
        if self.observations:
            return self.observations[0].asset
        return "XAU/USD"

    @property
    def start_ts(self) -> int:
        return int(self._timestamps[0]) if len(self._timestamps) > 0 else 0

    @property
    def end_ts(self) -> int:
        return int(self._timestamps[-1]) if len(self._timestamps) > 0 else 0

    def __len__(self) -> int:
        return len(self.observations)

    def get_observations_up_to(self, timestamp: int) -> List[HistoricalMarketObservation]:
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
    ) -> Optional[HistoricalMarketObservation]:
        """
        Retrieves the observation closest to the target timestamp within tolerance_sec.
        Useful for evaluating realized value at t + 3600s.
        """
        if len(self._timestamps) == 0:
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
        HistoricalMarketObservation(
            timestamp=timestamps[i],
            price=round(float(prices[i]), 4),
            volume=round(float(rng.uniform(10.0, 500.0)), 2),
            source="simulated_ou_market_feed",
            asset="XAU/USD",
            status="SIMULATED",
            metadata={"step_sec": step_seconds, "seed": seed}
        )
        for i in range(n_steps)
    ]

    manifest = DatasetManifest(
        dataset_id=dataset_name,
        asset="XAU/USD",
        source="simulated_ou_market_feed",
        acquisition_method="DETERMINISTIC_SYNTHETIC",
        source_url=None,
        timezone="UTC",
        sampling_interval_seconds=step_seconds,
        start_timestamp=timestamps[0] if timestamps else 0,
        end_timestamp=timestamps[-1] if timestamps else 0,
        status="SIMULATED",
        checksum_sha256=None,
        metadata={
            "seed": seed,
            "volatility": volatility,
            "mean_reversion_speed": mean_reversion_speed,
            "synthetic_model": "Ornstein-Uhlenbeck"
        }
    )

    quality_report = DataQualityReport(
        observation_count=n_steps,
        valid_count=n_steps,
        dropped_duplicates=0,
        invalid_prices_count=0,
        missing_intervals_count=0,
        expected_intervals_count=n_steps,
        coverage_percentage=100.0,
        min_timestamp=timestamps[0] if timestamps else None,
        max_timestamp=timestamps[-1] if timestamps else None,
        source="simulated_ou_market_feed",
        data_status="SIMULATED",
        gaps=[],
        is_strictly_monotonic=True
    )

    return HistoricalReplayDataset(
        name=dataset_name,
        observations=observations,
        description=f"Deterministic synthetic 24-hour RWA tick series generated with seed={seed}",
        status="SIMULATED",
        manifest=manifest,
        quality_report=quality_report,
        sampling_interval_seconds=step_seconds
    )
