# AEGIS — Technical Requirements Document (MVP)

## 1. Architecture

```text
Browser / Next.js
        |
        v
FastAPI service
        |
        +--> Verification Window Coordinator
        +--> Validator Strategy Registry
        +--> P_DEC Aggregator
        +--> Market Adapter (P_MARKET)
        +--> Evidence / Anomaly Engine
        +--> Decision Policy
        |
        +--> Mock OSM Adapter (P_OSM baseline)
        |
        v
Optional Solidity contracts (Anvil/Foundry)
```

## 2. Design rule
`P_DEC` must be an interface, not a hard-coded algorithm. Future research methodologies must implement the same validator contract/interface.

Suggested interface:

```text
ValidatorStrategy.generate(reference_context) -> ValidatorObservation

ValidatorObservation:
- validator_id
- estimate
- confidence (optional)
- interval_low / interval_high (optional)
- method_id
- source_ids
- generated_at
- metadata
```

## 3. P_DEC aggregation
The aggregator receives valid validator observations and returns:

```text
P_DECResult:
- aggregate_value
- observations_used
- observations_rejected
- dispersion
- quorum_met
- aggregation_method
- provenance
```

The first implementation can use a deterministic robust aggregate. Exact methodology is replaceable once research is completed.

## 4. P_MARKET adapter
Requirements:
- external provider adapter interface;
- explicit source name;
- retrieval timestamp;
- market/exchange symbol;
- payload hash where practical;
- stale/error state;
- no claim that centralized exchange data is on-chain.

Initial development may use a mocked adapter. A live adapter may be added later.

## 5. P_OSM baseline adapter
The MVP baseline should expose:
- current delayed value;
- queued/pending value if simulated;
- window start/end;
- activation timestamp;
- baseline action.

Do not infer undocumented Multipli contract fields or behavior. Any unknown field must be marked `ASSUMED`, `SIMULATED`, or `TO_VERIFY`.

## 6. Evidence engine
Input:
`P_OSM`, `P_DEC`, `P_MARKET`, validator observations, freshness, dispersion, source metadata.

Output:

```text
EvidenceResult:
- deviations
- osm_relative_deviation
- dec_relative_deviation
- validator_dispersion
- market_source_status
- anomaly_score (transparent formula)
- suspicion_state
- reason_codes[]
```

The initial anomaly score must be explainable. Avoid black-box classification in the MVP.

## 7. Decision engine
The decision engine takes evidence and applies a configurable policy:

```text
Decision:
- selected_value
- baseline_value
- action
- collateral_factor
- baseline_collateral_value
- aegis_collateral_value
- delta
- rationale
- policy_version
```

Example actions:
- `USE_OSM`
- `USE_REFERENCE`
- `RESTRICT`
- `HALT`

No production policy thresholds should be invented. Demo thresholds must be stored in configuration and labeled as prototype values.

## 8. API endpoints
Suggested MVP endpoints:

`POST /api/scenarios/run`
`GET /api/scenarios/{id}`
`POST /api/market/quote`
`POST /api/verification/start`
`POST /api/verification/{id}/submit`
`POST /api/verification/{id}/finalize`
`GET /api/health`

WebSockets can be introduced after the deterministic request/response path is stable.

## 9. Data contract
Use JSON with explicit names:

```json
{
  "scenario_id": "gold_01",
  "p_osm": 100.0,
  "validators": [],
  "p_dec": null,
  "p_market": null,
  "evidence": null,
  "decision": null,
  "data_status": "SIMULATED"
}
```

## 10. Persistence
No database required for MVP. Use in-memory scenario state or JSON fixtures. Do not introduce Postgres/Redis unless a demonstrated requirement appears.

## 11. Determinism
- Every simulation has a scenario ID and random seed.
- All prototype algorithms must be reproducible.
- Store algorithm/version IDs with outputs.
- Keep fixtures for judge-demo scenarios.

## 12. Solidity boundary
The chain layer should verify/consume compact outputs, not perform heavy statistics.

Potential contracts:
- `MockOSM.sol`
- `ValidatorRegistry.sol`
- `DecisionOracle.sol`

The first Solidity version may simply model data and permissions. Production security claims are out of scope.

## 13. Testing
### Unit
- aggregation
- deviation calculations
- stale detection
- validator availability
- evidence reason codes
- collateral calculation

### Property/fuzz
- aggregation never uses rejected observations;
- malformed observations cannot produce a valid finalized result;
- collateral calculation is monotonic in selected price for positive collateral factor;
- finalized results are reproducible from the same inputs.

### Scenario tests
1. healthy consensus;
2. one manipulated validator;
3. stale validator;
4. missing validators;
5. genuine market crash;
6. OSM outlier;
7. market-source failure.

## 14. Observability
Every run should expose an audit trail:

```text
source → observation → validator → aggregation → evidence → decision
```

The frontend should make this trace visible.
