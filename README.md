# AEGIS — Adaptive Oracle Verification Engine

AEGIS is a research-grade MVP for the Rethinking Blockchain Oracles track. It repurposes a delayed oracle window into a structured, multi-lane cryptographic and statistical verification process.

## Canonical Architecture

AEGIS operates strictly after and outside the existing Oracle Security Module (OSM) pipeline:

```
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

> **Canonical Boundary Rule:**  
> **"AEGIS does not replace the OSM queue and does not insert validator predictions into it. AEGIS consumes the delayed OSM value and verifies it through a separate decentralized evidence round before exposing a final protocol price."**

### Core Oracle Values
- `P_OSM`: Delayed baseline oracle value exposed by the existing OSM after its scheduled delay buffer.
- `P_DEC`: Aggregated price reference product deterministically computed from eligible price-estimating validator lanes (uncertainty-weighted median blend of Lanes 1 & 2):
  $$\text{methodology computation} \longrightarrow \text{validator evidence} \longrightarrow \text{deterministic cross-validator aggregation} \longrightarrow P_{DEC}$$
  *(Note: Lanes 1 & 2 serve as genuine price estimators; Lanes 3, 4, and 5 provide non-price diagnostic evidence directly to the Evidence Engine).*
- `P_MARKET`: Independent terminal market observation attested at the close of the verification window ($T_1$).
- `P_FINAL`: Single verified authoritative price exposed to the protocol through one stable price interface.

> **Core Solvency Axiom:**
> *"AEGIS protects against oracle inconsistency and manipulation; protocol solvency depends on liquidations, volatility, and protocol parameters."*

---

## Five Methodology Lanes

AEGIS organizes verification intelligence into:

> **"Five methodology lanes, each capable of being operated by multiple independent validator nodes."**
> 
> *(Current MVP simulation: 1 simulated node per lane. The architecture explicitly decouples methodology mathematical specifications from validator operator keys and node infrastructure).*

### Methodology Role Classification

To preserve mathematical coherence, AEGIS explicitly differentiates between **Price Estimators** and **Diagnostic Evidence Lanes**:
- **Price Estimators (Lanes 1 & 2):** Produce continuous numeric price forecasts and robust central tendencies. Only eligible price estimators contribute to $P_{DEC}$.
- **Diagnostic Evidence Lanes (Lanes 3, 4, 5):** Produce distributional, structural, and sequential drift diagnostics (such as JSD divergence matrices, standardized RWA residuals, and cumulative drift accumulators). These are ingested directly by the Evidence Engine without artificial price coercion.

### Epistemic Foundation

> **"Each methodology is an evidence producer, not an unquestionable truth source."**
> 
> No single statistical model possesses perfect foresight or immunity to market dislocations. AEGIS relies on defensive complementarity: diverse mathematical methodologies detect distinct failure modes, cross-validating each other before reaching protocol consensus.

---

### Lane 1: Recursive 1D Kalman Filter + Mahalanobis Innovation Gating

- **Target Failure Mode:** Transient flash spikes, single-block liquidity manipulation, and high-frequency oracle quote pollution.
- **Methodology Role:** `PRICE_ESTIMATOR` (Outputs continuous price posterior $\hat{x}_{t|t}$ and innovation gating diagnostic).
- **Methodology Name:** 1D Recursive State-Space Filter with Chi-Squared Innovation Gating.
- **Mathematical Foundation:**
  - Prediction:
    $$\hat{x}_{t|t-1} = \hat{x}_{t-1|t-1}, \quad P_{t|t-1} = P_{t-1|t-1} + Q$$
  - Measurement Innovation:
    $$\nu_t = z_t - \hat{x}_{t|t-1}, \quad S_t = P_{t|t-1} + R$$
  - Mahalanobis Distance Squared:
    $$D^2 = \frac{\nu_t^2}{S_t}$$
  - Innovation Gate ($\chi^2(1, 0.99)$ critical threshold $\gamma = 6.635$ at significance $\alpha = 0.01$):
    - *Rationale:* In volatile digital asset markets, legitimate price innovations frequently produce $D^2 \approx 4-5$. A conservative $\alpha=0.05$ threshold ($\chi^2 = 3.841$) results in excessive false rejections. A 99% confidence threshold ($\chi^2(1, 0.99) \approx 6.635$) allows genuine high-volatility moves to pass while decisively gating flash spikes ($D^2 \gg 10$).
    $$\text{If } D^2 > 6.635 \implies \text{Gate observation } z_t \text{ (Decision: INNOVATION_GATED), retain } \hat{x}_{t|t} = \hat{x}_{t|t-1}, P_{t|t} = P_{t|t-1}$$
    $$\text{If } D^2 \le 6.635 \implies K_t = \frac{P_{t|t-1}}{S_t}, \quad \hat{x}_{t|t} = \hat{x}_{t|t-1} + K_t \nu_t, \quad P_{t|t} = (1 - K_t) P_{t|t-1}$$
- **Concrete Inputs:** Observation quote $z_t$, prior state estimate $\hat{x}_{t-1}$, prior covariance $P_{t-1}$, process noise variance $Q$, measurement noise variance $R$.
- **Output Format:** Posterior price estimate $\hat{x}_{t|t}$, posterior covariance $P_{t|t}$, Mahalanobis distance $D^2$, $\alpha=0.01$, gating decision (`ACCEPTED` vs `INNOVATION_GATED`), reason code.
- **Security Role:** Acts as an immediate mathematical firewall preventing flash spikes from contaminating downstream price filters.
- **Known Failure Modes / Limitations:** Assumes Gaussian innovation statistics; slow to track genuine discontinuous regime changes unless process noise $Q$ adapts dynamically.

---

### Lane 2: Huber M-Estimation via Iteratively Reweighted Least Squares (IRLS)

- **Target Failure Mode:** Heavy-tailed distribution contamination, adversarial minority Sybil quotes, and unsynchronized multi-source outlier injection.
- **Methodology Role:** `PRICE_ESTIMATOR` (Outputs robust location estimate $\hat{\mu}_{Huber}$ and downweights input outliers).
- **Methodology Name:** Robust Location and Scale M-Estimation via IRLS ($k=1.345$).
- **Mathematical Foundation:**
  - Initial location $\tilde{\mu}_0 = \text{median}(z_1, \dots, z_n)$
  - Scale estimate:
    $$s = 1.4826 \cdot \text{MAD}(z)$$
  - Standardized residuals:
    $$r_i = \frac{z_i - \hat{\mu}}{s}$$
  - Huber weight function:
    $$w(r_i) = \begin{cases} 1 & \text{if } |r_i| \le k \\ \frac{k}{|r_i|} & \text{if } |r_i| > k \end{cases}$$
  - IRLS iteration:
    $$\hat{\mu}^{(m+1)} = \frac{\sum_{i=1}^n w(r_i^{(m)}) z_i}{\sum_{i=1}^n w(r_i^{(m)})}$$
  - Bounded influence: Huber transitions smoothly from quadratic loss (Gaussian center) to linear loss (heavy tails), bounding influence rather than assigning zero weight.
- **Concrete Inputs:** Vector of discrete feed prices $z \in \mathbb{R}^n$ ($n \ge 3$), tuning constant $k=1.345$, convergence tolerance $\epsilon=10^{-6}$.
- **Output Format:** Robust location estimate $\hat{\mu}_{Huber}$, robust standard error $\text{SE}(\hat{\mu})$, weights table for each input quote with residual and outlier flag ($|r_i| > 2.5$), outlier count, reason code.
- **Security Role:** Computes a robust central tendency resistant to corrupted or poisoned validator submissions without completely discarding information.
- **Known Failure Modes / Limitations:** Does not have a 50% breakdown point in joint location/scale estimation without high-breakdown auxiliary initializers; extreme clustering of corrupt quotes exceeding 50% of the sample can bias the estimate.

---

### Lane 3: Pairwise Jensen-Shannon Divergence (JSD) Matrix Analysis

- **Target Failure Mode:** Latent informational asymmetry, covert multi-validator collusion, and divergent uncertainty distributions.
- **Methodology Role:** `UNCERTAINTY_CONSENSUS_MEASURE` (Diagnostic lane; outputs pairwise uncertainty divergence matrix directly to the Evidence Engine).
- **Methodology Name:** Information-Theoretic Uncertainty Divergence on Discrete Probability Grids.
- **Mathematical Foundation:**
  - For continuous or parametric uncertainty distributions $P_i, P_j$, construct a unified bounded support grid $[x_{min}, x_{max}]$ with $M=100$ bins.
  - Compute mixture distribution:
    $$M = \frac{1}{2}(P_i + P_j)$$
  - Jensen-Shannon Divergence (symmetric, bounded in $[0, 1]$ when using base-2 logarithm):
    $$D_{JS}(P_i \parallel P_j) = \frac{1}{2} D_{KL}(P_i \parallel M) + \frac{1}{2} D_{KL}(P_j \parallel M)$$
  - Mean divergence per lane:
    $$\bar{D}_{JS}(L_i) = \frac{1}{K-1} \sum_{j \ne i} D_{JS}(L_i \parallel L_j)$$
  - Information-theoretic consensus weight:
    $$w_i = \frac{\exp(-\gamma \bar{D}_{JS}(L_i))}{\sum_m \exp(-\gamma \bar{D}_{JS}(L_m))}$$
- **Concrete Inputs:** Array of validator uncertainty distributions (each defined by estimate $\mu_i$ and bounds $[L_i, U_i]$).
- **Output Format:** $5 \times 5$ pairwise JSD matrix, mean divergence per lane, consensus weights $w_i$, isolated divergent lanes list, global disagreement score. Does not output an eligible price estimate for $P_{DEC}$.
- **Security Role:** Quantifies geometric disagreement across validator uncertainty profiles, isolating nodes whose distribution shape deviates even if their point estimates appear normal.
- **Known Failure Modes / Limitations:** Sensitive to discretization bin count and boundary truncation; computationally more intensive than scalar distance metrics.

---

### Lane 4: Ornstein-Uhlenbeck RWA Residual / Jump-Diffusion Analysis

- **Target Failure Mode:** Real World Asset (RWA) secondary market depegs, redemption halts, and structural discount breakdowns.
- **Methodology Role:** `RWA_STRUCTURAL_CHECK` (Diagnostic lane; outputs structural diffusion residuals and jump candidate flags directly to the Evidence Engine).
- **Methodology Name:** Continuous-Time Mean-Reverting Spread Diffusion with Jump Residual Testing.
- **Mathematical Foundation:**
  - If asset is not an anchored RWA, lane safely returns `NOT_APPLICABLE` with zero-divergence neutral telemetry.
  - For anchored RWAs with spot price $P_{spot}$ and physical redemption/NAV anchor $P_{anchor}$:
    $$S_t = \ln(P_{spot}) - \ln(P_{anchor})$$
  - Stochastic spread dynamics under baseline equilibrium $S_{prior}=0$:
    $$dS_t = \theta (\mu - S_t) dt + \sigma dW_t$$
  - Conditional expectations:
    $$\mathbb{E}[S_t \mid S_0 = 0] = \mu (1 - e^{-\theta \Delta t}) = 0$$
    $$\text{Var}(S_t \mid S_0 = 0) = \frac{\sigma^2}{2\theta} (1 - e^{-2\theta \Delta t})$$
  - Standardized spread residual:
    $$z_{OU} = \frac{S_t - \mathbb{E}[S_t \mid S_0]}{\sqrt{\text{Var}(S_t \mid S_0)}}$$
  - Jump candidate test:
    $$\text{If } |z_{OU}| \ge 3.5 \implies \text{Flag structural residual alert / jump candidate (under configured threshold)}$$
- **Concrete Inputs:** Secondary market spot price $P_{spot}$, primary redemption NAV/anchor price $P_{anchor}$, calibrated parameters $(\theta, \mu, \sigma, \Delta t)$, configured jump threshold $z_{thresh} = 3.5$, asset RWA flag.
- **Output Format:** Log spread $S_t$, conditional expectation, conditional variance, standardized residual $z_{OU}$, jump candidate flag (`DIFFUSION_MODEL_INCONSISTENCY` vs `DIFFUSION_CONSISTENT`), reason code (`STRUCTURAL_RESIDUAL_ALERT`). Does not output an eligible price estimate for $P_{DEC}$.
- **Security Role:** Disentangles normal market discount/premium fluctuations from structural residual alerts, preventing protocol vaults from overvaluing impaired RWA collateral under configured scenarios.
- **Known Failure Modes / Limitations:** Requires an authoritative off-chain redemption anchor feed; parameter miscalibration ($\theta, \sigma$) can misdiagnose high legitimate volatility as a jump.

---

### Lane 5: Page CUSUM Sequential Drift Detection Filter

- **Target Failure Mode:** Slow, cumulative, insidious price manipulation (stealth poisoning) designed to evade point-in-time threshold checks.
- **Methodology Role:** `SEQUENTIAL_DRIFT_DETECTOR` (Diagnostic lane; outputs sequential cumulative drift statistics directly to the Evidence Engine).
- **Methodology Name:** Page Cumulative Sum (CUSUM) Sequential Quality Control Filter.
- **Mathematical Foundation:**
  - Standardized price increment relative to baseline tick volatility $\sigma_k$:
    $$y_k = \frac{P_k - P_{k-1}}{\sigma_k}$$
  - Two-sided sequential accumulators with drift allowance $\kappa = 0.5$:
    $$S_k^+ = \max(0, S_{k-1}^+ + y_k - \kappa)$$
    $$S_k^- = \max(0, S_{k-1}^- - y_k - \kappa)$$
  - Decision threshold $h = 4.0$:
    $$\text{If } S_k^+ \ge h \text{ or } S_k^- \ge h \implies \text{Emit persistent drift alert}$$
- **Concrete Inputs:** Sequential price series $\{P_k\}$, baseline tick volatility $\sigma_k$, allowance parameter $\kappa$, decision threshold $h$.
- **Output Format:** Accumulator values $S_k^+, S_k^-$, standardized increment $y_k$, sequential drift alarm status (`PERSISTENT_DRIFT_ALERT` vs `BASELINE_STATIONARY`), accumulator history trajectory, reason code. Does not output an eligible price estimate for $P_{DEC}$.
- **Security Role:** Detects persistent micro-drifts ($+0.25\%$ per tick) that never breach single-tick deviation thresholds but cumulatively subvert protocol collateral solvency.
- **Known Failure Modes / Limitations:** Requires calibrated baseline tick volatility $\sigma_k$; in trending structural bull/bear markets, requires periodic baseline recentering to avoid false drift alarms.

---

## Defensive Synergy & Consensus Flow

The five methodology lanes feed directly into the Evidence Engine and Decision Engine:

1. **Role Segregation & Eligibility Filtering:** Observations are separated into Price Estimators (Lanes 1 & 2) and Diagnostic Evidence (Lanes 3, 4, 5). Price estimators are screened for innovation gating and disqualification. If Lane 1 gates an anomalous flash spike, Lane 2 (Huber) provides the uncontaminated price estimate.
2. **Robust Aggregation ($P_{DEC}$):** An uncertainty-weighted median blend aggregates eligible price estimators, computing a normalized MAD dispersion metric. Diagnostic lanes receive weight 0.0 in $P_{DEC}$ while their forensic diagnostics are preserved in `lane_results`.
3. **Triangulation & Evidence Ingestion:** The Evidence Engine evaluates triangular deviations ($d(OSM, Market)$, $d(DEC, Market)$, $d(OSM, DEC)$) and ingests diagnostic evidence directly from all 5 lanes:
   - Lane 1: Mahalanobis $D^2$, $\chi^2(1, 0.99)=6.635$, gating state
   - Lane 2: Outlier count and downweighted quote list
   - Lane 3: Pairwise JSD divergence matrix and informational disagreement
   - Lane 4: Standardized RWA spread residual and jump candidate state
   - Lane 5: Sequential drift accumulator states ($S_t^+, S_t^-$)
4. **Deterministic Policy:** The Decision Engine executes deterministic protocol actions:
   - `VERIFIED`: Discrepancies within normal bounds; adopts $P_{OSM}$ at full collateral power.
   - `WARNING`: Minor non-critical divergence; adopts $P_{DEC}$ with informational warning.
   - `DISPUTED`: Conflicting signals without clear alignment; applies conservative haircut.
   - `RESTRICTED`: Substantial divergence; restricts collateral valuation ceiling to prevent simulated collateral exposure overstatement under configured LTV.
   - `HALTED`: Extreme multi-sigma dislocation or quorum breakdown; invokes circuit breaker.


---

---

## Solidity On-Chain Verification Layer (Phase 4B & 4B.1)

The AEGIS on-chain verification layer provides a battle-hardened, EVM-native implementation of the canonical verification pipeline in Solidity (`^0.8.24`), fully tested via Foundry and compliant with OpenZeppelin Contracts v5.0.

### Trust Model & Security Hardening (Phase 4B.1)

1. **Operator Identity vs. Wallet Address Separation:**
   - Every registered validator is bound to an immutable organizational `operatorId` (`bytes32`).
   - Quorum evaluation strictly counts distinct `operatorId`s, preventing multi-wallet Sybil attacks from single entities.
   - At most one submission per `(roundId, laneId, operatorId)` is admitted to Tier 1 within-lane aggregation.
2. **Snapshot-Bound Commit-Reveal:**
   - `operatorId` and `laneId` are snapshotted in `CommitmentRecord` at commit time.
   - Reveal strictly enforces that current validator status, `operatorId`, and `laneId` have not mutated mid-round.
   - Cryptographic commitment payload binds `(operatorId, laneId, price, uncertaintyValue, uncertaintyType, isGated, diagPayload, evidenceHash)`.
3. **Explicit Uncertainty Type Semantics:**
   - Enforces typed uncertainty via `UncertaintyType` (`CI95_HALF_WIDTH`, `ABSOLUTE_STD`, `EMPIRICAL_DISPERSION`, `SOURCE_CONFIDENCE`, `OTHER_UNSUPPORTED`).
   - For `CI95_HALF_WIDTH`, exact Gaussian conversion $\sigma = (\text{uncertaintyValue} \times 100) / 196$ ($\sigma = \text{halfWidth} / 1.96$) is computed.
   - Unsupported variants or mixed uncertainty semantics within a single lane are deterministically rejected.
4. **MarketAttestor Market Observer Trust Boundary:**
   - EIP-712 typed data signatures prove attestor identity, non-repudiation, and payload integrity.
   - Market attestations are classified as external **Market Observers** (not infallible ground truth) and are triangulated against $P_{OSM}$ and $P_{DEC}$ by the Evidence and Decision Engines.

### Contract Inventory (`contracts/src/`)

| Contract | Category | Responsibility |
| :--- | :--- | :--- |
| [`IAEGISPriceFeed.sol`](file:///d:/Projects/aegis/contracts/src/interfaces/IAEGISPriceFeed.sol) | Interface | Canonical, unopinionated protocol price interface: `getPrice(bytes32 assetId) -> (price, status, timestamp)`. |
| [`IOSM.sol`](file:///d:/Projects/aegis/contracts/src/interfaces/IOSM.sol) | Interface | Minimal read-only delayed OSM baseline inspection: `readPrice() -> (price, hasPrice)`. |
| [`FixedPointMath.sol`](file:///d:/Projects/aegis/contracts/src/libraries/FixedPointMath.sol) | Library | Internal 18-decimal WAD arithmetic, BPS conversion, and relative deviation. |
| [`AggregatorLib.sol`](file:///d:/Projects/aegis/contracts/src/libraries/AggregatorLib.sol) | Library | Two-Tier Hierarchical Aggregation: Tier 1 within-lane robust median & conservative dispersion heuristic with exact CI95 conversion; Tier 2 inverse-variance cross-lane synthesis. |
| [`ValidatorRegistry.sol`](file:///d:/Projects/aegis/contracts/src/ValidatorRegistry.sol) | Core | Validator node authorization, organizational `operatorId` binding, lane assignment (1-5), and role classification (`PRICE_ESTIMATOR` vs `DIAGNOSTIC`). |
| [`MarketAttestor.sol`](file:///d:/Projects/aegis/contracts/src/MarketAttestor.sol) | Core | EIP-712 typed data signing, timestamp lower/upper freshness verification, and replay protection for $P_{MARKET}$ with documented Market Observer trust boundaries. |
| [`AEGISEvidenceEngine.sol`](file:///d:/Projects/aegis/contracts/src/AEGISEvidenceEngine.sol) | Core | On-chain triangular deviation evaluation ($d(OSM, MKT), d(DEC, MKT), d(OSM, DEC)$) and compact anomaly bitmask compilation. |
| [`AEGISDecisionEngine.sol`](file:///d:/Projects/aegis/contracts/src/AEGISDecisionEngine.sol) | Core | Deterministic safety policy matrix: maps triangular evidence and diagnostic flags to $P_{FINAL}$, `OracleStatus`, and `ActionCode`. |
| [`AEGISPriceRouter.sol`](file:///d:/Projects/aegis/contracts/src/AEGISPriceRouter.sol) | Core | Single authoritative price store implementing `IAEGISPriceFeed` with per-asset staleness bounds. |
| [`AEGISVerificationManager.sol`](file:///d:/Projects/aegis/contracts/src/AEGISVerificationManager.sol) | Core | Round coordinator state machine, commit-reveal management, 3D distinct-operator quorum, and keeper atomic finalization. |

### Measured Gas Benchmarks (`forge test --gas-report`)

Measured execution costs under `solc = "0.8.24"` (`via_ir = true`) with 200 optimizer runs:

| Operation | Function | 5 Validators | 10 Validators | Median Gas |
| :--- | :--- | :--- | :--- | :--- |
| **Commitment** | `AEGISVerificationManager.commit` | 61,708 | 61,708 | 61,708 |
| **Evidence Reveal** | `AEGISVerificationManager.reveal` | 173,062 | 173,062 | 173,062 |
| **Round Creation** | `AEGISVerificationManager.createRound` | 182,777 | 182,777 | 182,777 |
| **Atomic Finalization** | `finalizeRoundWithAttestation` | 424,718 | 501,195 | 462,956 |
| **Protocol Price Query** | `AEGISPriceRouter.getPrice` | 13,694 | 13,694 | 13,694 |
| **Attestation Verification** | `MarketAttestor.verifyAttestation` | 34,646 | 34,646 | 34,646 |

---

## Verification & Testing

AEGIS maintains comprehensive automated test suites covering Solidity smart contracts, Python statistical methodologies, and Next.js institutional web dashboards:

```bash
# 1. Run all Solidity smart contract tests (71/71 passing including 17 adversarial security scenarios)
cd contracts
forge test -vvv

# 2. Run Solidity gas benchmarks & invariant fuzz suites
forge test --gas-report

# 3. Run all off-chain quant methodologies & pipeline integration tests (58/58 passing)
cd ..
python -m pytest

# 4. Build and verify the Next.js institutional risk terminal (0 errors)
npm --prefix apps/web run build
```

---

## License & Attribution

AEGIS is developed as an open research prototype for the Rethinking Blockchain Oracles initiative.
