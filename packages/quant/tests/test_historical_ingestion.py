"""
Unit and Integration Tests for Phase 2B Historical Market Data Ingestion & Replay.
Tests:
- Chronological sorting and monotonicity verification
- Duplicate timestamp handling policies (KEEP_FIRST, KEEP_LAST, AVERAGE, ERROR)
- Missing interval and gap auditing
- Timezone normalization across Unix ms, Unix sec, and ISO-8601 offsets
- Point-in-time anti-leakage boundaries
- Exact 1-hour target alignment (t_now + 3600s)
- Deterministic replay reproducibility
- Invalid, negative, and zero price rejection
- Dataset manifest completeness and SHA-256 verification
- Binance Vision public kline archive preset parsing
"""

import pytest
import hashlib
from datetime import datetime, timezone

from packages.quant.src.models import (
    HistoricalMarketObservation,
    DatasetManifest,
    DataQualityReport,
)
from packages.quant.src.ingestion import (
    CSVIngestionReader,
    ColumnMapping,
    DuplicateTimestampPolicy,
    parse_timestamp_to_utc_seconds,
    compute_content_sha256,
)
from packages.quant.src.dataset import HistoricalReplayDataset
from packages.quant.src.baseline_strategies import NaivePersistenceStrategy
from packages.quant.src.backtest import RollingBacktestEngine


def test_parse_timestamp_to_utc_seconds():
    """Verify normalization across Unix seconds, ms, and ISO-8601 offsets."""
    # 1. Unix seconds
    assert parse_timestamp_to_utc_seconds(1774000000) == 1774000000
    assert parse_timestamp_to_utc_seconds("1774000000") == 1774000000

    # 2. Unix milliseconds (> 1e11)
    assert parse_timestamp_to_utc_seconds(1774000000000) == 1774000000
    assert parse_timestamp_to_utc_seconds("1774000000000") == 1774000000

    # 3. ISO-8601 UTC with Z
    iso_utc = "2026-03-20T10:00:00Z"
    expected_utc = int(datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc).timestamp())
    assert parse_timestamp_to_utc_seconds(iso_utc) == expected_utc

    # 4. ISO-8601 with offset +05:30 (e.g., IST)
    iso_offset_plus = "2026-03-20T15:30:00+05:30"
    assert parse_timestamp_to_utc_seconds(iso_offset_plus) == expected_utc

    # 5. ISO-8601 with offset -05:00 (e.g., EST)
    iso_offset_minus = "2026-03-20T05:00:00-05:00"
    assert parse_timestamp_to_utc_seconds(iso_offset_minus) == expected_utc

    # 6. Invalid timestamp string raises ValueError
    with pytest.raises(ValueError):
        parse_timestamp_to_utc_seconds("not-a-timestamp")


def test_invalid_negative_zero_observations_rejected():
    """Verify invalid, negative, or zero price observations are strictly dropped."""
    csv_data = """timestamp,price,volume
1774000000,95.50,100
1774000060,0.0,50
1774000120,-12.30,40
1774000180,corrupted_price,20
1774000240,96.20,110
corrupt_ts,96.50,30
"""
    dataset = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="test_filter_invalid",
        asset="XAU/USD",
        source="test_exchange_feed",
        status="SIMULATED",
        sampling_interval_seconds=60,
    )

    # Only 2 rows valid: 1774000000 (95.50) and 1774000240 (96.20)
    assert len(dataset) == 2
    assert dataset.observations[0].price == 95.50
    assert dataset.observations[1].price == 96.20

    # Verify quality report
    report = dataset.quality_report
    assert report is not None
    assert report.invalid_prices_count == 4
    assert report.valid_count == 2
    assert report.observation_count == 6


def test_chronological_ordering_and_monotonicity():
    """Verify out-of-order raw CSV data is sorted strictly into ascending order."""
    csv_data = """timestamp,price,volume
1774000180,96.00,100
1774000060,95.20,120
1774000000,95.00,110
1774000120,95.80,130
"""
    dataset = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="test_order",
        asset="XAU/USD",
        source="test_exchange_feed",
        status="SIMULATED",
        sampling_interval_seconds=60,
    )

    timestamps = [obs.timestamp for obs in dataset.observations]
    assert timestamps == [1774000000, 1774000060, 1774000120, 1774000180]
    # Check strict monotonicity of dataset
    for i in range(len(dataset.observations) - 1):
        assert dataset.observations[i].timestamp < dataset.observations[i + 1].timestamp


def test_duplicate_timestamp_handling():
    """Verify duplicate timestamp policies: KEEP_FIRST, KEEP_LAST, AVERAGE, ERROR."""
    csv_data = """timestamp,price,volume
1774000000,95.00,100
1774000060,95.20,100
1774000060,95.80,200
1774000120,96.00,150
"""
    # 1. KEEP_FIRST: retains 95.20
    ds_first = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="ds_first",
        asset="XAU/USD",
        source="test_feed",
        duplicate_policy=DuplicateTimestampPolicy.KEEP_FIRST,
    )
    assert len(ds_first) == 3
    assert ds_first.observations[1].price == 95.20
    assert ds_first.quality_report.dropped_duplicates == 1

    # 2. KEEP_LAST: retains 95.80
    ds_last = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="ds_last",
        asset="XAU/USD",
        source="test_feed",
        duplicate_policy=DuplicateTimestampPolicy.KEEP_LAST,
    )
    assert len(ds_last) == 3
    assert ds_last.observations[1].price == 95.80
    assert ds_last.quality_report.dropped_duplicates == 1

    # 3. AVERAGE: (95.20 + 95.80) / 2 = 95.50
    ds_avg = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="ds_avg",
        asset="XAU/USD",
        source="test_feed",
        duplicate_policy=DuplicateTimestampPolicy.AVERAGE,
    )
    assert len(ds_avg) == 3
    assert ds_avg.observations[1].price == 95.50
    assert ds_avg.quality_report.dropped_duplicates == 1

    # 4. ERROR: raises ValueError
    with pytest.raises(ValueError, match="Duplicate timestamp"):
        CSVIngestionReader.read_from_text(
            csv_text=csv_data,
            dataset_id="ds_err",
            asset="XAU/USD",
            source="test_feed",
            duplicate_policy=DuplicateTimestampPolicy.ERROR,
        )


def test_missing_intervals_and_gap_reporting():
    """Verify gap detection and coverage percentage calculation."""
    # 1-minute ticks with an 8-minute gap between t=180 and t=660
    # Expected ticks from 0 to 720: (720 - 0) // 60 + 1 = 13 ticks
    csv_data = """timestamp,price
1774000000,95.0
1774000060,95.1
1774000120,95.2
1774000180,95.3
1774000660,95.9
1774000720,96.0
"""
    dataset = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="test_gaps",
        asset="XAU/USD",
        source="gap_test_feed",
        sampling_interval_seconds=60,
    )

    report = dataset.quality_report
    assert report is not None
    assert len(report.gaps) == 1
    gap = report.gaps[0]
    assert gap["start_ts"] == 1774000180
    assert gap["end_ts"] == 1774000660
    assert gap["duration_seconds"] == 480
    assert gap["missing_intervals"] == 7  # 480 // 60 - 1 = 7 missing 1m bars
    assert report.expected_intervals_count == 13
    assert report.valid_count == 6
    # 6 / 13 * 100 = 46.15%
    assert 46.0 <= report.coverage_percentage <= 46.3


def test_point_in_time_anti_leakage_and_target_alignment():
    """
    Verify point-in-time anti-leakage boundaries and exact 1-hour target alignment (t + 3600s).
    """
    # Create 3 hours of 1-minute observations
    base_ts = 1774000000
    n_minutes = 180
    rows = ["timestamp,price"]
    for i in range(n_minutes):
        ts = base_ts + i * 60
        price = 100.0 + i * 0.10
        rows.append(f"{ts},{price:.2f}")

    dataset = CSVIngestionReader.read_from_text(
        csv_text="\n".join(rows),
        dataset_id="test_anti_leakage",
        asset="XAU/USD",
        source="synthetic_test_feed",
        status="SIMULATED",
        sampling_interval_seconds=60,
    )

    # 1. Test get_observations_up_to guarantees
    t_query = base_ts + 3600
    history = dataset.get_observations_up_to(t_query)
    assert len(history) == 61  # minute 0 to 60 inclusive
    assert max(o.timestamp for o in history) == t_query
    assert all(o.timestamp <= t_query for o in history)

    # 2. Test get_observation_at exact one-hour alignment
    t_target = t_query + 3600
    target_obs = dataset.get_observation_at(t_target, tolerance_sec=60)
    assert target_obs is not None
    assert target_obs.timestamp == t_target
    assert target_obs.price == round(100.0 + 120 * 0.10, 2)

    # 3. Rolling backtest engine verification
    engine = RollingBacktestEngine(
        horizon_seconds=3600,
        rolling_step_seconds=900,
        warmup_seconds=3600,
    )
    strat = NaivePersistenceStrategy()
    result = engine.run(strategy=strat, dataset=dataset)

    assert result.status == "SIMULATED"
    assert result.dataset_id == "test_anti_leakage"
    assert result.source == "synthetic_test_feed"
    assert result.horizon_seconds == 3600
    assert result.metrics.sample_count > 0


def test_deterministic_replay():
    """Verify that multiple replayed evaluations on the same dataset yield identical results."""
    base_ts = 1774000000
    rows = ["timestamp,price"]
    for i in range(120):
        ts = base_ts + i * 60
        price = 100.0 + (i % 5) * 0.5
        rows.append(f"{ts},{price:.2f}")

    dataset = CSVIngestionReader.read_from_text(
        csv_text="\n".join(rows),
        dataset_id="test_deterministic",
        asset="XAU/USD",
        source="test_feed",
        status="REPLAY",
    )

    engine = RollingBacktestEngine(
        horizon_seconds=1800,
        rolling_step_seconds=300,
        warmup_seconds=1800,
    )
    strat = NaivePersistenceStrategy()

    run1 = engine.run(strat, dataset)
    run2 = engine.run(strat, dataset)

    assert run1.metrics.mae == run2.metrics.mae
    assert run1.metrics.rmse == run2.metrics.rmse
    assert run1.metrics.sample_count == run2.metrics.sample_count
    assert run1.dataset_status == "REPLAY"


def test_dataset_manifest_and_sha256_checksum():
    """Verify DatasetManifest fields, status constraints, and content SHA-256 hash."""
    csv_data = "timestamp,price\n1774000000,95.0\n1774000060,95.5\n"
    expected_sha256 = hashlib.sha256(csv_data.encode("utf-8")).hexdigest()

    dataset = CSVIngestionReader.read_from_text(
        csv_text=csv_data,
        dataset_id="manifest_test_ds",
        asset="PAXG/USDT",
        source="binance_vision_public_archive",
        status="SIMULATED",
        source_url="https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip",
        sampling_interval_seconds=60,
    )

    manifest = dataset.manifest
    assert manifest is not None
    assert manifest.dataset_id == "manifest_test_ds"
    assert manifest.asset == "PAXG/USDT"
    assert manifest.source == "binance_vision_public_archive"
    assert manifest.timezone == "UTC"
    assert manifest.status == "SIMULATED"
    assert manifest.checksum_sha256 == expected_sha256
    assert manifest.start_timestamp == 1774000000
    assert manifest.end_timestamp == 1774000060


def test_binance_vision_preset_reader():
    """Verify preset reader for Binance Vision headerless 1-minute klines format."""
    # Binance format: open_time, open, high, low, close, volume, close_time, quote_asset_volume, trades, ...
    binance_csv = """1704067200000,2065.50,2066.00,2064.50,2065.80,12.5,1704067259999,25822.5,45,6.2,12807.9,0
1704067260000,2065.80,2067.10,2065.20,2066.90,18.2,1704067319999,37617.5,60,9.1,18808.7,0
"""
    dataset = CSVIngestionReader.read_binance_vision_klines(
        csv_text_or_path=binance_csv,
        asset="PAXG/USDT",
        dataset_id="binance_paxgusdt_jan2024_1m",
        status="SIMULATED"
    )

    assert len(dataset) == 2
    assert dataset.status == "SIMULATED"
    assert dataset.asset == "PAXG/USDT"
    assert dataset.source == "binance_vision_public_archive"
    assert dataset.observations[0].timestamp == 1704067200  # Unix ms -> Unix s
    assert dataset.observations[0].price == 2065.80       # close price
    assert dataset.observations[0].volume == 12.5
    assert dataset.observations[1].timestamp == 1704067260
    assert dataset.observations[1].price == 2066.90
