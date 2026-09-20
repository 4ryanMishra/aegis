# AEGIS — On-Chain Oracle Cross-Checking & Risk-Resolution Layer

> **Multipli / VIT Vellore Hackathon 2026 Track: "Rethinking Blockchain Oracles"**

AEGIS is an **On-Chain Oracle Cross-Checking & Risk-Resolution Layer** designed for lending and collateralized stablecoin protocols (such as **Multipli RWAUSD vaults**). 

Instead of trusting an unverified delayed Oracle Security Module (OSM) or training speculative off-chain prediction models, AEGIS compares the upstream Multipli OSM against **6 established on-chain oracle networks** (Chainlink, Pyth, Chronicle, RedStone, Supra, and API3), executes **deterministic on-chain Price-Band Agreement Clustering ($\le 0.5\%$)**, and enforces **conservative risk resolution** ($P_{\text{FINAL}} = \min(P_{\text{OSM}}, P_{\text{CONSENSUS}})$ + dynamic LTV dampening) to definitively protect protocol solvency from bad debt.

---

## Quick Start — One-Click Demo Launcher (Windows PowerShell)

Launch the complete AEGIS demo environment (Python Backend API + Next.js Control Room Dashboard + Automatic Browser Launch):

```powershell
.\run-demo.ps1
```

- **Frontend Risk Control Room:** [http://localhost:3000](http://localhost:3000)
- **Backend Interactive Swagger API:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Run Comprehensive Verification Suite

Run all automated test suites (Python unit/integration tests, 5 deterministic scenarios, Next.js production build, and Solidity contracts):

```powershell
.\verify.ps1
```

---

## Core Thesis & The Multipli Problem

### The Problem with Delayed OSMs
Lending protocols commonly employ an **Oracle Security Module (OSM)** with a mandatory delay window (e.g. 60 minutes) to protect against single-block flash-loan manipulation. However, this introduces a critical systemic risk:

1. **Staleness During Flash Drops:** If the collateral asset plunges (e.g., Gold drops \$4,380 $\to$ \$4,050 in 15 minutes), the delayed OSM remains stale at \$4,380.00 for the remainder of the 60-minute buffer.
2. **Undercollateralized Borrow Exploitation:** An attacker can deposit suddenly devalued collateral at the inflated \$4,380 valuation and borrow maximum RWAUSD stablecoins. When the delayed OSM eventually updates to \$4,050, the position is hopelessly underwater, leaving the protocol with **irrecoverable bad debt**.
3. **Feed Dislocation & Stalls:** If an upstream oracle node stalls or experiences network partition, the protocol has no native on-chain mechanism to detect that its price has detached from broader DeFi consensus.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WITHOUT AEGIS (Traditional Delayed OSM)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Real Market:       $4,050 ─────────── (Flash drop)                         │
│  Multipli OSM:      $4,380 ─────────── (Stale for 60 minutes)               │
│  Attacker Action:   Deposits 10 oz Gold ($40,500 real value)                │
│                     Borrows against $43,800 valuation @ 80% LTV = $35,040   │
│  True Collateral:   $40,500 < $35,040 / 0.85 = INSOLVENT (BAD DEBT CREATED) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The AEGIS Solution: Cross-Oracle Agreement & Risk Resolution
AEGIS solves this without replacing existing oracles and without black-box predictive AI:

1. **Multi-Oracle Ingestion:** Concurrently reads 7 on-chain feeds (Multipli OSM + Chainlink, Pyth, Chronicle, RedStone, Supra, API3).
2. **Deterministic Price-Band Clustering:** Groups independent feeds into agreement clusters ($\le 0.5\%$ spread) and derives the DeFi consensus median ($P_{\text{CONSENSUS}}$).
3. **Quantified Multipli Deviation:** Calculates $\text{multipliDeviation} = |P_{\text{OSM}} - P_{\text{CONSENSUS}}| / P_{\text{CONSENSUS}}$.
4. **Conservative Valuation & LTV Dampening:**
   - When Multipli is stale/elevated, AEGIS immediately overrides valuation:
     $$P_{\text{FINAL}} = \min(P_{\text{OSM}}, P_{\text{CONSENSUS}})$$
   - Concurrently constrains downstream protocol LTV from **80% to 50%**.
   - Maximum borrow capacity on 10 oz Gold is restricted to \$20,254, saving the protocol from **\$14,786 in bad debt**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WITH AEGIS ACTIVE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Multipli OSM:      $4,380 (Stale)                                          │
│  Consensus Median:  $4,050.85 (Chainlink, Pyth, Chronicle, RedStone, Supra) │
│  AEGIS Decision:    DIVERGENT (Deviation: 8.13% >> 0.50% Threshold)         │
│  AEGIS Valuation:   min($4,380, $4,050.85) = $4,050.85                      │
│  Protocol Policy:   RESTRICTED Mode (LTV Capped at 50%)                     │
│  Borrow Capacity:   $20,254.25 (Collateral Value: $40,508.50)               │
│  Protocol Health:   100% SOLVENT — 0 BAD DEBT CREATED                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete End-to-End Pipeline

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          7 ON-CHAIN ORACLE FEEDS                          │
│   Multipli OSM │ Chainlink │ Pyth │ Chronicle │ RedStone │ Supra │ API3  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        CONSENSUS ENGINE (On-Chain)                        │
│   • Deterministic Price-Band Agreement Clustering (threshold <= 0.5%)      │
│   • Form Largest Agreement Cluster (e.g. 5/6 external oracles)            │
│   • Compute Consensus Median (P_CONSENSUS) & Agreement Spread (BPS)       │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      RISK DECISION ENGINE (On-Chain)                      │
│   • Compute Multipli Deviation: |P_OSM - P_CONSENSUS| / P_CONSENSUS       │
│   • Evaluate Status: NORMAL (<= 0.5%) | RESTRICTED (> 0.5%) | HALTED      │
│   • Enforce Conservative Valuation: P_FINAL = min(P_OSM, P_CONSENSUS)     │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      AEGIS PRICE ROUTER (IAEGISPriceFeed)                 │
│   • Exposes single authoritative price interface to DeFi protocols        │
│   • Returns (price, status, timestamp, maxLtvBps)                         │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                   DOWNSTREAM PROTOCOL (Multipli RWAUSD)                   │
│   • User Collateral: 10.0 oz Tokenized Gold (XAUt)                        │
│   • Valuation = 10 * P_FINAL                                              │
│   • Max Borrow Capacity = Valuation * maxLtv                              │
│   • Bad Debt Prevention: Enforced automatically on-chain                  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Canonical Demo Scenarios

AEGIS features 5 deterministic test scenarios validating full-spectrum oracle behaviors:

| Scenario | State / Input Condition | Consensus & Multipli Status | AEGIS Valuation | Protocol Action & Solvency Impact |
| :--- | :--- | :--- | :--- | :--- |
| **A: Normal Multi-Oracle Agreement** | All 6 oracles & Multipli agree at \$4,380.00 ($\text{spread} < 0.05\%$) | `ALIGNED` (Dev: 0.00%) | \$4,380.00 | **NORMAL** (80% LTV, \$35,040 max borrow, \$0 bad debt) |
| **B: Flash Drop (Multipli Stale)** | Market plunges to \$4,050; Multipli delayed OSM stays stale at \$4,380 | `DIVERGENT` (Dev: 8.13%) | **\$4,050.85** | **RESTRICTED** (50% LTV, \$20,254 max borrow, **\$14,786 bad debt prevented**) |
| **C: Poisoned Single Feed** | RedStone injects rogue \$5,200 quote; 5 other oracles agree at \$4,380 | `ALIGNED` (5/6 Agree) | \$4,380.00 | **NORMAL** (Rogue quote isolated to outlier cluster, 0 disruption) |
| **D: Multipli Outlier Dislocation** | Multipli spikes to \$4,700 while all 6 independent oracles agree at \$4,380 | `DIVERGENT` (Dev: 7.31%) | **\$4,380.00** | **RESTRICTED** (Overvaluation rejected; conservative pricing enforced) |
| **E: Oracle Fragmentation / Crash** | Extreme volatility splits oracles into disjoint clusters (no $\ge 3$ quorum) | `FRAGMENTED` | **REVERTS** | **HALTED** (Circuit breaker triggered; borrow operations frozen) |

---

## Smart Contract Architecture (`contracts/`)

The on-chain layer is implemented in production-grade Solidity (`^0.8.24`) tested via Foundry:

### Contract Inventory

| Contract | Category | Responsibility |
| :--- | :--- | :--- |
| [`IOracleAdapter.sol`](file:///d:/Projects/aegis/contracts/src/interfaces/IOracleAdapter.sol) | Interface | Unified on-chain oracle adapter interface: `readObservation() -> (price, updatedAt, status, source)`. |
| [`OracleRegistry.sol`](file:///d:/Projects/aegis/contracts/src/OracleRegistry.sol) | Core Registry | Registers and configures all external oracle adapters and Multipli OSM feeds per asset. |
| [`ConsensusEngine.sol`](file:///d:/Projects/aegis/contracts/src/ConsensusEngine.sol) | Core Math | On-chain deterministic price-band agreement clustering ($\le 0.5\%$), cluster selection, and median computation. |
| [`RiskDecisionEngine.sol`](file:///d:/Projects/aegis/contracts/src/RiskDecisionEngine.sol) | Core Policy | Computes Multipli deviation, evaluates oracle status, enforces $P_{\text{FINAL}} = \min(P_{\text{OSM}}, P_{\text{CONSENSUS}})$, and sets dynamic LTV limits. |
| [`AEGISPriceRouter.sol`](file:///d:/Projects/aegis/contracts/src/AEGISPriceRouter.sol) | Interface Hub | Unified price router implementing `IAEGISPriceFeed` for downstream protocol queries. |
| [`MockOracleFeeds.sol`](file:///d:/Projects/aegis/contracts/src/mocks/MockOracleFeeds.sol) | Test Infrastructure | High-fidelity mocks for Chainlink AggregatorV3, Pyth, Chronicle, RedStone, Supra, API3, and Multipli OSM. |
| [`ChainlinkAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/ChainlinkAdapter.sol) | Adapter | Normalizes Chainlink 8-decimal quotes to 18-decimal WAD with staleness checks. |
| [`PythAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/PythAdapter.sol) | Adapter | Normalizes Pyth exponent-scaled quotes and confidence intervals to 18-decimal WAD. |
| [`ChronicleAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/ChronicleAdapter.sol) | Adapter | Interfaces MakerDAO/Chronicle Scribe feeds with 18-decimal WAD. |
| [`RedStoneAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/RedStoneAdapter.sol) | Adapter | Gas-optimized RedStone payload decoder with freshness validation. |
| [`SupraAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/SupraAdapter.sol) | Adapter | Normalizes Supra Dora oracle quotes to 18-decimal WAD. |
| [`API3Adapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/API3Adapter.sol) | Adapter | Ingests API3 dAPI observations with heartbeat checks. |
| [`MultipliAdapter.sol`](file:///d:/Projects/aegis/contracts/src/adapters/MultipliAdapter.sol) | Adapter | Ingests delayed Multipli OSM prices with status flags. |

---

## Institutional Risk Control Room UI (`apps/web/`)

The AEGIS web interface is a modern Next.js 14 / Tailwind CSS application tailored for protocol risk officers and hackathon evaluators:

1. **Top Price Comparison Strip:** Displays live Multipli OSM, Consensus Median, Reference Spot, and AEGIS Final Valuation with live deviation badges.
2. **Oracle Feed Matrix:** Complete tabular view of all 7 oracle sources (Source, Network, Type, Reported Price, Age/Latency, Heartbeat, Status, Cluster Assignment).
3. **Consensus Telemetry Panel:** Real-time metrics on Consensus Median, Agreeing Cluster Size, Agreement Spread (BPS), Multipli Deviation %, and Quorum Status.
4. **"Why AEGIS Decided This" Audit Rationale Card:** Interactive mathematical proof showing exact calculation steps, agreement cluster membership, deviation analysis, and bad debt impact.
5. **Downstream RWAUSD Vault:** Interactive collateral position (10 oz Tokenized Gold XAUt) showing collateral valuation, max borrow capacity, debt outstanding, current LTV, liquidation threshold, and bad debt prevented.
6. **Live Multi-Line Comparison Chart:** Continuous streaming time-series tracking Multipli OSM (stepped line), Consensus Median (with $\pm 0.5\%$ agreement band), and Spot Reference.
7. **5-Step Causal Pipeline:** Visual flowchart tracking data from Feed Ingestion $\to$ Band Clustering $\to$ Consensus $\to$ Risk Decision $\to$ Protocol Vault.

---

## Verification & Testing

AEGIS enforces 100% test pass rate across all software layers:

```bash
# 1. Run all Python unit and integration tests (54/54 PASS)
python -m pytest

# 2. Run the 5 canonical demo scenarios via Python CLI (5/5 PASS)
python -m packages.client.scenario_runner --all

# 3. Build the Next.js web application (0 errors, 0 lint/type issues)
npm --prefix apps/web run build

# 4. Run all Solidity smart contract suites in Foundry (88/88 PASS across 14 suites)
cd contracts
forge test -vvv
```

---

## Running the Demo

### Method 1: One-Click PowerShell Launcher (Recommended)
```powershell
.\run-demo.ps1
```

### Method 2: Manual Start
```bash
# Terminal 1: Start Backend API
python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Next.js Frontend
cd apps/web
npm run dev
```

Navigate to [http://localhost:3000](http://localhost:3000) to inspect the Oracle Control Room.

---

## License & Attribution

AEGIS is open-source research and engineering developed for the **Multipli / VIT Vellore Hackathon 2026** under the *"Rethinking Blockchain Oracles"* track.
