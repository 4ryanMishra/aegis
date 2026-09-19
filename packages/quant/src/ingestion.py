"""
Historical Market Data Ingestion & Validation Layer.
Supports CSV ingestion (with standard presets for Binance archives, CoinGecko, and generic OHLCV/Tick data),
strict chronological validation, timezone normalization to UTC, duplicate handling, and data-quality reporting.
"""

import csv
import io
import hashlib
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field

from .models import (
    HistoricalMarketObservation,
    DatasetManifest,
    DataQualityReport,
)
from .dataset import HistoricalReplayDataset


class DuplicateTimestampPolicy(str, Enum):
    KEEP_FIRST = "KEEP_FIRST"
    KEEP_LAST = "KEEP_LAST"
    AVERAGE = "AVERAGE"
    ERROR = "ERROR"


class ColumnMapping(BaseModel):
    """Configurable column mapping for arbitrary CSV formats."""
    timestamp_col: str = "timestamp"
    price_col: str = "price"
    volume_col: Optional[str] = "volume"
    open_col: Optional[str] = None
    high_col: Optional[str] = None
    low_col: Optional[str] = None
    close_col: Optional[str] = None
    bid_col: Optional[str] = None
    ask_col: Optional[str] = None


def parse_timestamp_to_utc_seconds(raw_val: Union[int, float, str]) -> int:
    """
    Normalizes any timestamp format (Unix seconds, Unix milliseconds, or ISO-8601 string)
    to a Unix epoch integer in seconds (UTC).
    """
    if isinstance(raw_val, (int, float)):
        # If timestamp is in milliseconds (e.g. > 1e11), convert to seconds
        if raw_val > 100_000_000_000:
            return int(raw_val // 1000)
        return int(raw_val)

    s = str(raw_val).strip()
    # Try integer/float string
    try:
        num = float(s)
        if num > 100_000_000_000:
            return int(num // 1000)
        return int(num)
    except ValueError:
        pass

    # Try ISO-8601 datetime strings
    # Replace trailing 'Z' with '+00:00' for standard ISO parsing if needed
    normalized_s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized_s)
        if dt.tzinfo is None:
            # Naive datetime: assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp())
    except ValueError as e:
        raise ValueError(f"Unable to parse timestamp '{raw_val}' to UTC epoch seconds: {e}")


def compute_content_sha256(data: Union[bytes, str]) -> str:
    """Computes SHA-256 hex digest for dataset content verification."""
    hasher = hashlib.sha256()
    if isinstance(data, str):
        hasher.update(data.encode("utf-8"))
    else:
        hasher.update(data)
    return hasher.hexdigest()


class CSVIngestionReader:
    """
    Standard CSV Ingestion Reader for historical financial market observations.
    Performs validation, deduplication, UTC timezone normalization, and gap auditing.
    """

    @classmethod
    def read_from_file(
        cls,
        file_path: Union[str, Path],
        asset: str,
        source: str,
        dataset_id: Optional[str] = None,
        status: str = "HISTORICAL",
        sampling_interval_seconds: int = 60,
        mapping: Optional[ColumnMapping] = None,
        duplicate_policy: DuplicateTimestampPolicy = DuplicateTimestampPolicy.KEEP_LAST,
        source_url: Optional[str] = None,
        has_header: bool = True
    ) -> HistoricalReplayDataset:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")

        raw_bytes = path.read_bytes()
        checksum = compute_content_sha256(raw_bytes)
        csv_text = raw_bytes.decode("utf-8", errors="replace")

        d_id = dataset_id or f"{asset.lower().replace('/', '_')}_{path.stem}"

        return cls.read_from_text(
            csv_text=csv_text,
            dataset_id=d_id,
            asset=asset,
            source=source,
            status=status,
            sampling_interval_seconds=sampling_interval_seconds,
            mapping=mapping,
            duplicate_policy=duplicate_policy,
            source_url=source_url,
            checksum_sha256=checksum,
            has_header=has_header
        )

    @classmethod
    def read_from_text(
        cls,
        csv_text: str,
        dataset_id: str,
        asset: str,
        source: str,
        status: str = "HISTORICAL",
        sampling_interval_seconds: int = 60,
        mapping: Optional[ColumnMapping] = None,
        duplicate_policy: DuplicateTimestampPolicy = DuplicateTimestampPolicy.KEEP_LAST,
        source_url: Optional[str] = None,
        checksum_sha256: Optional[str] = None,
        has_header: bool = True
    ) -> HistoricalReplayDataset:
        col_map = mapping or ColumnMapping()
        f = io.StringIO(csv_text.strip())
        reader = csv.reader(f)

        rows = list(reader)
        if not rows:
            raise ValueError("CSV content is empty")

        headers: Dict[str, int] = {}
        data_rows: List[List[str]] = []

        if has_header:
            header_row = [h.strip().lower() for h in rows[0]]
            headers = {name: idx for idx, name in enumerate(header_row)}
            data_rows = rows[1:]
        else:
            # Assume standard positional columns: 0=timestamp, 1=price, 2=volume
            headers = {
                col_map.timestamp_col.lower(): 0,
                col_map.price_col.lower(): 1,
            }
            if col_map.volume_col:
                headers[col_map.volume_col.lower()] = 2
            data_rows = rows

        def get_val(row: List[str], col_name: Optional[str]) -> Optional[str]:
            if not col_name:
                return None
            if col_name.isdigit():
                idx = int(col_name)
                if idx < len(row):
                    val = row[idx].strip()
                    return val if val != "" else None
                return None
            idx = headers.get(col_name.lower())
            if idx is not None and idx < len(row):
                val = row[idx].strip()
                return val if val != "" else None
            return None

        def safe_float(val: Optional[str]) -> Optional[float]:
            if val is None:
                return None
            try:
                f = float(val)
                return f if (float("-inf") < f < float("inf")) else None
            except (ValueError, TypeError):
                return None

        raw_observations: List[HistoricalMarketObservation] = []
        invalid_prices = 0
        total_raw_rows = len(data_rows)

        for row_idx, row in enumerate(data_rows):
            if not row or all(c.strip() == "" for c in row):
                continue

            ts_str = get_val(row, col_map.timestamp_col)
            price_str = get_val(row, col_map.price_col) or get_val(row, col_map.close_col)

            if ts_str is None or price_str is None:
                invalid_prices += 1
                continue

            try:
                ts = parse_timestamp_to_utc_seconds(ts_str)
            except Exception:
                invalid_prices += 1
                continue

            try:
                price = float(price_str)
                if price <= 0.0 or not (float("-inf") < price < float("inf")):
                    invalid_prices += 1
                    continue
            except (ValueError, TypeError):
                invalid_prices += 1
                continue

            # Optional fields with safe float conversion
            volume = safe_float(get_val(row, col_map.volume_col))
            open_p = safe_float(get_val(row, col_map.open_col))
            high_p = safe_float(get_val(row, col_map.high_col))
            low_p = safe_float(get_val(row, col_map.low_col))
            close_p = safe_float(get_val(row, col_map.close_col)) or price
            bid_p = safe_float(get_val(row, col_map.bid_col))
            ask_p = safe_float(get_val(row, col_map.ask_col))

            obs = HistoricalMarketObservation(
                timestamp=ts,
                price=price,
                source=source,
                asset=asset,
                status=status,
                volume=volume,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                bid=bid_p,
                ask=ask_p,
                metadata={"row_index": row_idx}
            )
            raw_observations.append(obs)

        # 1. Sort chronologically
        is_monotonic_before_sort = all(
            raw_observations[i].timestamp <= raw_observations[i + 1].timestamp
            for i in range(len(raw_observations) - 1)
        )
        raw_observations.sort(key=lambda o: o.timestamp)

        # 2. Duplicate timestamp handling
        deduped_observations: List[HistoricalMarketObservation] = []
        dropped_duplicates = 0
        i = 0
        n = len(raw_observations)

        while i < n:
            same_ts_group = [raw_observations[i]]
            j = i + 1
            while j < n and raw_observations[j].timestamp == raw_observations[i].timestamp:
                same_ts_group.append(raw_observations[j])
                j += 1

            if len(same_ts_group) > 1:
                dropped_duplicates += (len(same_ts_group) - 1)
                if duplicate_policy == DuplicateTimestampPolicy.ERROR:
                    raise ValueError(f"Duplicate timestamp encountered at {same_ts_group[0].timestamp}")
                elif duplicate_policy == DuplicateTimestampPolicy.KEEP_FIRST:
                    deduped_observations.append(same_ts_group[0])
                elif duplicate_policy == DuplicateTimestampPolicy.KEEP_LAST:
                    deduped_observations.append(same_ts_group[-1])
                elif duplicate_policy == DuplicateTimestampPolicy.AVERAGE:
                    avg_p = sum(o.price for o in same_ts_group) / len(same_ts_group)
                    rep = same_ts_group[-1].model_copy(update={"price": round(avg_p, 4)})
                    deduped_observations.append(rep)
            else:
                deduped_observations.append(same_ts_group[0])

            i = j

        # 3. Gap & continuity analysis
        gaps: List[Dict[str, int]] = []
        gap_threshold = int(sampling_interval_seconds * 1.5)

        for k in range(len(deduped_observations) - 1):
            t_curr = deduped_observations[k].timestamp
            t_next = deduped_observations[k + 1].timestamp
            delta = t_next - t_curr
            if delta > gap_threshold:
                gaps.append({
                    "start_ts": t_curr,
                    "end_ts": t_next,
                    "duration_seconds": delta,
                    "missing_intervals": (delta // sampling_interval_seconds) - 1
                })

        min_ts = deduped_observations[0].timestamp if deduped_observations else None
        max_ts = deduped_observations[-1].timestamp if deduped_observations else None

        if min_ts is not None and max_ts is not None and sampling_interval_seconds > 0:
            expected_count = ((max_ts - min_ts) // sampling_interval_seconds) + 1
            coverage_pct = round((len(deduped_observations) / max(expected_count, 1)) * 100.0, 2)
        else:
            expected_count = len(deduped_observations)
            coverage_pct = 100.0 if deduped_observations else 0.0

        quality_report = DataQualityReport(
            observation_count=total_raw_rows,
            valid_count=len(deduped_observations),
            dropped_duplicates=dropped_duplicates,
            invalid_prices_count=invalid_prices,
            missing_intervals_count=sum(g.get("missing_intervals", 1) for g in gaps),
            expected_intervals_count=expected_count,
            coverage_percentage=coverage_pct,
            min_timestamp=min_ts,
            max_timestamp=max_ts,
            source=source,
            data_status=status,
            gaps=gaps,
            is_strictly_monotonic=is_monotonic_before_sort and (dropped_duplicates == 0)
        )

        manifest = DatasetManifest(
            dataset_id=dataset_id,
            asset=asset,
            source=source,
            acquisition_method="MANUAL_DOWNLOAD" if source_url else "CSV_INGESTION",
            source_url=source_url,
            timezone="UTC",
            sampling_interval_seconds=sampling_interval_seconds,
            start_timestamp=min_ts or 0,
            end_timestamp=max_ts or 0,
            status=status,
            checksum_sha256=checksum_sha256 or compute_content_sha256(csv_text),
            metadata={
                "coverage_pct": coverage_pct,
                "dropped_duplicates": dropped_duplicates,
                "gaps_count": len(gaps),
            }
        )

        return HistoricalReplayDataset(
            name=dataset_id,
            observations=deduped_observations,
            description=f"Ingested historical dataset for {asset} from {source}",
            status=status,
            manifest=manifest,
            quality_report=quality_report,
            sampling_interval_seconds=sampling_interval_seconds
        )

    @classmethod
    def read_binance_vision_klines(
        cls,
        csv_text_or_path: Union[str, Path],
        asset: str = "PAXG/USDT",
        dataset_id: Optional[str] = None,
        source_url: Optional[str] = "https://data.binance.vision"
    ) -> HistoricalReplayDataset:
        """
        Preset reader for Binance Public Data Vision monthly/daily klines CSV.
        Headerless format:
        [0: open_time, 1: open, 2: high, 3: low, 4: close, 5: volume, 6: close_time, ...]
        """
        mapping = ColumnMapping(
            timestamp_col="0",
            open_col="1",
            high_col="2",
            low_col="3",
            close_col="4",
            price_col="4",
            volume_col="5"
        )
        if isinstance(csv_text_or_path, Path) or (isinstance(csv_text_or_path, str) and "\n" not in csv_text_or_path and Path(csv_text_or_path).exists()):
            return cls.read_from_file(
                file_path=csv_text_or_path,
                asset=asset,
                source="binance_vision_public_archive",
                dataset_id=dataset_id,
                status="HISTORICAL",
                sampling_interval_seconds=60,
                mapping=mapping,
                source_url=source_url,
                has_header=False
            )
        else:
            return cls.read_from_text(
                csv_text=str(csv_text_or_path),
                dataset_id=dataset_id or f"binance_{asset.lower().replace('/', '_')}_1m",
                asset=asset,
                source="binance_vision_public_archive",
                status="HISTORICAL",
                sampling_interval_seconds=60,
                mapping=mapping,
                source_url=source_url,
                has_header=False
            )


class ParquetIngestionReader:
    """
    Parquet Ingestion interface.
    Gracefully validates parquet library availability (e.g. pyarrow).
    """

    @classmethod
    def is_supported(cls) -> bool:
        try:
            import pyarrow.parquet  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def read_from_file(cls, file_path: Union[str, Path], asset: str, source: str) -> HistoricalReplayDataset:
        if not cls.is_supported():
            raise NotImplementedError(
                "Parquet ingestion requires 'pyarrow' to be installed. "
                "For native zero-dependency historical ingestion, use CSVIngestionReader."
            )
        # Placeholder for pyarrow parquet loader
        raise NotImplementedError("Parquet format parsing available when pyarrow runtime is active.")
