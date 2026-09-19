# AEGIS MVP Master Plan

## Objective
Demonstrate, end-to-end, that a one-hour delayed oracle price can be evaluated against independently generated/decentralized evidence and an end-of-window market observation before being used for a protocol action.

## MVP success condition
Given a scenario where `P_OSM` is stale or abnormal, the system should:

1. capture `P_OSM` at T0,
2. run a verification window,
3. generate validator submissions,
4. aggregate them into `P_DEC`,
5. observe `P_MARKET` at T1,
6. calculate deviations and validator agreement,
7. flag `P_OSM` as normal or suspicious,
8. produce a final valuation/action,
9. show the baseline vs AEGIS collateral impact.

## Phase 0 — scaffold
- Create monorepo structure.
- Add rules/docs.
- Add shared JSON/Pydantic schema.
- Set up Next.js and FastAPI.
- Set up Foundry + Anvil.
- Add CI for tests/builds.

## Phase 1 — War Room UI
UI sections:
- OSM price card
- Decentralized value card
- Current market card
- validator table
- one-hour timeline
- deviation/evidence panel
- manipulation suspicion panel
- collateral impact panel
- scenario/attack controls
- baseline vs AEGIS comparison

Use mocked data until API is ready.

## Phase 2 — Quant framework
Build:
- `MarketObservation` model
- `ValidatorContext`
- `ValidatorStrategy` protocol
- `ValidatorSubmission`
- `ValidatorNetworkSimulator`
- `PDecAggregator`
- `EvidenceAnalyzer`
- `DecisionPolicy`

Use placeholder strategies so the system runs now.

## Phase 3 — Market observer
Create an adapter abstraction:

```python
get_market_price(asset, timestamp) -> MarketObservation
```

For development use a deterministic scenario feed or public API adapter. Keep the API source behind an interface.

## Phase 4 — Scenario/attack engine
Implement scenarios:
- normal drift
- stale OSM
- sudden crash
- source manipulation
- source failure
- temporary market dislocation

The first attack engine is a simulator. It must not imply the real Multipli implementation behaves exactly like the simulator.

## Phase 5 — Evidence + decision
For each scenario produce:

```json
{
  "p_osm": 100.0,
  "p_dec": 93.0,
  "p_market": 95.0,
  "deviations": {},
  "validator_dispersion": 0.0,
  "oracle_status": "SUSPECT",
  "decision_policy": "NEAREST_TO_MARKET",
  "final_price": 93.0,
  "ltv": 0.60,
  "baseline_collateral_value": 60.0,
  "aegis_collateral_value": 55.8
}
```

The values above are illustrative only.

## Phase 6 — Solidity vertical slice
Build minimal contracts that model the data flow and decision recording. Add events for:

- OSM update
- validator submission
- P_DEC aggregation
- market validation
- decision

Use Foundry tests and at least one invariant around state transitions.

## Phase 7 — Research methodology integration
When teammates return with credible techniques:

1. write methodology note,
2. define inputs/outputs,
3. implement strategy class,
4. run historical backtests,
5. compare forecast error and calibration,
6. add method version to submissions,
7. integrate without changing frontend/API contract.

## Phase 8 — Demo hardening
Prepare one golden scenario:

T0:
`P_OSM = $100`

During window:
validator outputs converge toward the 90s.

T1:
`P_MARKET ≈ $95`

AEGIS:
- detects abnormal OSM deviation,
- shows validator consensus,
- selects policy output,
- shows collateral difference.

Then run a second scenario where the OSM value is actually consistent, demonstrating that AEGIS does not blindly override every OSM value.

## Explicit non-goals for MVP
- production-grade economic security
- true permissionless validator network
- real slashing marketplace
- full Multipli private contract integration before source/ABI access
- complex ML ensemble
- cross-chain deployment
- production custody/compliance logic
