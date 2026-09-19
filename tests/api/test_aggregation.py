import pytest
from services.api.src.core.aggregator import P_DECAggregator
from services.api.src.models.schema import ValidatorObservation, DataStatus


def test_aggregation_quorum_not_met():
    aggregator = P_DECAggregator(min_quorum=3)
    obs = [
        ValidatorObservation(
            validator_id="val_1",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=95.0,
            uncertainty_lower=93.0,
            uncertainty_upper=97.0,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0",
            status=DataStatus.SIMULATED
        )
    ]
    res = aggregator.aggregate(obs)
    assert res.quorum_met is False
    assert res.value is None


def test_aggregation_median_calculation():
    aggregator = P_DECAggregator(min_quorum=3, method="median")
    obs = [
        ValidatorObservation(
            validator_id=f"val_{i}",
            strategy_id="strat_1",
            strategy_name="Strat 1",
            estimated_price=p,
            uncertainty_lower=p - 1,
            uncertainty_upper=p + 1,
            observed_at=1000,
            source_ids=["src_a"],
            method_version="0.1.0",
            status=DataStatus.SIMULATED
        )
        for i, p in enumerate([92.0, 93.0, 94.0, 95.0])
    ]
    res = aggregator.aggregate(obs)
    assert res.quorum_met is True
    assert res.value == 93.5  # median of [92, 93, 94, 95] is 93.5
    assert res.validator_count == 4
    assert res.dispersion >= 0.0
