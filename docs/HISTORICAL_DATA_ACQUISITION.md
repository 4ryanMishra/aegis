# AEGIS Historical Market Data Acquisition & Ingestion Guide

## 1. Governance & Provenance Rules

Every historical dataset ingested into the AEGIS benchmark and replay engine must strictly adhere to the project's data provenance and non-hallucination rules:

1. **Explicit Status Tagging**: Every dataset and observation must carry an immutable status:
   - `LIVE`: Streamed in real time from live socket/polling infrastructure.
   - `HISTORICAL`: Ingested from unauthenticated public archives or historical market records via public download without synthetic modification.
   - `REPLAY`: Historical data currently being streamed or iterated through the evaluation engine.
   - `SIMULATED`: Generated via mathematical or synthetic models (e.g., Ornstein-Uhlenbeck test fixtures).
2. **Off-Chain Source Classification**: All centralized exchange records (Binance, Coinbase, Kraken, etc.) and aggregators (CoinGecko, Kaiko) are **OFF-CHAIN**. They must never be described or labeled as "on-chain" data.
3. **No Synthetic Substitution**: Real datasets must never be silently substituted with synthetic data.
4. **Cryptographic Provenance**: Every ingested file must undergo **SHA-256 checksum verification** against published digests, with the digest preserved in the `DatasetManifest`.
5. **Point-in-Time Anti-Leakage**: Replay interfaces must guarantee that validators evaluating at time $t$ can never inspect observations with $t_{\text{obs}} > t$.

---

## 2. Target Asset & Data Source

PAXG/USDT is an empirical proxy for gold-linked RWA/oracle research. It is NOT claimed to be Multipli's production collateral price or oracle feed.

- **Primary Historical Provider**: **Binance Public Data Vision Archive**
- **Access Level**: **Unauthenticated public archive** (public download). **No API key, credentials, or paid subscription required.**
- **Integrity**: **SHA-256 checksum verification** against published digests.
- **Licensing/Terms**: Binance Open Data Archive for academic and analytical research.
- **Granularity**: 1-minute ($1m$) OHLCV klines.

---

## 3. Step-by-Step Acquisition Procedure

### Step 1: Select Target Period
Identify the monthly or daily archive for PAXG/USDT.
Example: January 2024 monthly 1-minute klines archive:
```
https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip
```
The official SHA-256 checksum provided by the archive is:
```
https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip.CHECKSUM
```

### Step 2: Download the Archive & Checksum (Public Download)
Using curl or browser:
```bash
# Create local data directory (git-ignored)
mkdir -p data/historical

# Download zip file and checksum via public download
curl -O https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip
curl -O https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip.CHECKSUM
```

### Step 3: SHA-256 Checksum Verification
Verify the public download matches the provider's published SHA-256 digest:

**On Linux/macOS:**
```bash
sha256sum -c PAXGUSDT-1m-2024-01.zip.CHECKSUM
```

**On Windows (PowerShell):**
```powershell
Get-FileHash PAXGUSDT-1m-2024-01.zip -Algorithm SHA256
Get-Content PAXGUSDT-1m-2024-01.zip.CHECKSUM
```

### Step 4: Extract the CSV
Extract the `.zip` archive into the target folder:
```bash
unzip PAXGUSDT-1m-2024-01.zip -d data/historical/
```
The extracted file will be:
`data/historical/PAXGUSDT-1m-2024-01.csv`

---

## 4. Binance Vision Raw CSV Format Reference

Binance Vision kline files are headerless CSVs with the following column positions:
```
Col 0:  Open time (Unix milliseconds UTC)
Col 1:  Open price (float)
Col 2:  High price (float)
Col 3:  Low price (float)
Col 4:  Close price (float) -> Used as primary execution price
Col 5:  Volume (float)
Col 6:  Close time (Unix milliseconds UTC)
Col 7:  Quote asset volume (float)
Col 8:  Number of trades (integer)
Col 9:  Taker buy base asset volume (float)
Col 10: Taker buy quote asset volume (float)
Col 11: Ignore
```

---

## 5. Ingestion & Quality Audit via AEGIS Quant

Run the ingestion reader directly in Python:

```python
from pathlib import Path
from packages.quant.src import (
    CSVIngestionReader,
    ValidatorBenchmarkRunner,
    NaivePersistenceStrategy,
    SimpleMovingAverageStrategy,
    ExponentialMovingAverageStrategy,
)

# 1. Ingest and validate historical file
csv_path = Path("data/historical/PAXGUSDT-1m-2024-01.csv")
dataset = CSVIngestionReader.read_binance_vision_klines(
    csv_text_or_path=csv_path,
    asset="PAXG/USDT",
    dataset_id="paxg_usdt_binance_jan2024_1m",
    source_url="https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/1m/PAXGUSDT-1m-2024-01.zip"
)

# 2. Inspect Data Quality Audit
report = dataset.quality_report
print(f"Total Observations : {report.observation_count}")
print(f"Valid Retained     : {report.valid_count}")
print(f"Duplicates Dropped : {report.dropped_duplicates}")
print(f"Invalid Prices     : {report.invalid_prices_count}")
print(f"Coverage Ratio     : {report.coverage_percentage}%")
print(f"Gaps Detected      : {len(report.gaps)}")
print(f"SHA-256 Checksum   : {dataset.manifest.checksum_sha256}")

# 3. Run Benchmark across candidate validator methodologies
runner = ValidatorBenchmarkRunner(
    horizon_seconds=3600,       # 1-hour verification window
    rolling_step_seconds=900,   # Step every 15 minutes
    warmup_seconds=3600         # 1-hour initial warmup
)

strategies = [
    NaivePersistenceStrategy(),
    SimpleMovingAverageStrategy(window_points=60),
    ExponentialMovingAverageStrategy(alpha=0.05),
]

comparison = runner.run_benchmark(strategies=strategies, dataset=dataset)
print(runner.format_markdown_table(comparison))
```

---

## 6. Audit & Archival Rules

- **Do Not Commit Large Raw CSVs**: Historical data files (`.csv`, `.zip`, `.parquet`) must remain in `data/historical/` or another git-ignored directory to keep the repository lightweight.
- **Commit Manifests**: The resulting `DatasetManifest` and `DataQualityReport` JSON objects can be committed to document benchmark runs.
- **License Compliance**: Do not re-distribute commercial feeds (e.g., Bloomberg, Refinitiv) without express redistributable licensing.
