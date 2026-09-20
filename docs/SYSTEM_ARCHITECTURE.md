# AEGIS MVP System Architecture

## 1. Core Canonical Architecture

AEGIS repurposes a delayed oracle window into a structured multi-lane statistical verification process:

```text
Existing OSM
    ↓
P_OSM
    ↓
AEGIS Verification Window
    ↓
Five Methodology Lanes
    ↓
Validator Evidence
    ↓
P_DEC + P_MARKET + P_OSM
    ↓
Evidence Engine
    ↓
Decision Engine
    ↓
P_FINAL
    ↓
Price Interface
    ↓
Protocol / Ledger
```

**Canonical Boundary Rule:**
> **"AEGIS does not replace the OSM queue and does not insert validator predictions into it. AEGIS consumes the delayed OSM value and verifies it through a separate decentralized evidence round before exposing a final protocol price."**

**Core Terminology Invariant:**
> "Five methodology lanes, each capable of being operated by multiple independent validator nodes."
> *(Current MVP simulation: 1 simulated node per lane. Multiple independent validator operators are a future architecture).*

**Core Solvency Axiom:**
> *"AEGIS protects against oracle inconsistency and manipulation; protocol solvency depends on liquidations, volatility, and protocol parameters."*

## 2. Value Definitions

### P_OSM
The delayed value exposed by the existing Multipli OSM/oracle flow after its scheduled delay buffer.

### P_DEC
The decentralized reference value generated from eligible price-estimating validator submissions (Lanes 1 & 2):
$$\text{methodology computation} \longrightarrow \text{validator evidence} \longrightarrow \text{deterministic cross-validator aggregation} \longrightarrow P_{DEC}$$
*(Note: Lanes 1 & 2 serve as genuine price estimators; Lanes 3, 4, and 5 produce structured diagnostic evidence consumed directly by the Evidence Engine).*

### P_MARKET
An independent terminal market observation attested at the close of the verification window ($T_1$).

### P_FINAL
Single verified authoritative price exposed to the protocol through one stable price interface.

## 3. Five Methodology Lanes & Role Classification

To preserve mathematical consistency, AEGIS explicitly differentiates between **Price Estimators** and **Diagnostic Evidence Lanes**:

### Price Estimators (Eligible for $P_{DEC}$)
1. **Lane 1 — Recursive 1D Kalman Filter + Mahalanobis Innovation Gating:**
   - **Role:** `PRICE_ESTIMATOR`
   - **Formulation:** Tracks state $\hat{x}_{t|t}$ with innovation variance $S_t = P_{t|t-1} + R$ and Mahalanobis distance squared $D^2 = \nu_t^2 / S_t$.
   - **Gating Gate:** $\chi^2(1, 0.99) \approx 6.635$ ($\alpha=0.01$). Calibrated to prevent false rejections during volatile market periods ($D^2 \approx 4-5$) while gating extreme flash spikes ($D^2 \gg 10$).
2. **Lane 2 — Huber M-Estimation via IRLS:**
   - **Role:** `PRICE_ESTIMATOR`
   - **Formulation:** Computes robust location $\hat{\mu}$ using Huber loss ($k=1.345$) via Iteratively Reweighted Least Squares (IRLS). Downweights outliers without complete truncation.

### Diagnostic Evidence Lanes (Direct Evidence Engine Input)
3. **Lane 3 — Pairwise Jensen-Shannon Divergence (JSD):**
   - **Role:** `UNCERTAINTY_CONSENSUS_MEASURE`
   - **Formulation:** Evaluates symmetric divergence $D_{JS} \in [0, 1]$ over discrete probability grids across validator uncertainty distributions. Produces pairwise matrices and consensus disagreement scores.
4. **Lane 4 — Ornstein-Uhlenbeck RWA Residual Analysis:**
   - **Role:** `RWA_STRUCTURAL_CHECK`
   - **Formulation:** For anchored RWAs, tracks continuous-time spread $S_t = \ln(P_{spot}) - \ln(P_{anchor})$ under mean-reverting OU SDE. Standardized residual $|z_{OU}| \ge 3.5$ (under configured threshold) flags structural residual alerts / jump candidates. Returns `NOT_APPLICABLE` for non-RWA assets.
5. **Lane 5 — Page CUSUM Sequential Drift Detection:**
   - **Role:** `SEQUENTIAL_DRIFT_DETECTOR`
   - **Formulation:** Standardized price increment $y_k = (P_k - P_{k-1})/\sigma_k$. Two-sided sequential accumulators $S_k^+ = \max(0, S_{k-1}^+ + y_k - \kappa)$, $S_k^- = \max(0, S_{k-1}^- - y_k - \kappa)$ with slack $\kappa=0.5$ and decision threshold $h=4.0$. Detects persistent directional micro-drifts that evade point-in-time threshold checks.

## 4. Aggregation Layer (P_DEC)

The `P_DECAggregator` and on-chain `AggregatorLib` implement a **Two-Tier Hierarchical Aggregation** model supporting multiple independent validator operators per methodology lane:
1. **Tier 1 — Within-Lane Operator Consensus:**
   - For each price estimator lane (Lanes 1 & 2), collects all revealed operator estimates and uncertainty widths.
   - Computes canonical lane price $P_L$ via **robust median** of operator submissions.
   - Computes the **AEGIS canonical lane uncertainty/dispersion estimate** (conservative dispersion heuristic): $\sigma_L = \text{median}(\sigma_i) + \text{IQR}(P_i)$. This heuristic must not be described as a statistically exact standard deviation unless later calibration establishes that property; it serves as the robust weighting input for Tier 2 cross-lane synthesis, where operator disagreement inflates dispersion and down-weights that lane.
2. **Tier 2 — Cross-Lane Methodology Synthesis:**
   - Inverse-variance weighted blend across eligible price-estimator lanes:
     $$\lambda = \frac{1/\sigma_1^2}{1/\sigma_1^2 + 1/\sigma_2^2}, \quad P_{DEC} = \lambda P_1 + (1 - \lambda) P_2$$
   - Gating isolation: If Lane 1 is innovation-gated, $P_{DEC} = P_{\text{Huber}}$.
3. **Quorum & Lane Diversity Rules:**
   - **Applicability-Aware 3D Quorum:** requires configured minimum total reveals ($N_{\text{total}}$), configured distinct operator addresses ($N_{\text{operators}}$), and minimum distinct APPLICABLE methodology lanes ($N_{\text{lanes}} \ge 3$).
   - **Healthy Consensus Requirements:** requires $\ge 1$ active price-estimator lane and $\ge 2$ active/applicable diagnostic lanes.
   - **Asset-Specific Applicability:** Diagnostic lanes marked `NOT_APPLICABLE` (such as an OU lane for an asset lacking a mean-reverting reference peg) are not treated as failed validators and do not cause quorum failure.
   - A single lane cannot satisfy quorum alone under any circumstances.
4. **Diagnostic Exclusion:** Diagnostic lanes (Lanes 3, 4, 5) never enter $P_{DEC}$ pricing accumulators; their evidence feeds the Evidence Engine directly.

## 5. Evidence Layer (Evidence Engine)

At $T_1$, computes triangular deviations:
- $d_{osm, market} = \frac{|P_{OSM} - P_{MARKET}|}{P_{MARKET}}$
- $d_{dec, market} = \frac{|P_{DEC} - P_{MARKET}|}{P_{MARKET}}$
- $d_{osm, dec} = \frac{|P_{OSM} - P_{DEC}|}{\max(P_{DEC}, \epsilon)}$

Directly ingests diagnostic evidence payloads:
- Lane 1: $D^2$, threshold $6.635$, gating status
- Lane 2: Outlier count and downweighting weights
- Lane 3: JSD pairwise matrix and informational disagreement
- Lane 4: Standardized residual and jump candidate state
- Lane 5: Two-sided accumulators and sequential trip status

The output is an evidence record, not a claim of absolute truth.

## 6. Decision layer

Use a policy interface rather than hard-code a final-price formula:

```python
decide(osm, p_dec, p_market, evidence, config) -> Decision
```

The first demonstrator may implement `NEAREST_TO_MARKET` as an evaluation policy because it matches the team's current example. Label this explicitly as an MVP policy, not as a final production oracle rule.

Future policies may use credibility-weighted robust fusion and conservative risk bounds.

## 7. Blockchain Boundary (Phase 4B Solidity Layer)

The AEGIS on-chain verification layer provides EVM-native enforcement of the verification lifecycle, running concurrently within the existing OSM delay window ($T_0 \to T_1$):

```text
contracts/src/
├── interfaces/
│   ├── IAEGISPriceFeed.sol   (Canonical protocol price interface consumed by downstream dApps)
│   └── IOSM.sol              (Minimal read-only peek/read interface to the delayed baseline)
├── libraries/
│   ├── FixedPointMath.sol    (18-decimal WAD & BPS arithmetic, relative deviation)
│   └── AggregatorLib.sol     (Two-tier hierarchical aggregation: median + dispersion heuristic + inverse-variance)
├── ValidatorRegistry.sol     (Decoupled validator operators, lane roles 1-5)
├── MarketAttestor.sol        (EIP-712 terminal market attestation with replay & freshness bounds)
├── AEGISEvidenceEngine.sol   (Triangular deviations & compact anomaly bitmask compilation)
├── AEGISDecisionEngine.sol   (Deterministic safety policy matrix: P_FINAL, OracleStatus, ActionCode)
├── AEGISPriceRouter.sol      (Authoritative price store implementing IAEGISPriceFeed with staleness checks)
└── AEGISVerificationManager.sol (State machine coordinator, commit/reveal, 3D quorum, keeper finalizer)
```

### Core Invariants Guaranteed by Smart Contracts
1. **Zero Double-Delay:** Verification rounds open at $T_0$ when an observation enters the OSM delay queue. Commitments and reveals execute during the 1-hour delay. At $T_1$, when the OSM matures, keeper finalization reads $P_{OSM}$, verifies $P_{MARKET}$, aggregates $P_{DEC}$, evaluates evidence, and publishes $P_{FINAL}$ immediately with **zero added delay**.
2. **Strict Downstream Position:** AEGIS is downstream of the OSM in data flow. Validator submissions NEVER enter the OSM queue, and $P_{FINAL}$ is NEVER written back into the upstream OSM.
3. **Distinct Operator Identity Separation (Phase 4B.1):** Separates organizational identity (`operatorId`) from wallet addresses. Quorum evaluation strictly counts distinct `operatorId`s, preventing multi-wallet Sybil attacks from single entities. At most one submission per `(roundId, laneId, operatorId)` is admitted to lane aggregation.
4. **Snapshot-Bound Commit-Reveal (Phase 4B.1):** Commitments snapshot `operatorId` and `laneId`. Reveals enforce that validator status, `operatorId`, and `laneId` have not mutated mid-round. Payload hashes bind `(operatorId, laneId, price, uncertaintyValue, uncertaintyType, isGated, diagPayload, evidenceHash)`.
5. **Explicit Uncertainty Semantics (Phase 4B.1):** Enforces typed uncertainty via `UncertaintyType` (`CI95_HALF_WIDTH`, `ABSOLUTE_STD`, `EMPIRICAL_DISPERSION`, `SOURCE_CONFIDENCE`, `OTHER_UNSUPPORTED`). For `CI95_HALF_WIDTH`, exact Gaussian conversion $\sigma = (\text{uncertaintyValue} \times 100) / 196$ ($\sigma = \text{halfWidth} / 1.96$) is computed. Unsupported variants or mixed uncertainty semantics within a single lane are deterministically rejected.
6. **MarketAttestor Market Observer Trust Boundary (Phase 4B.1):** EIP-712 typed data signatures prove attestor identity, non-repudiation, and payload integrity. Market attestations are classified as external **Market Observers** (not infallible ground truth) and are triangulated against $P_{OSM}$ and $P_{DEC}$ by the Evidence and Decision Engines.
7. **Two-Tier Multi-Operator Aggregation:** Decouples operator count from methodology weight. Multiple operators per lane are synthesized into a canonical lane estimate via median price and conservative dispersion heuristic ($\sigma_L = \text{median}(\sigma_i) + \text{IQR}(P_i)$). Cross-lane synthesis blends price estimators inversely proportional to variance.
8. **Diagnostic Lane Exclusion:** Lanes 3, 4, and 5 produce evidence hashes and diagnostic flags only; their values never enter pricing accumulators.
9. **Applicability-Aware 3D Quorum:** Rounds require configured minimum total reveals ($N_{\text{total}}$), distinct operator identities ($N_{\text{operators}}$), and distinct applicable lanes ($N_{\text{lanes}} \ge 3$). An asset where OU analysis is marked `NOT_APPLICABLE` does not suffer quorum failure.
10. **Single Authoritative Price Interface:** Protocols consume exactly one method: `IAEGISPriceFeed.getPrice(bytes32 assetId) -> (uint256 price, OracleStatus status, uint256 timestamp)`.

## 9. End-to-End Integration & Testnet Prototype (Phase 4C)

The AEGIS Phase 4C prototype establishes a unified operational loop linking statistical methodology execution to on-chain protocol consumption:

```text
Historical / Live Tick Data
            ↓
ValidatorNodeClient (Python)
• Lane 1 (Kalman + Chi-squared gating)
• Lane 2 (Huber M-Estimation via IRLS)
• Lane 3 (JSD Pairwise Divergence)
• Lane 4 (Ornstein-Uhlenbeck RWA Spread Residuals)
• Lane 5 (Page CUSUM Cumulative Sequential Drift)
• Typed Uncertainty (CI95, std, dispersion)
            ↓
Keeper Orchestration Loop
• Opens verification round (createRound)
• Submits cryptographic commitments (commit)
• Reveals payloads after commit window (reveal)
• Attaches EIP-712 MarketAttestor signature
• Executes atomic finalization (finalizeRoundWithAttestation)
            ↓
AEGIS Verification Manager & Engines (Solidity)
• Validates 3D Quorum (reveals, operators, applicable lanes)
• Tier 1 Within-Lane Median & Dispersion Heuristic
• Tier 2 Cross-Lane Inverse-Variance Synthesis -> P_DEC
• Evaluates Triangular Evidence Matrix -> P_FINAL & OracleStatus
• Updates AEGISPriceRouter
            ↓
Downstream Protocol (MockRWAUSDProtocol)
• Evaluates borrow / liquidation capacity based on OracleStatus
• NORMAL: 80% LTV ($80k borrow per $100k collateral)
• RESTRICTED: 50% LTV + conservative haircut
• HALTED: Reverts operations, protecting solvency
```

## 10. Repository & Testing Status

- **Solidity Smart Contracts:** 77/77 tests passing (unit, adversarial security, invariant fuzzing, and end-to-end integration).
- **Off-Chain Quantitative Pipeline:** 64/64 pytest tests passing.
- **Frontend Institutional Dashboard:** Clean production build (`npm run build`).
