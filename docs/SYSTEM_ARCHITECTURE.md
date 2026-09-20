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

**Core Terminology Invariant:**
> "Five methodology lanes, each capable of being operated by multiple independent validator nodes."
> *(Current MVP simulation: 1 simulated node per lane).*

## 2. Value Definitions

### P_OSM
The delayed value exposed by the existing Multipli OSM/oracle flow after its scheduled delay.

### P_DEC
The decentralized reference value generated from validator submissions across the five methodology lanes:
$$\text{methodology computation} \longrightarrow \text{validator evidence} \longrightarrow \text{deterministic cross-validator aggregation} \longrightarrow P_{DEC}$$

### P_MARKET
An independent terminal market observation attested at the close of the verification window ($T_1$).

### P_FINAL
Single verified authoritative price exposed to the protocol through one stable price interface.

## 3. Five Methodology Lanes & Validator Abstraction

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
