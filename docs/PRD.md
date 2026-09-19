# AEGIS — Product Requirements Document (MVP)

## 0. Status
- Version: 0.1 MVP
- Date: 2026-09-20
- Product: AEGIS (working name) — Adaptive Oracle Verification & Risk Engine
- Track: Rethinking Blockchain Oracles
- Target integration context: Multipli RWAUSD / delayed-oracle flow

## 1. Product thesis
AEGIS repurposes the existing oracle delay window as a verification window. Instead of blindly activating the delayed OSM value at the end of the hour, the system collects independently produced reference estimates (`P_DEC`) and an end-of-window independent market observation (`P_MARKET`), then evaluates the evidence against the delayed oracle value (`P_OSM`) before producing a protocol valuation/action.

The MVP is a research prototype. It must demonstrate the mechanism without pretending that the prototype is the production Multipli implementation.

## 2. Core values
### P_OSM
The delayed value supplied by the existing Multipli oracle/OSM mechanism in the baseline scenario.

### P_DEC
An independently constructed reference value produced through a decentralized/validator-style process. The validator generation techniques are intentionally pluggable because the research team is still evaluating the most credible methodologies.

### P_MARKET
An independently observed market value at the end of the verification window. In the MVP this can be supplied by public market APIs/exchange endpoints. A Binance endpoint is an off-chain centralized exchange observation, not an on-chain price.

## 3. User problem
A delayed oracle is intentionally conservative against short-lived manipulation, but the delayed value can diverge from the market during a genuine move or stale/manipulated condition. The protocol needs a way to use the delay window to collect additional evidence before applying the price to collateral or issuance decisions.

## 4. MVP goals
1. Visualize the baseline delayed-oracle flow.
2. Simulate a verification window.
3. Generate multiple independent validator outputs through replaceable strategies.
4. Aggregate those outputs into `P_DEC` using a deterministic rule.
5. Retrieve/ingest `P_MARKET` at the end of the window.
6. Compare `P_OSM`, `P_DEC`, and `P_MARKET`.
7. Detect large deviations / suspicious inconsistency.
8. Demonstrate the collateral-value impact of using a risk-aware final value.
9. Keep every assumption, simulated value, and methodology explicitly labeled.

## 5. Non-goals for MVP
- Reproducing Multipli's private/internal contracts without authoritative material.
- Claiming Binance is decentralized or on-chain.
- Claiming a model prediction is inherently trustworthy.
- Deploying a production oracle network.
- Full token economics, validator staking, slashing, governance, bridges, auth, databases, Kubernetes, or multi-chain production infrastructure.
- Hiding methodology behind opaque ML.

## 6. Primary demo scenario
Baseline:
- `P_OSM = $100`
- `P_MARKET = $95`
- validator estimates might include `$89, $98, $110, $93` (illustrative only)
- `P_DEC` is produced by the chosen aggregation of the actual validator outputs.
- Example collateral factor: 60%.

The UI must label illustrative/demo numbers as DEMO DATA until backed by live or replayed historical data.

## 7. Product behavior
At T0:
1. Receive or configure `P_OSM`.
2. Start verification window.
3. Validators submit/produce estimates.
4. Record methodology, source set, timestamp, and confidence/quality metadata where available.
5. Aggregate to `P_DEC`.
6. At T1, ingest `P_MARKET`.
7. Run evidence analysis.
8. Produce a final valuation/action recommendation for the prototype.

The final pricing rule must be configurable. `nearest-to-P_MARKET` may be used as a temporary demo policy only; it must not be presented as the final research methodology.

## 8. Trust requirements
AEGIS must never rely on “trust our model.” Trust should be demonstrated through:
- independent inputs;
- transparent methodology;
- reproducible calculation;
- signed validator/attestation interfaces where implemented;
- deterministic aggregation;
- visible provenance;
- explicit timestamps/freshness;
- source diversity;
- historical backtesting before any production claim.

## 9. Attack scenarios
- Single-source manipulation.
- Stale feed.
- Source failure / unavailable validator.
- Coordinated disagreement (research scenario).
- Genuine market regime shift.
- Terminal market-source anomaly.

These are simulation modes unless connected to real data.

## 10. Success criteria
The MVP is successful when a judge can watch one scenario and answer:
1. What was the delayed price?
2. What independent evidence was collected during the hour?
3. How was `P_DEC` produced?
4. What was the terminal market observation?
5. Why was `P_OSM` considered consistent or suspicious?
6. What valuation/action resulted?
7. How much collateral-value exposure changed relative to the baseline?

## 11. Key metrics
- Absolute deviation: `|P_i - P_MARKET|`
- Relative deviation: `|P_i - P_MARKET| / P_MARKET`
- Validator dispersion
- Fraction of unavailable/stale validators
- False-positive manipulation flags on historical replay
- Missed-manipulation rate on synthetic attacks
- Collateral valuation difference vs baseline

## 12. Product principles
- Evidence before assertion.
- Deterministic core over hidden intelligence.
- Research claims must be reproducible.
- Every external source must be labeled.
- Prototype behavior must be visibly distinct from production claims.
- Do not optimize for flashy UI at the expense of auditability.
