# AEGIS MVP System Architecture

## 1. Core idea
Use Multipli's one-hour delay as a verification/computation window.

```text
P_OSM arrives at T0
      |
      +--------------------- verification window ---------------------+
      |                                                               |
      v                                                               v
Validator network                                         Independent market observer
(3–4 logical validators initially)                         P_MARKET at T1
      |
      v
P_DEC aggregation
      |
      +------------------------+
                               v
                     Evidence / anomaly engine
                               |
                 +-------------+-------------+
                 |                           |
           oracle consistency          manipulation signal
                 |                           |
                 +-------------+-------------+
                               v
                    valuation / action policy
                               |
                 +-------------+-------------+
                 |                           |
              UI demo                 mock OSM/adapter
```

## 2. Value definitions

### P_OSM
The delayed value that the existing Multipli OSM/oracle flow would expose after its validation window.

### P_DEC
The decentralized reference/forecast value generated from validator submissions. Initially these are simulated logical validators using a pluggable strategy interface. Later they can be real independently operated nodes/contracts.

### P_MARKET
An independent terminal market observation at T1. MVP may use a public exchange API adapter. Later add several independent market/oracle sources and on-chain observations.

## 3. Validator abstraction

Each validator submission should contain:

```text
validator_id
strategy_id
estimated_price
uncertainty_lower
uncertainty_upper
observed_at
source_ids[]
method_version
signature_or_commitment (optional in first UI-only stage)
```

The strategy interface should support:

```python
forecast(context) -> ValidatorSubmission
```

This lets the research team add ARIMA/EWMA/robust-statistical/other approved methods later without changing the rest of the system.

## 4. Aggregation layer

The aggregation layer is deliberately replaceable. Start with a deterministic robust placeholder (for example median) so the end-to-end system works. Replace or augment it with the research team's selected aggregation mechanism.

## 5. Evidence layer

At T1 compute, at minimum:

- `d_osm_market = abs(P_OSM - P_MARKET) / P_MARKET`
- `d_dec_market = abs(P_DEC - P_MARKET) / P_MARKET`
- `d_osm_dec = abs(P_OSM - P_DEC) / max(P_DEC, eps)`

Also compute validator dispersion and the fraction of validators agreeing within configured tolerance.

The output should be an evidence record, not a claim of truth.

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
