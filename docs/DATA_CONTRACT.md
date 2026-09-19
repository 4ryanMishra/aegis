# Shared Data Contract

```json
{
  "scenario_id": "string",
  "asset": "XAU",
  "window": {
    "start_ts": 0,
    "end_ts": 0
  },
  "p_osm": {
    "value": 100.0,
    "timestamp": 0,
    "source": "multipli_osm_mock"
  },
  "validators": [
    {
      "validator_id": "v1",
      "strategy_id": "placeholder_1",
      "estimated_price": 93.0,
      "uncertainty_lower": 90.0,
      "uncertainty_upper": 97.0,
      "observed_at": 0,
      "source_ids": ["source-a", "source-b"],
      "method_version": "0.1.0",
      "status": "SIMULATED"
    }
  ],
  "p_dec": {
    "value": 93.0,
    "aggregation": "median",
    "validator_count": 4,
    "status": "SIMULATED"
  },
  "p_market": {
    "value": 95.0,
    "timestamp": 0,
    "source": "market_adapter",
    "status": "OBSERVED"
  },
  "evidence": {
    "d_osm_market": 0.0526,
    "d_dec_market": 0.0211,
    "d_osm_dec": 0.0753,
    "validator_dispersion": 0.0,
    "agreement_ratio": 0.75,
    "oracle_status": "SUSPECTED_INCONSISTENCY"
  },
  "decision": {
    "policy": "NEAREST_TO_MARKET",
    "final_price": 93.0,
    "confidence": null,
    "reason_codes": ["OSM_DEVIATION", "DEC_MARKET_ALIGNMENT"]
  },
  "collateral": {
    "ltv": 0.60,
    "baseline_value": 60.0,
    "aegis_value": 55.8,
    "difference": 4.2
  }
}
```

## Compatibility rule
The frontend must consume this schema without knowing how the validator algorithms work internally.
