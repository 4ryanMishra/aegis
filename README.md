# AEGIS — Adaptive Oracle Verification Engine

AEGIS is a research-grade MVP for the Rethinking Blockchain Oracles track. It repurposes a delayed oracle window into a structured verification process.

### Core Oracle Values
- `P_OSM`: delayed baseline oracle value exposed by the existing OSM after its scheduled delay.
- `P_DEC`: aggregated evidence product deterministically computed from independent validator submissions across methodology lanes (not simply a fixed median):
  $$\text{methodology computation} \longrightarrow \text{validator evidence} \longrightarrow \text{deterministic cross-validator aggregation} \longrightarrow P_{DEC}$$
- `P_MARKET`: independent terminal market observation attested at the close of the verification window.
- `P_FINAL`: single verified authoritative price exposed to the protocol through one stable price interface.

The MVP compares these values, exposes provenance and evidence, detects suspicious deviations, and demonstrates the collateral-value impact of a safer decision policy.

### Five Methodology Lanes
AEGIS organizes validator intelligence into five methodology lanes, each capable of being operated by multiple independent validator nodes:
1. **Lane 1:** Recursive 1D Kalman + Mahalanobis Innovation Gating
2. **Lane 2:** Huber M-Estimation
3. **Lane 3:** Jensen-Shannon Divergence
4. **Lane 4:** Ornstein-Uhlenbeck RWA Residual Analysis
5. **Lane 5:** Page CUSUM Sequential Drift Detection

*(MVP limitation: for prototype demonstration, one simulated node per methodology lane is operated, but the architecture decouples methodology definitions from node infrastructure to support multiple operators per lane.)*

## Important
This repository intentionally separates:
- verified Multipli facts;
- team-provided behavior descriptions;
- project assumptions;
- simulated prototype behavior;
- research methodologies awaiting validation.

Do not invent missing Multipli implementation details.

## Architecture & Integration
AEGIS sits **after / above** the existing Oracle Security Module (OSM).

> **Core Axiom:** AEGIS does not replace the OSM queue and does not insert validator predictions into it. AEGIS consumes the delayed OSM value and verifies it through a separate decentralized evidence round before exposing a final protocol price.

The OSM queue remains untouched, executing its single-value delay mechanism ($P_{OSM}$). Concurrently, AEGIS coordinates an independent on-chain verification round aggregating evidence across the five methodology lanes ($P_{DEC}$) and verifying terminal market attestations ($P_{MARKET}$) to resolve a single verified protocol price ($P_{FINAL}$). Downstream protocol contracts (Ledger, Collateral Adapters) query this finalized price through one stable price interface.

For the complete technical specification, see [`docs/AEGIS_SOLIDITY_OSM_INTEGRATION.md`](docs/AEGIS_SOLIDITY_OSM_INTEGRATION.md).

## Start
See [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) and [`docs/AEGIS_SOLIDITY_OSM_INTEGRATION.md`](docs/AEGIS_SOLIDITY_OSM_INTEGRATION.md).
