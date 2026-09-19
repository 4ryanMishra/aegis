# MVP Threat Model

## Threats

### T1. Stale OSM value
The delayed value remains above or below the terminal market price.

### T2. Single malicious validator
One validator submits an extreme estimate.

### T3. Correlated validator failure
Several validators rely on the same underlying source, reducing true independence.

### T4. Market observer manipulation
The terminal market source is wrong or manipulated.

### T5. Forecast model error
A validator strategy produces a poor estimate even when honest.

### T6. Selection-rule bias
A policy that always chooses the value closest to `P_MARKET` can overfit the terminal observation and does not by itself prove economic correctness.

## MVP mitigations
- robust aggregation
- source/operator metadata
- validator agreement metrics
- explicit confidence/uncertainty fields
- independent market observer abstraction
- scenario testing
- reproducible historical backtests
- no claim of absolute truth

## Future mitigations
- commit-reveal
- validator staking/slashing
- multiple independent market sources
- on-chain TWAP
- threshold signatures / attestations
- reputation based on historical calibration
- economic attack-cost analysis
