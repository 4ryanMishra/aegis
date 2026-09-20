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

The `P_DECAggregator` performs deterministic robust aggregation:
1. **Role Filtering:** Isolates Price Estimators (`is_price_estimator == True` and `estimated_price is not None`).
2. **Gating Isolation:** If a price estimator is gated (`INNOVATION_GATED` from Lane 1), it is removed from the eligible pool. In flash spikes, Lane 2 (Huber) provides the uncontaminated price estimate alone.
3. **Uncertainty-Weighted Blend:** Combines median with inverse-variance weighted mean based on uncertainty interval widths.
4. **Forensic Preservation:** Diagnostic lanes (Lanes 3, 4, 5) receive weight 0.0 in $P_{DEC}$ but their rich forensic diagnostics are preserved in `lane_results`.

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

## 7. Blockchain boundary

First MVP contract set:

- `MockOSM`: stores current and pending values and activation time.
- `ValidatorRegistry`: optional lightweight registry for logical validator identities.
- `OracleDecisionEngine`: consumes submitted values/evidence and exposes the selected decision.

Do not attempt to put forecasting or advanced statistical inference into Solidity.

## 8. Research insertion points

```text
packages/quant/src/strategies/
packages/quant/src/aggregation/
packages/quant/src/detection/
packages/quant/src/risk/
contracts/src/ValidatorRegistry.sol
contracts/src/OracleDecisionEngine.sol
```

These are the places where the research team's methodologies will be added.
