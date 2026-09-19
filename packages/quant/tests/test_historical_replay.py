"""
Unit and Integration Tests for Phase 2C Real Historical Data Replay & Benchmark.
Tests:
- Real-dataset ingestion path and 100% coverage
- Checksum and manifest correctness
- Strict point-in-time anti-leakage on real market data
- Deterministic benchmark reproducibility on real market data
"""

import pathlib
import hashlib
import pytest

from packages.quant.src.ingestion import CSVIngestionReader
from packages.quant.src.dataset import HistoricalReplayDataset
from packages.quant.src.strategy_base import ValidatorStrategy, InputContext
from packages.quant.src.models import ValidatorPrediction
from packages.quant.src.baseline_strategies import (
    NaivePersistenceStrategy,
    SimpleMovingAverageStrategy,
    ExponentialMovingAverageStrategy,
)
from packages.quant.src.backtest import RollingBacktestEngine
from packages.quant.src.benchmark import ValidatorBenchmarkRunner


CSV_PATH = pathlib.Path("data/historical/PAXGUSDT-1m-2024-01.csv")
ZIP_PATH = pathlib.Path("data/historical/PAXGUSDT-1m-2024-01.zip")
CHECKSUM_PATH = pathlib.Path("data/historical/PAXGUSDT-1m-2024-01.zip.CHECKSUM")

EXPECTED_ZIP_SHA256 = "84d790dda546070e4be0fbcc02e7751c2339c7d35ba91bfa1ad0f4f19aa7dcdc"


class FutureLeakageDetectionProbe(ValidatorStrategy):
    """Probe strategy that explicitly asserts no observation timestamp exceeds current_ts."""
    def __init__(self):
        self.leakage_detected = False
        self.max_seen_future_timestamp = -1

    @property
    def method_id(self) -> str:
        return "probe_future_leakage"

    @property
    def method_name(self) -> str:
        return "Future Leakage Detection Probe"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def source_provenance(self) -> list:
        return ["probe_feed"]

    def predict(self, context: InputContext) -> ValidatorPrediction:
        for obs in context.history:
            if obs.timestamp > context.current_ts:
                self.leakage_detected = True
                self.max_seen_future_timestamp = max(self.max_seen_future_timestamp, obs.timestamp)

        latest = context.latest_observation
        p = latest.price if latest else 100.0
        return ValidatorPrediction(
            validator_id=context.validator_id,
            method_id=self.method_id,
            method_version=self.version,
            point_estimate=p,
            lower_bound=p - 1.0,
            upper_bound=p + 1.0,
            timestamp=context.current_ts,
            target_timestamp=context.target_ts,
            source_provenance=self.source_provenance,
            input_window=context.get_input_window(),
            status=latest.status if latest else "HISTORICAL"
        )


@pytest.mark.skipif(not ZIP_PATH.exists(), reason="Real dataset zip archive not present in local data/historical")
def test_real_dataset_archive_checksum_correctness():
    """Verify raw downloaded ZIP archive matches the published Binance Vision SHA-256 hash."""
    raw_bytes = ZIP_PATH.read_bytes()
    computed_sha256 = hashlib.sha256(raw_bytes).hexdigest().lower()
    assert computed_sha256 == EXPECTED_ZIP_SHA256, (
        f"Archive checksum mismatch! Computed {computed_sha256} != expected {EXPECTED_ZIP_SHA256}"
    )
    if CHECKSUM_PATH.exists():
        expected_from_file = CHECKSUM_PATH.read_text().split()[0].strip().lower()
        assert computed_sha256 == expected_from_file


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Real dataset CSV not present in local data/historical")
def test_real_dataset_ingestion_path_and_quality():
    """Verify end-to-end ingestion of authentic Binance Vision PAXG/USDT 1m dataset."""
    dataset = CSVIngestionReader.read_binance_vision_klines(
        csv_text_or_path=CSV_PATH,
        asset="PAXG/USDT",
        dataset_id="paxg_usdt_binance_jan2024_1m",
        source_url="https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip"
    )

    # 1. Dataset identification & status
    assert dataset.status == "HISTORICAL"
    assert dataset.asset == "PAXG/USDT"
    assert dataset.source == "binance_vision_public_archive"
    assert dataset.dataset_id == "paxg_usdt_binance_jan2024_1m"

    # 2. Complete 31-day coverage check: 31 * 24 * 60 = 44,640 minutes
    assert len(dataset) == 44640

    # 3. Quality audit
    quality = dataset.quality_report
    assert quality is not None
    assert quality.observation_count == 44640
    assert quality.valid_count == 44640
    assert quality.dropped_duplicates == 0
    assert quality.invalid_prices_count == 0
    assert quality.missing_intervals_count == 0
    assert quality.coverage_percentage == 100.0
    assert quality.is_strictly_monotonic is True
    assert quality.min_timestamp == 1704067200  # 2024-01-01 00:00:00 UTC
    assert quality.max_timestamp == 1706745540  # 2024-01-31 23:59:00 UTC

    # 4. Manifest audit
    manifest = dataset.manifest
    assert manifest is not None
    assert manifest.status == "HISTORICAL"
    assert manifest.timezone == "UTC"
    assert manifest.sampling_interval_seconds == 60
    assert manifest.checksum_sha256 is not None


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Real dataset CSV not present in local data/historical")
def test_no_future_leakage_on_historical_dataset():
    """Verify strict anti-leakage invariant holds across rolling replay of authentic historical data."""
    dataset = CSVIngestionReader.read_binance_vision_klines(
        csv_text_or_path=CSV_PATH,
        asset="PAXG/USDT",
        dataset_id="paxg_usdt_leakage_test"
    )

    engine = RollingBacktestEngine(
        horizon_seconds=3600,
        rolling_step_seconds=1800,  # step every 30m for rapid testing
        warmup_seconds=3600
    )
    probe = FutureLeakageDetectionProbe()
    result = engine.run(strategy=probe, dataset=dataset)

    assert probe.leakage_detected is False, (
        f"CRITICAL: Future leakage detected! Max future timestamp seen: {probe.max_seen_future_timestamp}"
    )
    assert result.metrics.sample_count > 0
    assert result.dataset_status == "HISTORICAL"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Real dataset CSV not present in local data/historical")
def test_benchmark_reproducibility_on_historical_dataset():
    """Verify benchmark runs produce bit-for-bit identical results on identical historical data."""
    # Slice first 1,440 ticks (24 hours) for reproducible test
    dataset = CSVIngestionReader.read_binance_vision_klines(
        csv_text_or_path=CSV_PATH,
        asset="PAXG/USDT",
        dataset_id="paxg_usdt_repro_test"
    )
    # Take first 1440 observations
    sliced_observations = dataset.observations[:1440]
    replay_subset = HistoricalReplayDataset(
        name="paxg_usdt_24h_slice",
        observations=sliced_observations,
        status="HISTORICAL",
        manifest=dataset.manifest,
        quality_report=dataset.quality_report,
        sampling_interval_seconds=60
    )

    runner = ValidatorBenchmarkRunner(
        horizon_seconds=3600,
        rolling_step_seconds=900,
        warmup_seconds=3600
    )
    strategies = [
        NaivePersistenceStrategy(),
        SimpleMovingAverageStrategy(window_seconds=1800),
        ExponentialMovingAverageStrategy(alpha=0.15),
    ]

    comp1 = runner.run_benchmark(strategies=strategies, dataset=replay_subset, benchmark_id="run_1")
    comp2 = runner.run_benchmark(strategies=strategies, dataset=replay_subset, benchmark_id="run_2")

    assert comp1.ranked_by_mae == comp2.ranked_by_mae
    for r1, r2 in zip(comp1.results, comp2.results):
        assert r1.methodology_id == r2.methodology_id
        assert r1.metrics.mae == r2.metrics.mae
        assert r1.metrics.rmse == r2.metrics.rmse
        assert r1.metrics.directional_accuracy == r2.metrics.directional_accuracy
        assert r1.metrics.mean_absolute_percentage_error == r2.metrics.mean_absolute_percentage_error
        assert r1.metrics.sample_count == r2.metrics.sample_count
        assert r1.dataset_status == "HISTORICAL"


def test_deterministic_simulated_fixture_replay():
    """
    Fresh-clone reproducibility test:
    Verifies that the replay and benchmark pipeline runs deterministically
    on a committed synthetic fixture without requiring untracked historical files.
    Explicitly labeled as SIMULATED.
    """
    from packages.quant.src.dataset import generate_synthetic_rwa_series

    sim_dataset = generate_synthetic_rwa_series(
        dataset_name="repro_fixture_simulated_24h",
        duration_seconds=86400,
        step_seconds=60,
        seed=101
    )

    assert sim_dataset.status == "SIMULATED"
    assert sim_dataset.manifest is not None
    assert sim_dataset.manifest.status == "SIMULATED"

    runner = ValidatorBenchmarkRunner(
        horizon_seconds=3600,
        rolling_step_seconds=1800,
        warmup_seconds=3600
    )
    strategies = [
        NaivePersistenceStrategy(),
        SimpleMovingAverageStrategy(window_seconds=1800),
        ExponentialMovingAverageStrategy(alpha=0.15),
    ]

    comp1 = runner.run_benchmark(strategies=strategies, dataset=sim_dataset, benchmark_id="sim_run_1")
    comp2 = runner.run_benchmark(strategies=strategies, dataset=sim_dataset, benchmark_id="sim_run_2")

    assert comp1.status == "SIMULATED"
    assert comp1.dataset_status == "SIMULATED"
    assert comp1.ranked_by_mae == comp2.ranked_by_mae
    for r1, r2 in zip(comp1.results, comp2.results):
        assert r1.status == "SIMULATED"
        assert r1.metrics.mae == r2.metrics.mae
        assert r1.metrics.sample_count > 0

