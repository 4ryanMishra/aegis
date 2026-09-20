"""
AEGIS Simulation Engine (Phase 5 - Cross-Oracle Architecture).
Deterministic, seeded, real-time accelerated simulation of multi-oracle cross-checking.
"""

import time
import math
import random
from typing import Dict, List, Optional, Any

from services.api.src.oracles.consensus_engine import ConsensusEngine, OracleObservationData
from services.api.src.oracles.risk_decision_engine import RiskDecisionEngine, RiskDecisionOutput


class SimulationEngine:
    """
    Authoritative stateful simulation runtime managing multi-oracle feeds, consensus clustering,
    risk decision policies, and downstream collateralized protocol positions.
    """

    def __init__(self):
        self.consensus_engine = ConsensusEngine(cluster_tolerance_pct=0.50, min_quorum=3, min_agreement_ratio=0.60)
        self.decision_engine = RiskDecisionEngine(normal_threshold_pct=0.50, deviation_threshold_pct=1.00, critical_threshold_pct=3.00)

        # Simulation Clock & State
        self.scenario_id: str = "scen_normal"
        self.sim_time_seconds: float = 0.0
        self.window_duration_seconds: int = 3600
        self.speed_multiplier: float = 60.0
        self.is_running: bool = False
        self.is_paused: bool = False
        self.is_finalized: bool = False
        self.last_wall_time: Optional[float] = None
        self.seed: int = 42

        # User Collateral Position State (MockRWAUSDProtocol)
        self.user_address: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        self.collateral_asset: str = "Tokenized Gold (XAU)"
        self.collateral_amount: float = 10.0  # 10.00 oz default
        self.debt_amount: float = 28000.0     # 28,000.00 RWAUSD default
        self.ltv: float = 0.80

        # Scenario Fixtures
        self.fixtures = {
            "scen_normal": {
                "scenario_id": "scen_normal",
                "title": "Normal Market Convergence",
                "description": "Multipli OSM and all external oracle feeds agree in tight consensus (~$4,320/oz). Standard 80% LTV maintained.",
                "scenario_type": "NORMAL",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
            },
            "scen_flash_crash": {
                "scenario_id": "scen_flash_crash",
                "title": "Multipli OSM Divergence / Market Drop (Hero Demo)",
                "description": "External spot market falls to ~$4,050 while Multipli OSM remains delayed at $4,380. AEGIS detects divergence and restricts LTV.",
                "scenario_type": "FLASH_CRASH",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
            },
            "scen_outlier": {
                "scenario_id": "scen_outlier",
                "title": "Single Oracle Outlier Rejection",
                "description": "A single oracle feed reports an anomalous $9,000 quote. Agreement clustering isolates the outlier and preserves consensus.",
                "scenario_type": "OUTLIER",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4050.0,
            },
            "scen_disagreement": {
                "scenario_id": "scen_disagreement",
                "title": "Multi-Oracle Disagreement (Bimodal Split)",
                "description": "External oracles split into two contradictory clusters ($4,050 vs $4,450). No consensus exists; emergency circuit breaker engages.",
                "scenario_type": "DISAGREEMENT",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4050.0,
            },
            "scen_outage": {
                "scenario_id": "scen_outage",
                "title": "Source Outage & Staleness Resilience",
                "description": "Two oracle feeds fail/stale out. The system gracefully continues on remaining active quorum (SOURCE_DEGRADED).",
                "scenario_type": "OUTAGE",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4050.0,
            },
        }

        self.reset("scen_normal", ltv=0.80)

    def reset(self, scenario_id: Optional[str] = None, ltv: Optional[float] = None, seed: int = 42):
        if scenario_id and scenario_id in self.fixtures:
            self.scenario_id = scenario_id
        elif scenario_id:
            # Fallback mapping for old IDs
            if "flash" in scenario_id or "spike" in scenario_id:
                self.scenario_id = "scen_flash_crash"
            elif "poison" in scenario_id:
                self.scenario_id = "scen_outlier"
            elif "dislocation" in scenario_id:
                self.scenario_id = "scen_disagreement"
            elif "outage" in scenario_id or "failure" in scenario_id:
                self.scenario_id = "scen_outage"
            else:
                self.scenario_id = "scen_normal"

        self.ltv = ltv if ltv is not None else 0.80
        self.seed = seed
        self.sim_time_seconds = 0.0
        self.is_running = False
        self.is_paused = False
        self.is_finalized = False
        self.last_wall_time = None
        self.collateral_amount = 10.0
        self.debt_amount = 28000.0

    def start(self):
        self.is_running = True
        self.is_paused = False
        self.last_wall_time = time.monotonic()

    def pause(self):
        self.is_running = False
        self.is_paused = True
        self.last_wall_time = None

    def step(self, delta_seconds: float = 600.0):
        self.sim_time_seconds = min(float(self.window_duration_seconds), self.sim_time_seconds + delta_seconds)
        if self.sim_time_seconds >= self.window_duration_seconds:
            self.is_finalized = True
            self.is_running = False

    def finalize(self):
        self.sim_time_seconds = float(self.window_duration_seconds)
        self.is_finalized = True
        self.is_running = False

    def set_speed(self, speed_multiplier: float):
        self.speed_multiplier = max(1.0, float(speed_multiplier))

    def update_position(
        self,
        collateral_amount: Optional[float] = None,
        debt_amount: Optional[float] = None,
        set_max_borrow: bool = False,
    ):
        if collateral_amount is not None:
            self.collateral_amount = max(0.0, float(collateral_amount))

        if set_max_borrow:
            snap = self.get_snapshot()
            self.debt_amount = max(0.0, float(snap["position"]["max_borrow_capacity"]))
        elif debt_amount is not None:
            self.debt_amount = max(0.0, float(debt_amount))

    def _tick_clock(self):
        if not self.is_running or self.is_paused or self.is_finalized:
            return

        now = time.monotonic()
        if self.last_wall_time is not None:
            elapsed_wall = now - self.last_wall_time
            sim_advance = elapsed_wall * self.speed_multiplier
            self.sim_time_seconds += sim_advance
            if self.sim_time_seconds >= self.window_duration_seconds:
                self.sim_time_seconds = float(self.window_duration_seconds)
                self.is_finalized = True
                self.is_running = False
        self.last_wall_time = now

    def _generate_oracle_feeds(self, t_sec: float, scen_type: str) -> Tuple[List[OracleObservationData], OracleObservationData, OracleObservationData]:
        now_ts = 1774000000 + int(t_sec)
        progress = min(1.0, t_sec / self.window_duration_seconds)

        # Baseline noise generator
        rnd = random.Random(self.seed + int(t_sec // 10))

        if scen_type == "NORMAL":
            # Feeds fluctuate tightly around $4,320
            spot = 4320.0 + 1.2 * math.sin(t_sec / 300.0)
            p_cl = spot + rnd.uniform(-0.4, 0.4)
            p_pyth = spot + rnd.uniform(-0.3, 0.3)
            p_chron = spot + rnd.uniform(-0.5, 0.5)
            p_rs = spot + rnd.uniform(-0.4, 0.4)
            p_supra = spot + rnd.uniform(-0.3, 0.3)
            p_api3 = spot + rnd.uniform(-0.4, 0.4)
            p_osm = 4320.0
            p_mkt = spot + rnd.uniform(-0.2, 0.2)

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(p_cl, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(p_pyth, 2), now_ts - 2, 2, "ACTIVE", 0.15, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(p_chron, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(p_rs, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(p_supra, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(p_api3, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", round(p_osm, 2), now_ts - int(t_sec), int(t_sec), "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(p_mkt, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "FLASH_CRASH":
            # Market drops from 4320 down to 4050; Multipli stays delayed @ 4380
            spot = 4320.0 - (270.0 * progress) + rnd.uniform(-0.5, 0.5)
            p_osm = 4380.0  # Stale delayed OSM value

            p_cl = spot + rnd.uniform(-0.4, 0.4)
            p_pyth = spot + rnd.uniform(-0.3, 0.3)
            p_chron = spot + rnd.uniform(-0.5, 0.5)
            p_rs = spot + rnd.uniform(-0.4, 0.4)
            p_supra = spot + rnd.uniform(-0.3, 0.3)
            p_api3 = spot + rnd.uniform(-0.4, 0.4)
            p_mkt = spot + rnd.uniform(-0.2, 0.2)

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(p_cl, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(p_pyth, 2), now_ts - 2, 2, "ACTIVE", 0.12, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(p_chron, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(p_rs, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(p_supra, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(p_api3, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", round(p_osm, 2), now_ts - int(t_sec), int(t_sec), "DELAYED", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(p_mkt, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "OUTLIER":
            # 5 feeds agree @ 4050; RedStone reports 9000
            spot = 4050.0 + rnd.uniform(-0.5, 0.5)
            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.2, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot + 0.1, 2), now_ts - 2, 2, "ACTIVE", 0.10, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(spot - 0.2, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", 9000.0, now_ts - 6, 6, "ACTIVE", None, False, True),  # Outlier
                OracleObservationData("supra_xau", "Supra", round(spot + 0.3, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(spot - 0.1, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4050.0, now_ts - 100, 100, "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "DISAGREEMENT":
            # Group A @ 4050; Group B @ 4450; Multipli @ 4300
            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", 4050.2, now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", 4051.0, now_ts - 2, 2, "ACTIVE", 0.20, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", 4049.8, now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", 4452.1, now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", 4450.7, now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", 4451.4, now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4300.0, now_ts - 200, 200, "DELAYED", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", 4050.0, now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "OUTAGE":
            # Chronicle stale, API3 failed, others active @ 4050
            spot = 4050.0 + rnd.uniform(-0.4, 0.4)
            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.1, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.1, 2), now_ts - 2, 2, "ACTIVE", 0.15, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", 4320.0, now_ts - 7200, 7200, "STALE", None, False, False),  # Stale
                OracleObservationData("redstone_xau", "RedStone", round(spot + 0.2, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(spot - 0.2, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", 0.0, 0, 0, "FAILED", None, False, False),  # Failed
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4050.0, now_ts - 300, 300, "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        else:
            feeds = []
            osm = OracleObservationData("multipli_osm", "Multipli", 4320.0, now_ts, 0, "ACTIVE")
            mkt = OracleObservationData("market_terminal", "Market Reference", 4320.0, now_ts, 0, "ACTIVE")

        return feeds, osm, mkt

    def get_snapshot(self) -> Dict[str, Any]:
        self._tick_clock()

        t_sec = self.sim_time_seconds
        fixture = self.fixtures[self.scenario_id]
        scen_type = fixture["scenario_type"]

        # 1. Generate Oracle Observations
        oracle_feeds, multipli_obs, market_obs = self._generate_oracle_feeds(t_sec, scen_type)

        # 2. Consensus Agreement Clustering
        consensus = self.consensus_engine.compute_consensus(oracle_feeds)

        # Assign cluster IDs to feeds
        for f in oracle_feeds:
            if f.source_id in consensus.cluster_members:
                f.cluster_id = "A"
            elif f.status != "ACTIVE":
                f.cluster_id = "OFFLINE"
            else:
                f.cluster_id = "OUTLIER"

        multipli_obs.cluster_id = "A" if (abs(multipli_obs.price - consensus.consensus_price) / max(0.001, consensus.consensus_price) <= 0.005) else "OUTLIER"

        # 3. Risk Decision Engine Evaluation
        decision = self.decision_engine.evaluate_decision(
            consensus=consensus,
            multipli_obs=multipli_obs,
            market_ref_price=market_obs.price,
        )

        # 4. Downstream Protocol & Collateral Calculations
        effective_price = decision.final_price if decision.final_price > 0 else (consensus.consensus_price if consensus.consensus_price > 0 else multipli_obs.price)
        collateral_value = round(self.collateral_amount * effective_price, 2)
        max_borrow_capacity = round(collateral_value * decision.effective_ltv, 2)
        current_ltv = round(self.debt_amount / max(0.0001, collateral_value), 4) if collateral_value > 0 else 0.0
        borrowing_headroom = round(max_borrow_capacity - self.debt_amount, 2)

        if self.debt_amount <= 0.0001:
            health_factor = 999.0
        elif collateral_value <= 0.0001:
            health_factor = 0.0
        else:
            health_factor = round(max_borrow_capacity / self.debt_amount, 2)

        if decision.protocol_state == "HALTED":
            position_status = "HALTED"
        elif self.debt_amount > max_borrow_capacity:
            position_status = "OVER_LIMIT" if decision.protocol_state == "NORMAL" else "RESTRICTED"
        elif health_factor < 1.10:
            position_status = "AT_RISK"
        else:
            position_status = "HEALTHY"

        position_dict = {
            "user_address": self.user_address,
            "collateral_asset": self.collateral_asset,
            "collateral_amount": round(self.collateral_amount, 2),
            "collateral_value": collateral_value,
            "effective_oracle_price": round(effective_price, 2),
            "debt_amount": round(self.debt_amount, 2),
            "current_ltv": current_ltv,
            "effective_ltv": decision.effective_ltv,
            "max_borrow_capacity": max_borrow_capacity,
            "borrowing_headroom": borrowing_headroom,
            "health_factor": health_factor,
            "protocol_state": decision.protocol_state,
            "position_status": position_status,
        }

        causal_chain_dict = {
            "multipli_price": round(multipli_obs.price, 2),
            "consensus_price": round(consensus.consensus_price, 2),
            "market_price": round(market_obs.price, 2),
            "deviation_pct": decision.multipli_deviation_pct,
            "agreement_ratio": consensus.agreement_ratio,
            "oracle_state": decision.state,
            "selected_price": round(decision.final_price, 2),
            "effective_ltv": decision.effective_ltv,
            "max_borrow_capacity": max_borrow_capacity,
            "position_status": position_status,
        }

        # 5. Time Series Trajectory
        total_mins = int(t_sec // 60)
        time_series = []
        for m in range(max(0, total_mins - 60), total_mins + 1):
            t_sample = m * 60.0
            s_feeds, s_osm, s_mkt = self._generate_oracle_feeds(t_sample, scen_type)
            s_cons = self.consensus_engine.compute_consensus(s_feeds)
            time_series.append({
                "minute": m,
                "time_label": f"{m:02d}:00",
                "p_multipli": round(s_osm.price, 2) if s_osm.price > 0 else None,
                "p_consensus": round(s_cons.consensus_price, 2) if s_cons.consensus_price > 0 else None,
                "p_market": round(s_mkt.price, 2) if s_mkt.price > 0 else None,
                "cluster_min": round(s_cons.cluster_min, 2) if s_cons.cluster_min > 0 else None,
                "cluster_max": round(s_cons.cluster_max, 2) if s_cons.cluster_max > 0 else None,
            })

        # 6. Live Events Feed
        events = self._generate_events(t_sec, scen_type, consensus, decision)

        # 7. System Interpretation
        interpretation = self._generate_interpretation(scen_type, consensus, decision, multipli_obs)

        elapsed_mins = int(t_sec // 60)
        elapsed_secs_remainder = int(t_sec % 60)
        sim_time_formatted = f"{elapsed_mins:02d}:{elapsed_secs_remainder:02d}"

        return {
            "scenario_id": fixture["scenario_id"],
            "title": fixture["title"],
            "description": fixture["description"],
            "asset": fixture["asset"],
            "simulation_time_seconds": round(t_sec, 1),
            "simulation_time_formatted": sim_time_formatted,
            "elapsed_minutes": elapsed_mins,
            "window_duration_seconds": self.window_duration_seconds,
            "speed_multiplier": self.speed_multiplier,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "is_finalized": self.is_finalized,
            "current_block": f"SIM-{18400 + int(t_sec // 12)}",
            "oracle_sources": [
                {
                    "source_id": f.source_id,
                    "name": f.name,
                    "price": f.price,
                    "updated_at": f.updated_at,
                    "age_seconds": f.age_seconds,
                    "status": f.status,
                    "confidence": f.confidence,
                    "has_confidence": f.has_confidence,
                    "valid": f.valid,
                    "cluster_id": f.cluster_id,
                }
                for f in oracle_feeds
            ],
            "multipli_observation": {
                "source_id": multipli_obs.source_id,
                "name": multipli_obs.name,
                "price": multipli_obs.price,
                "updated_at": multipli_obs.updated_at,
                "age_seconds": multipli_obs.age_seconds,
                "status": multipli_obs.status,
                "confidence": multipli_obs.confidence,
                "has_confidence": multipli_obs.has_confidence,
                "valid": multipli_obs.valid,
                "cluster_id": multipli_obs.cluster_id,
            },
            "market_observation": {
                "source_id": market_obs.source_id,
                "name": market_obs.name,
                "price": market_obs.price,
                "updated_at": market_obs.updated_at,
                "age_seconds": market_obs.age_seconds,
                "status": market_obs.status,
                "confidence": market_obs.confidence,
                "has_confidence": market_obs.has_confidence,
                "valid": market_obs.valid,
                "cluster_id": "MKT",
            },
            "consensus": {
                "consensus_price": consensus.consensus_price,
                "cluster_size": consensus.cluster_size,
                "total_eligible": consensus.total_eligible,
                "agreement_ratio": consensus.agreement_ratio,
                "cluster_min": consensus.cluster_min,
                "cluster_max": consensus.cluster_max,
                "cluster_spread_pct": consensus.cluster_spread_pct,
                "has_strong_consensus": consensus.has_strong_consensus,
                "cluster_members": consensus.cluster_members,
                "outlier_members": consensus.outlier_members,
            },
            "decision": {
                "state": decision.state,
                "oracle_status": decision.oracle_status,
                "final_price": decision.final_price,
                "multipli_deviation_pct": decision.multipli_deviation_pct,
                "is_conservative_applied": decision.is_conservative_applied,
                "policy_rationale": decision.policy_rationale,
                "effective_ltv": decision.effective_ltv,
                "protocol_state": decision.protocol_state,
            },
            "position": position_dict,
            "causal_chain": causal_chain_dict,
            "time_series": time_series,
            "events": events,
            "interpretation": interpretation,
        }

    def _generate_events(
        self,
        t_sec: float,
        scen_type: str,
        consensus: ConsensusMetrics,
        decision: RiskDecisionOutput,
    ) -> List[Dict[str, Any]]:
        events = []
        events.append({
            "timestamp": "00:00",
            "category": "INITIALIZATION",
            "message": "AEGIS Cross-Oracle Risk Layer connected to Multipli OSM and 6 external oracle adapters",
            "severity": "INFO",
        })

        if t_sec >= 15:
            events.append({
                "timestamp": "00:15",
                "category": "CONSENSUS",
                "message": f"Initial agreement cluster formed across {consensus.cluster_size}/{consensus.total_eligible} feeds (Spread: {consensus.cluster_spread_pct:.2f}%)",
                "severity": "SUCCESS",
            })

        if scen_type == "FLASH_CRASH" and t_sec >= 600:
            events.append({
                "timestamp": "10:00",
                "category": "MARKET",
                "message": "Macro spot price dropping across Chainlink, Pyth, Chronicle, RedStone, Supra, API3",
                "severity": "WARNING",
            })
            if t_sec >= 1200:
                events.append({
                    "timestamp": "20:00",
                    "category": "ORACLE_DEVIATION",
                    "message": "Multipli OSM delayed at $4,380.00 while external oracle consensus falls to ~$4,160.00",
                    "severity": "ALERT",
                })
            if t_sec >= 1800:
                events.append({
                    "timestamp": "30:00",
                    "category": "RISK_DECISION",
                    "message": "MULTIPLI_DEVIATION detected (>3.0% divergence). Conservative valuation enforced = min(P_OSM, P_CONSENSUS)",
                    "severity": "ALERT",
                })
                events.append({
                    "timestamp": "30:05",
                    "category": "PROTOCOL",
                    "message": "Downstream RWAUSD Protocol risk state restricted: Max LTV capped from 80% to 50%",
                    "severity": "WARNING",
                })
                events.append({
                    "timestamp": "30:10",
                    "category": "AUDIT",
                    "message": "Collateral overstatement prevented: Successfully protected vault from bad debt accumulation",
                    "severity": "SUCCESS",
                })

        elif scen_type == "OUTLIER" and t_sec >= 300:
            events.append({
                "timestamp": "05:00",
                "category": "OUTLIER",
                "message": "RedStone feed anomaly detected ($9,000.00). Price-band clustering isolated outlier without consensus corruption",
                "severity": "SUCCESS",
            })

        elif scen_type == "DISAGREEMENT" and t_sec >= 300:
            events.append({
                "timestamp": "05:00",
                "category": "CIRCUIT_BREAKER",
                "message": "Bimodal disagreement detected across oracle networks ($4,050 vs $4,450). Emergency halt engaged",
                "severity": "CRITICAL",
            })

        elif scen_type == "OUTAGE" and t_sec >= 300:
            events.append({
                "timestamp": "05:00",
                "category": "FAULT_TOLERANCE",
                "message": "Chronicle feed stale and API3 failed. Quorum preserved across 4 active independent feeds",
                "severity": "WARNING",
            })

        return events[-25:][::-1]

    def _generate_interpretation(
        self,
        scen_type: str,
        consensus: ConsensusMetrics,
        decision: RiskDecisionOutput,
        multipli_obs: OracleObservationData,
    ) -> str:
        if scen_type == "NORMAL":
            return (
                f"Multipli OSM (${multipli_obs.price:.2f}) and all {consensus.cluster_size} external oracle feeds "
                f"agree in tight consensus around ${consensus.consensus_price:.2f} (cluster spread: {consensus.cluster_spread_pct:.2f}%). "
                f"Protocol maintains standard 80% LTV under HEALTHY_CONSENSUS."
            )
        elif scen_type == "FLASH_CRASH":
            return (
                f"Multipli OSM remains delayed at ${multipli_obs.price:.2f} while {consensus.cluster_size} external oracle feeds "
                f"corroborate an intraday market drop to ${consensus.consensus_price:.2f} (deviation: {decision.multipli_deviation_pct:.2f}%). "
                f"AEGIS has engaged MULTIPLI_DEVIATION, applied conservative valuation min(P_OSM, P_CONSENSUS) = ${decision.final_price:.2f}, "
                f"and restricted downstream LTV to 50%, preventing unbacked collateral overstatement."
            )
        elif scen_type == "OUTLIER":
            return (
                f"One oracle feed submitted an anomalous outlier quote ($9,000.00). Deterministic price-band clustering "
                f"isolated the outlier to cluster 'OUTLIER', preserving consensus across {consensus.cluster_size} honest feeds "
                f"at ${consensus.consensus_price:.2f} without disrupting protocol operations."
            )
        elif scen_type == "DISAGREEMENT":
            return (
                "External oracle networks split into contradictory bimodal groups ($4,050 vs $4,450). No dominant agreement "
                "cluster exists (>60%). AEGIS triggered ORACLE_INSTABILITY, halting new borrowing to protect system solvency."
            )
        elif scen_type == "OUTAGE":
            return (
                f"Two oracle feeds are unavailable (Chronicle stale, API3 failed). AEGIS successfully maintained quorum "
                f"across {consensus.cluster_size} active feeds at ${consensus.consensus_price:.2f} under SOURCE_DEGRADED."
            )
        else:
            return f"AEGIS Cross-Oracle Risk Layer is actively monitoring multi-oracle consensus. Status: {decision.state}."
