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

### Core Oracle Values
- `P_OSM`: Delayed baseline oracle value exposed by the existing OSM after its scheduled delay buffer.
- `P_DEC`: Aggregated evidence product deterministically computed from independent validator submissions across methodology lanes (uncertainty-weighted robust median blend):
  $$\text{methodology computation} \longrightarrow \text{validator evidence} \longrightarrow \text{deterministic cross-validator aggregation} \longrightarrow P_{DEC}$$
- `P_MARKET`: Independent terminal market observation attested at the close of the verification window ($T_1$).
- `P_FINAL`: Single verified authoritative price exposed to the protocol through one stable price interface.

---

## Five Methodology Lanes

AEGIS organizes verification intelligence into:

> **"Five methodology lanes, each capable of being operated by multiple independent validator nodes."**
> 
> *(Current MVP simulation: 1 simulated node per lane. The architecture explicitly decouples methodology mathematical specifications from validator operator keys and node infrastructure).*

### Epistemic Foundation

> **"Each methodology is an evidence producer, not an unquestionable truth source."**
> 
> No single statistical model possesses perfect foresight or immunity to market dislocations. AEGIS relies on defensive complementarity: diverse mathematical methodologies detect distinct failure modes, cross-validating each other before reaching protocol consensus.

---

### Lane 1: Recursive 1D Kalman Filter + Mahalanobis Innovation Gating

- **Target Failure Mode:** Transient flash spikes, single-block liquidity manipulation, and high-frequency oracle quote pollution.
- **Methodology Name:** 1D Recursive State-Space Filter with Chi-Squared Innovation Gating.
- **Mathematical Foundation:**
  - Prediction:
    $$\hat{x}_{t|t-1} = \hat{x}_{t-1|t-1}, \quad P_{t|t-1} = P_{t-1|t-1} + Q$$
  - Measurement Innovation:
    $$\nu_t = z_t - \hat{x}_{t|t-1}, \quad S_t = P_{t|t-1} + R$$
  - Mahalanobis Distance Squared:
    $$D^2 = \frac{\nu_t^2}{S_t}$$
  - Innovation Gate ($\chi^2(1)$ critical threshold $\gamma = 3.841$ at $p=0.05$):
    $$\text{If } D^2 > \gamma \implies \text{Reject observation } z_t, \text{ retain } \hat{x}_{t|t} = \hat{x}_{t|t-1}, P_{t|t} = P_{t|t-1}$$
    $$\text{If } D^2 \le \gamma \implies K_t = \frac{P_{t|t-1}}{S_t}, \quad \hat{x}_{t|t} = \hat{x}_{t|t-1} + K_t \nu_t, \quad P_{t|t} = (1 - K_t) P_{t|t-1}$$
- **Concrete Inputs:** Observation quote $z_t$, prior state estimate $\hat{x}_{t-1}$, prior covariance $P_{t-1}$, process noise variance $Q$, measurement noise variance $R$.
- **Output Format:** Posterior price estimate $\hat{x}_{t|t}$, posterior covariance $P_{t|t}$, Mahalanobis distance $D^2$, gating decision (`OBSERVATION_ACCEPTED` vs `OBSERVATION_GATED`), reason code.
- **Security Role:** Acts as an immediate mathematical firewall preventing flash spikes from contaminating downstream price filters.
- **Known Failure Modes / Limitations:** Assumes Gaussian innovation statistics; slow to track genuine discontinuous regime changes unless process noise $Q$ adapts dynamically.

---

### Lane 2: Huber M-Estimation via Iteratively Reweighted Least Squares (IRLS)

- **Target Failure Mode:** Heavy-tailed distribution contamination, adversarial minority Sybil quotes, and unsynchronized multi-source outlier injection.
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
- **Output Format:** $5 \times 5$ pairwise JSD matrix, mean divergence per lane, consensus weights $w_i$, isolated divergent lanes list, global disagreement score.
- **Security Role:** Quantifies geometric disagreement across validator uncertainty profiles, isolating nodes whose distribution shape deviates even if their point estimates appear normal.
- **Known Failure Modes / Limitations:** Sensitive to discretization bin count and boundary truncation; computationally more intensive than scalar distance metrics.

---

### Lane 4: Ornstein-Uhlenbeck RWA Residual / Jump-Diffusion Analysis

- **Target Failure Mode:** Real World Asset (RWA) secondary market depegs, redemption halts, and structural discount breakdowns.
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
    $$\text{If } |z_{OU}| \ge 3.5 \implies \text{Flag structural jump / depeg candidate}$$
- **Concrete Inputs:** Secondary market spot price $P_{spot}$, primary redemption NAV/anchor price $P_{anchor}$, calibrated parameters $(\theta, \mu, \sigma, \Delta t)$, asset RWA flag.
- **Output Format:** Log spread $S_t$, conditional expectation, conditional variance, standardized residual $z_{OU}$, jump candidate flag (`OU_JUMP_DIFFUSION_CANDIDATE` vs `OU_SPREAD_EQUILIBRIUM`), reason code.
- **Security Role:** Disentangles normal market discount/premium fluctuations from systemic depeg shocks, preventing protocol vaults from overvaluing impaired RWA collateral.
- **Known Failure Modes / Limitations:** Requires an authoritative off-chain redemption anchor feed; parameter miscalibration ($\theta, \sigma$) can misdiagnose high legitimate volatility as a jump.

---

### Lane 5: Page CUSUM Sequential Drift Detection Filter

- **Target Failure Mode:** Slow, cumulative, insidious price manipulation (stealth poisoning) designed to evade point-in-time threshold checks.
- **Methodology Name:** Page Cumulative Sum (CUSUM) Sequential Quality Control Filter.
- **Mathematical Foundation:**
  - Standardized increment relative to in-control baseline $(\mu_0, \sigma_0)$:
    $$z_t = \frac{P_t - \mu_0}{\sigma_0}$$
  - Two-sided sequential accumulators with drift allowance $\kappa = 0.5$:
    $$S_t^+ = \max(0, S_{t-1}^+ + z_t - \kappa)$$
    $$S_t^- = \max(0, S_{t-1}^- - z_t - \kappa)$$
  - Decision threshold $h = 4.0$:
    $$\text{If } S_t^+ \ge h \text{ or } S_t^- \ge h \implies \text{Emit persistent drift alert}$$
- **Concrete Inputs:** Sequential price series $\{P_t\}$, in-control mean $\mu_0$, standard deviation $\sigma_0$, allowance parameter $\kappa$, decision threshold $h$.
- **Output Format:** Accumulator values $S_t^+, S_t^-$, standardized increment $z_t$, sequential drift alarm status (`PERSISTENT_DRIFT_ALERT` vs `DRIFT_ABSENT_STABLE`), accumulator history trajectory, reason code.
- **Security Role:** Detects persistent micro-drifts ($+0.25\%$ per tick) that never breach single-tick deviation thresholds but cumulatively subvert protocol collateral solvency.
- **Known Failure Modes / Limitations:** Requires stationary baseline calibration $(\mu_0, \sigma_0)$; in trending structural bull/bear markets, requires periodic baseline recentering to avoid false drift alarms.

---

## Defensive Synergy & Consensus Flow

The five methodology lanes feed directly into the Evidence Engine and Decision Engine:

1. **Filtering:** Observations from individual lanes are screened for eligibility (quorum condition $N \ge 3$, valid bounds).
2. **Robust Aggregation ($P_{DEC}$):** An uncertainty-weighted median blend aggregates eligible lane estimates, computing a normalized MAD dispersion metric.
3. **Triangulation:** The Evidence Engine evaluates the three pairwise deviations:
   - $d(OSM, Market) = \frac{|P_{OSM} - P_{MARKET}|}{P_{MARKET}}$
   - $d(DEC, Market) = \frac{|P_{DEC} - P_{MARKET}|}{P_{MARKET}}$
   - $d(OSM, DEC) = \frac{|P_{OSM} - P_{DEC}|}{P_{DEC}}$
   correlated with lane anomaly flags (Kalman gated, Huber outliers, JSD divergent, OU jump, CUSUM drift).
4. **Deterministic Policy:** The Decision Engine executes deterministic protocol actions:
   - `VERIFIED`: Discrepancies within normal bounds; adopts $P_{OSM}$ at full collateral power.
   - `WARNING`: Minor non-critical divergence; adopts $P_{DEC}$ with informational warning.
   - `DISPUTED`: Conflicting signals without clear alignment; applies conservative haircut.
   - `RESTRICTED`: Substantial divergence; restricts collateral valuation ceiling to prevent bad debt.
   - `HALTED`: Extreme multi-sigma dislocation or quorum breakdown; invokes circuit breaker.

---

## Verification & Testing

AEGIS maintains comprehensive automated test suites covering mathematical edge cases, determinism, and end-to-end scenario simulations:

```bash
# Run all unit, quant, and end-to-end scenario tests
pytest

# Build and verify the Next.js institutional risk terminal
npm --prefix apps/web run build
```

---

## License & Attribution

AEGIS is developed as an open research prototype for the Rethinking Blockchain Oracles initiative.
