"""
Verification Window Coordinator (Phase 4A).
Coordinates the end-to-end verification window across the five methodology lanes:
T0 P_OSM -> Five Methodology Lanes -> Validator Evidence -> P_DEC -> P_MARKET -> Evidence Engine -> Decision Engine -> P_FINAL
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..models.schema import (
    ScenarioRecord,
    TimeWindow,
    ScenarioRunRequest,
    CustomVerificationRequest,
    DataStatus,
    ValidatorResult,
)
from .osm_adapter import MockOSMAdapter
from .market_adapter import MockMarketAdapter
from .aggregator import P_DECAggregator
from .evidence_engine import EvidenceEngine
from .decision_engine import DecisionEngine
from ..validators.base import ReferenceContext
from ..validators.registry import MethodologyRegistry, default_registry
from ..config import AegisConfig, default_config


class VerificationCoordinator:
    def __init__(
        self,
        registry: MethodologyRegistry = default_registry,
        config: AegisConfig = default_config,
    ):
        self.registry = registry
        self.config = config
        self.osm_adapter = MockOSMAdapter()
        self.market_adapter = MockMarketAdapter()
        self.aggregator = P_DECAggregator(min_quorum=config.min_validator_quorum)
        self.evidence_engine = EvidenceEngine(config=config)
        self.decision_engine = DecisionEngine()
        self.fixtures: Dict[str, dict] = {}
        self._load_fixtures()

    def _load_fixtures(self):
        fixtures_path = Path(__file__).resolve().parents[4] / "shared" / "fixtures" / "baseline_scenarios.json"
        if fixtures_path.exists():
            with open(fixtures_path, "r", encoding="utf-8") as f:
                scenarios = json.load(f)
                for s in scenarios:
                    self.fixtures[s["scenario_id"]] = s

    def list_scenarios(self) -> List[dict]:
        return list(self.fixtures.values())

    def run_scenario(self, req: ScenarioRunRequest) -> ScenarioRecord:
        fixture = self.fixtures.get(req.scenario_id)
        if not fixture:
            # Default fallback scenario
            fixture = {
                "scenario_id": req.scenario_id,
                "scenario_type": "NORMAL",
                "title": "Simulated RWA Asset Verification",
                "description": "Standard 1-hour verification window test scenario.",
                "asset": "XAU/USD (Tokenized Gold)",
                "p_osm_initial": 95.20,
                "expected_market": 95.15,
                "anchor_price": 95.20,
                "is_rwa": True,
                "ltv_default": 0.60,
            }

        start_ts = 1774000000
        duration = self.config.window_duration_seconds
        step_elapsed = min(req.step_seconds if req.step_seconds is not None else duration, duration)
        end_ts = start_ts + duration
        is_finalized = step_elapsed >= duration

        # 1. P_OSM baseline feed at T0
        p_osm = self.osm_adapter.get_queued_osm(
            initial_price=fixture["p_osm_initial"],
            timestamp=start_ts,
        )

        # 2. Context for the Five Methodology Lanes
        scenario_type = fixture.get("scenario_type", "NORMAL")
        context = ReferenceContext(
            asset=fixture["asset"],
            p_osm=p_osm.value,
            window_start_ts=start_ts,
            current_ts=start_ts + step_elapsed,
            expected_market_hint=fixture.get("expected_market", p_osm.value),
            anchor_price=fixture.get("anchor_price", p_osm.value),
            is_rwa=fixture.get("is_rwa", True),
            scenario_type=scenario_type,
            seed=req.custom_seed or 42,
        )

        # 3. Generate Validator Evidence across Methodology Lanes
        validators = self.registry.generate_all(context=context)

        # Filter validators based on window elapsed time
        visible_validators = [v for v in validators if v.timestamp <= start_ts + step_elapsed]

        # 4. P_DEC Deterministic Cross-Lane Aggregation
        p_dec = self.aggregator.aggregate(visible_validators)

        # 5. P_MARKET Terminal Observation
        if is_finalized:
            p_market = self.market_adapter.observe_market(
                price=fixture.get("expected_market", p_osm.value),
                timestamp=end_ts,
                symbol=fixture["asset"],
                status=DataStatus.SIMULATED,
            )
        else:
            p_market = self.market_adapter.observe_market(
                price=0.0,
                timestamp=None,
                symbol=fixture["asset"],
                status=DataStatus.PENDING,
            )
            p_market.value = None

        # 6. Evidence Engine Evaluation
        evidence = self.evidence_engine.evaluate(
            p_osm=p_osm,
            p_dec=p_dec,
            p_market=p_market,
            validators=visible_validators,
        )

        # 7. Decision & Collateral Consequence
        ltv = req.ltv_factor if req.ltv_factor is not None else fixture.get("ltv_default", 0.60)
        decision, collateral = self.decision_engine.decide(
            p_osm=p_osm,
            p_dec=p_dec,
            p_market=p_market,
            evidence=evidence,
            ltv=ltv,
        )

        window = TimeWindow(
            start_ts=start_ts,
            end_ts=end_ts,
            duration_seconds=duration,
            elapsed_seconds=step_elapsed,
            is_finalized=is_finalized,
        )

        # Intermediate telemetry map for quick UI lookup
        intermediate_telemetry: Dict[str, Any] = {
            v.methodology: {
                "lane_id": v.lane_id,
                "metrics": v.intermediate_metrics,
                "decision": v.decision,
                "reason_code": v.reason_code,
            }
            for v in visible_validators
        }

        return ScenarioRecord(
            scenario_id=fixture["scenario_id"],
            title=fixture["title"],
            description=fixture["description"],
            asset=fixture["asset"],
            window=window,
            p_osm=p_osm,
            validators=visible_validators,
            p_dec=p_dec,
            p_market=p_market,
            evidence=evidence,
            decision=decision,
            collateral=collateral,
            intermediate_telemetry=intermediate_telemetry,
        )
