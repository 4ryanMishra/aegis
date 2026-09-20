"""
AEGIS Simulation Engine (Phase 5 - Cross-Oracle Architecture).
Deterministic, seeded, real-time accelerated simulation of multi-oracle cross-checking.
"""

import time
import math
from typing import Dict, List, Optional, Any, Tuple

from services.api.src.oracles.consensus_engine import ConsensusEngine, OracleObservationData, ConsensusMetrics
from services.api.src.oracles.risk_decision_engine import RiskDecisionEngine, RiskDecisionOutput


def interpolate_piecewise(t_sec: float, points: List[Tuple[float, float]]) -> float:
    """Deterministic piecewise linear interpolation between (t_seconds, value) points."""
    if t_sec <= points[0][0]:
        return points[0][1]
    if t_sec >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        t0, v0 = points[i]
        t1, v1 = points[i + 1]
        if t0 <= t_sec <= t1:
            ratio = (t_sec - t0) / (t1 - t0) if t1 > t0 else 0.0
            return v0 + ratio * (v1 - v0)
    return points[-1][1]


class SimulationEngine:
    """
    Authoritative stateful simulation runtime managing multi-oracle feeds, consensus clustering,
    risk decision policies, and downstream collateralized protocol positions.
    """

    def __init__(self):
        self.consensus_engine = ConsensusEngine(cluster_tolerance_pct=0.50, min_quorum=3, min_agreement_ratio=0.60)
        self.decision_engine = RiskDecisionEngine(
            normal_threshold_pct=0.50,
            deviation_threshold_pct=1.00,
            critical_threshold_pct=3.00,
            standard_ltv=0.80,
            restricted_ltv=0.50,
        )

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
                "title": "Scenario 1: Normal Multi-Oracle Convergence",
                "description": "Multipli OSM and all 6 external oracle feeds agree in tight consensus (~$4,320/oz). Standard 80% LTV maintained.",
                "scenario_type": "NORMAL",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "NORMAL START", "description": "All 7 feeds aligned within 0.1%", "severity": "SUCCESS"},
                    {"time_seconds": 900, "time_formatted": "15:00", "title": "STABLE CONSENSUS", "description": "Continuous tight spread <= 0.05%", "severity": "INFO"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "MID-WINDOW CHECK", "description": "Quorum verified (6/6 agree)", "severity": "INFO"},
                    {"time_seconds": 2700, "time_formatted": "45:00", "title": "LOW VOLATILITY", "description": "Normal 80% LTV capacity active", "severity": "INFO"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "VERIFIED FINALIZATION", "description": "Clean settlement at $4,320.00", "severity": "SUCCESS"},
                ],
            },
            "scen_flash_crash": {
                "scenario_id": "scen_flash_crash",
                "title": "Scenario 2: Multipli OSM Divergence (Hero Demo)",
                "description": "Spot market plunges to ~$4,000 across independent feeds while Multipli OSM remains delayed at $4,320. AEGIS detects divergence, enforces conservative valuation min(OSM, Consensus), and dampens LTV to 50%.",
                "scenario_type": "FLASH_CRASH",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "ALIGNED CONVERGENCE", "description": "Initial agreement at $4,320", "severity": "SUCCESS"},
                    {"time_seconds": 600, "time_formatted": "10:00", "title": "MARKET DROP BEGINS", "description": "External oracles fall to $4,250", "severity": "WARNING"},
                    {"time_seconds": 1200, "time_formatted": "20:00", "title": "DIVERGENCE THRESHOLD", "description": "OSM delayed; dev exceeds 3.0%", "severity": "ALERT"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "LTV DAMPENED (50%)", "description": "Conservative min($4320, $4050) enforced", "severity": "ALERT"},
                    {"time_seconds": 2700, "time_formatted": "45:00", "title": "BAD DEBT BLOCKED", "description": "Over $14,500 bad debt prevented", "severity": "SUCCESS"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "PROTECTED SETTLEMENT", "description": "Vault 100% solvent at $4,000 valuation", "severity": "SUCCESS"},
                ],
            },
            "scen_outlier": {
                "scenario_id": "scen_outlier",
                "title": "Scenario 3: Single Oracle Outlier Isolation",
                "description": "One anomalous feed reports $9,000 while 5 external feeds and Multipli agree at ~$4,320. Price-band clustering isolates the outlier and preserves consensus.",
                "scenario_type": "OUTLIER",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "CLUSTERING ACTIVE", "description": "Band clustering initialized", "severity": "INFO"},
                    {"time_seconds": 900, "time_formatted": "15:00", "title": "OUTLIER ISOLATED", "description": "RedStone ($9,000) rejected from Cluster A", "severity": "SUCCESS"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "CONSENSUS PRESERVED", "description": "6/7 feeds agree in Cluster A", "severity": "SUCCESS"},
                    {"time_seconds": 2700, "time_formatted": "45:00", "title": "STABLE OPERATION", "description": "Standard 80% LTV maintained", "severity": "INFO"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "ROBUST SETTLEMENT", "description": "Settled at $4,320.00 without disruption", "severity": "SUCCESS"},
                ],
            },
            "scen_disagreement": {
                "scenario_id": "scen_disagreement",
                "title": "Scenario 4: Bimodal Multi-Oracle Disagreement",
                "description": "Oracle networks split into two contradictory clusters ($4,050 vs $4,450). No dominant consensus exists. Terminal market reference resolves ambiguity at T+40 or triggers circuit breaker.",
                "scenario_type": "DISAGREEMENT",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4050.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "BIMODAL SPLIT", "description": "Group A ($4050) vs Group B ($4450)", "severity": "ALERT"},
                    {"time_seconds": 900, "time_formatted": "15:00", "title": "NO CONSENSUS (HALT)", "description": "Circuit breaker active; borrows frozen", "severity": "CRITICAL"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "DISPERSION PERSISTS", "description": "Multipli ($4300) dislocated from both", "severity": "CRITICAL"},
                    {"time_seconds": 2400, "time_formatted": "40:00", "title": "MARKET CHECK", "description": "Spot reference corroborates Group A", "severity": "WARNING"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "CORROBORATED SETTLE", "description": "Restricted settlement at $4,050.00 (50% LTV)", "severity": "SUCCESS"},
                ],
            },
            "scen_outage": {
                "scenario_id": "scen_outage",
                "title": "Scenario 5: Source Outage & Staleness Resilience",
                "description": "Chronicle feed is stale and API3 fails. Quorum is preserved across remaining 4 active feeds, demonstrating graceful degradation.",
                "scenario_type": "OUTAGE",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4050.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "HEALTH SCAN", "description": "Scanning 6 oracle adapters", "severity": "INFO"},
                    {"time_seconds": 900, "time_formatted": "15:00", "title": "CHRONICLE STALE", "description": "Chronicle timestamp > 2 hours old", "severity": "WARNING"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "API3 OUTAGE", "description": "API3 dAPI unreachable / zero quote", "severity": "WARNING"},
                    {"time_seconds": 2700, "time_formatted": "45:00", "title": "4-FEED QUORUM", "description": "Chainlink, Pyth, RedStone, Supra active", "severity": "SUCCESS"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "DEGRADED SETTLE", "description": "Settled under SOURCE_DEGRADED (80% LTV)", "severity": "SUCCESS"},
                ],
            },
            "scen_recovery": {
                "scenario_id": "scen_recovery",
                "title": "Scenario 6: Dynamic Recovery & Consensus Restored",
                "description": "Demonstrates AEGIS dynamically transitioning from healthy -> divergence -> restriction -> reconvergence -> consensus restored.",
                "scenario_type": "RECOVERY",
                "asset": "Tokenized Gold (XAU/USD)",
                "base_price": 4320.0,
                "ltv_default": 0.80,
                "timeline_markers": [
                    {"time_seconds": 0, "time_formatted": "00:00", "title": "HEALTHY START", "description": "All feeds agree at $4,320", "severity": "SUCCESS"},
                    {"time_seconds": 900, "time_formatted": "15:00", "title": "DIVERGENCE BEGINS", "description": "External feeds dip to $4,180", "severity": "WARNING"},
                    {"time_seconds": 1800, "time_formatted": "30:00", "title": "RESTRICTED MODE", "description": "LTV capped at 50% (min price)", "severity": "ALERT"},
                    {"time_seconds": 2700, "time_formatted": "45:00", "title": "RECONVERGENCE", "description": "Feeds rally back toward $4,315", "severity": "INFO"},
                    {"time_seconds": 3600, "time_formatted": "60:00", "title": "CONSENSUS RESTORED", "description": "Returned to HEALTHY (80% LTV)", "severity": "SUCCESS"},
                ],
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
            elif "recovery" in scenario_id or "restore" in scenario_id:
                self.scenario_id = "scen_recovery"
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

    def step(self, delta_seconds: float = 900.0):
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

    def _generate_oracle_feeds(
        self, t_sec: float, scen_type: str
    ) -> Tuple[List[OracleObservationData], OracleObservationData, OracleObservationData]:
        now_ts = 1774000000 + int(t_sec)

        # Micro smooth harmonic noise based on simulation time
        w = t_sec / 300.0
        micro_noise = 0.3 * math.sin(w * 1.7) + 0.2 * math.cos(w * 3.1)

        if scen_type == "NORMAL":
            # Scenario 1: Normal Convergence (~$4,320)
            # T+00: 4320, T+15: 4321, T+30: 4319, T+45: 4322, T+60: 4320
            points = [(0.0, 4320.0), (900.0, 4321.0), (1800.0, 4319.0), (2700.0, 4322.0), (3600.0, 4320.0)]
            spot = interpolate_piecewise(t_sec, points) + micro_noise
            p_osm = 4320.0 + 0.5 * math.sin(t_sec / 600.0)

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.15, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.10, 2), now_ts - 2, 2, "ACTIVE", 0.12, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(spot + 0.30, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(spot - 0.20, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(spot + 0.05, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(spot - 0.15, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", round(p_osm, 2), now_ts - int(min(3600, t_sec + 60)), int(min(3600, t_sec + 60)), "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "FLASH_CRASH":
            # Scenario 2: Multipli Divergence / Hero Demo
            # Multipli delayed at 4320.0
            # Others: T+0: 4320, T+10: 4250, T+20: 4160, T+30: 4050, T+45: 4010, T+60: 4000
            points = [
                (0.0, 4320.0),
                (600.0, 4250.0),
                (1200.0, 4160.0),
                (1800.0, 4050.0),
                (2700.0, 4010.0),
                (3600.0, 4000.0),
            ]
            spot = interpolate_piecewise(t_sec, points) + micro_noise
            p_osm = 4320.0  # Delayed baseline OSM value

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.20, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.15, 2), now_ts - 2, 2, "ACTIVE", 0.15, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(spot + 0.35, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(spot - 0.25, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(spot + 0.10, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(spot - 0.20, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", round(p_osm, 2), now_ts - int(min(3600, t_sec + 600)), int(min(3600, t_sec + 600)), "DELAYED", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "OUTLIER":
            # Scenario 3: Single Oracle Outlier Isolation ($9,000 Outlier)
            spot = 4320.0 + micro_noise
            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.15, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.10, 2), now_ts - 2, 2, "ACTIVE", 0.10, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(spot + 0.25, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", 9000.0, now_ts - 6, 6, "ACTIVE", None, False, True),  # Outlier quote
                OracleObservationData("supra_xau", "Supra", round(spot + 0.10, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(spot - 0.15, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4320.0, now_ts - 100, 100, "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "DISAGREEMENT":
            # Scenario 4: Bimodal Disagreement ($4,050 vs $4,450)
            # Group A @ 4050, Group B @ 4450, Multipli @ 4300
            # For t < 2400s (40m): Market reference is uncorroborated @ 4250
            # For t >= 2400s (40m): Market reference firmly corroborates Group A @ 4050
            p_a = 4050.0 + micro_noise
            p_b = 4450.0 + micro_noise
            p_mkt = 4050.0 if t_sec >= 2400.0 else 4250.0

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(p_a + 0.20, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(p_a - 0.10, 2), now_ts - 2, 2, "ACTIVE", 0.15, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(p_a + 0.10, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(p_b + 0.30, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(p_b - 0.20, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(p_b + 0.10, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4300.0, now_ts - 200, 200, "DELAYED", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(p_mkt, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "OUTAGE":
            # Scenario 5: Source Outage (Chronicle Stale, API3 Failed)
            spot = 4050.0 + micro_noise
            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.15, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.10, 2), now_ts - 2, 2, "ACTIVE", 0.15, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", 4320.0, now_ts - 7200, 7200, "STALE", None, False, False),
                OracleObservationData("redstone_xau", "RedStone", round(spot + 0.20, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(spot - 0.15, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", 0.0, 0, 0, "FAILED", None, False, False),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", 4050.0, now_ts - 300, 300, "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        elif scen_type == "RECOVERY":
            # Scenario 6: Recovery & Reconvergence
            # T+0: 4320, T+15: 4180, T+30: 4150, T+45: 4310, T+60: 4320
            points = [
                (0.0, 4320.0),
                (900.0, 4180.0),
                (1800.0, 4150.0),
                (2700.0, 4310.0),
                (3600.0, 4320.0),
            ]
            spot = interpolate_piecewise(t_sec, points) + micro_noise
            p_osm = 4320.0

            feeds = [
                OracleObservationData("chainlink_main", "Chainlink", round(spot + 0.15, 2), now_ts - 4, 4, "ACTIVE", None, False, True),
                OracleObservationData("pyth_gold", "Pyth", round(spot - 0.10, 2), now_ts - 2, 2, "ACTIVE", 0.12, True, True),
                OracleObservationData("chronicle_gold", "Chronicle", round(spot + 0.25, 2), now_ts - 9, 9, "ACTIVE", None, False, True),
                OracleObservationData("redstone_xau", "RedStone", round(spot - 0.20, 2), now_ts - 6, 6, "ACTIVE", None, False, True),
                OracleObservationData("supra_xau", "Supra", round(spot + 0.05, 2), now_ts - 5, 5, "ACTIVE", None, False, True),
                OracleObservationData("api3_xau", "API3", round(spot - 0.15, 2), now_ts - 8, 8, "ACTIVE", None, False, True),
            ]
            osm = OracleObservationData("multipli_osm", "Multipli", round(p_osm, 2), now_ts - int(min(3600, t_sec + 60)), int(min(3600, t_sec + 60)), "ACTIVE", None, False, True)
            mkt = OracleObservationData("market_terminal", "Market Reference", round(spot, 2), now_ts, 0, "ACTIVE", None, False, True)

        else:
            feeds = []
            osm = OracleObservationData("multipli_osm", "Multipli", 4320.0, now_ts, 0, "ACTIVE")
            mkt = OracleObservationData("market_terminal", "Market Reference", 4320.0, now_ts, 0, "ACTIVE")

        return feeds, osm, mkt

    def get_snapshot(self) -> Dict[str, Any]:
        self._tick_clock()

        t_sec = self.sim_time_seconds
        fixture = self.fixtures.get(self.scenario_id, self.fixtures["scen_normal"])
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
            elif scen_type == "DISAGREEMENT" and f.source_id in ("redstone_xau", "supra_xau", "api3_xau"):
                f.cluster_id = "B"
            else:
                f.cluster_id = "OUTLIER"

        if consensus.consensus_price > 0 and multipli_obs.price > 0:
            dev_osm = abs(multipli_obs.price - consensus.consensus_price) / consensus.consensus_price
            multipli_obs.cluster_id = "A" if dev_osm <= 0.005 else "OUTLIER"
        else:
            multipli_obs.cluster_id = "OUTLIER"

        # 3. Risk Decision Engine Evaluation
        decision = self.decision_engine.evaluate_decision(
            consensus=consensus,
            multipli_obs=multipli_obs,
            market_ref_price=market_obs.price,
        )

        # 4. Downstream Protocol & Collateral Calculations
        # Under HALTED, effective price is locked / 0.0
        if decision.protocol_state == "HALTED":
            effective_price = 0.0
            collateral_value = 0.0
            max_borrow_capacity = 0.0
            current_ltv = 0.0
            borrowing_headroom = 0.0
            health_factor = 0.0
            position_status = "HALTED"
            bad_debt_prevented = 0.0
        else:
            effective_price = decision.final_price if decision.final_price > 0 else consensus.consensus_price
            collateral_value = round(self.collateral_amount * effective_price, 2)
            max_borrow_capacity = round(collateral_value * decision.effective_ltv, 2)
            current_ltv = round(self.debt_amount / max(0.0001, collateral_value), 4) if collateral_value > 0 else 0.0
            borrowing_headroom = round(max_borrow_capacity - self.debt_amount, 2)

            # Baseline unverified OSM borrow capacity
            unverified_osm_borrow = round(self.collateral_amount * multipli_obs.price * 0.80, 2)
            bad_debt_prevented = max(0.0, round(unverified_osm_borrow - max_borrow_capacity, 2)) if decision.is_conservative_applied else 0.0

            if self.debt_amount <= 0.0001:
                health_factor = 999.0
            elif collateral_value <= 0.0001:
                health_factor = 0.0
            else:
                health_factor = round(max_borrow_capacity / self.debt_amount, 2)

            if decision.protocol_state == "RESTRICTED":
                position_status = "RESTRICTED"
            elif self.debt_amount > max_borrow_capacity:
                position_status = "OVER_LIMIT"
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
            "bad_debt_prevented": bad_debt_prevented,
        }

        causal_chain_dict = {
            "multipli_price": round(multipli_obs.price, 2) if multipli_obs.price > 0 else None,
            "consensus_price": round(consensus.consensus_price, 2) if consensus.consensus_price > 0 else None,
            "market_price": round(market_obs.price, 2) if market_obs.price > 0 else None,
            "deviation_pct": decision.multipli_deviation_pct,
            "agreement_ratio": consensus.agreement_ratio,
            "oracle_state": decision.state,
            "selected_price": round(decision.final_price, 2) if decision.final_price > 0 else None,
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
            "timeline_markers": fixture.get("timeline_markers", []),
            "bad_debt_prevented": bad_debt_prevented,
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
                "selected_source": decision.selected_source,
                "consensus_price": decision.consensus_price,
                "cluster_size": decision.cluster_size,
                "total_eligible": decision.total_eligible,
                "multipli_deviation_pct": decision.multipli_deviation_pct,
                "is_conservative_applied": decision.is_conservative_applied,
                "market_reference_used": decision.market_reference_used,
                "policy_rationale": decision.policy_rationale,
                "effective_ltv": decision.effective_ltv,
                "protocol_state": decision.protocol_state,
                "action": decision.action,
                "decision": decision.decision,
                "policy": decision.policy,
                "reason_codes": decision.reason_codes,
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

        if scen_type == "FLASH_CRASH":
            if t_sec >= 600:
                events.append({
                    "timestamp": "10:00",
                    "category": "MARKET",
                    "message": "Macro spot price dropping across Chainlink, Pyth, Chronicle, RedStone, Supra, API3 ($4,250)",
                    "severity": "WARNING",
                })
            if t_sec >= 1200:
                events.append({
                    "timestamp": "20:00",
                    "category": "ORACLE_DEVIATION",
                    "message": "Multipli OSM delayed at $4,320.00 while external oracle consensus falls to ~$4,160.00",
                    "severity": "ALERT",
                })
            if t_sec >= 1800:
                events.append({
                    "timestamp": "30:00",
                    "category": "RISK_DECISION",
                    "message": "MULTIPLI_DEVIATION detected (>1.0% divergence). Conservative valuation enforced = min(P_OSM, P_CONSENSUS)",
                    "severity": "ALERT",
                })
                events.append({
                    "timestamp": "30:05",
                    "category": "PROTOCOL",
                    "message": "Downstream RWAUSD Protocol risk state restricted: Max LTV capped from 80% to 50%",
                    "severity": "WARNING",
                })
            if t_sec >= 2700:
                events.append({
                    "timestamp": "45:00",
                    "category": "AUDIT",
                    "message": "Collateral overstatement prevented: Successfully protected vault from bad debt accumulation",
                    "severity": "SUCCESS",
                })

        elif scen_type == "OUTLIER" and t_sec >= 300:
            events.append({
                "timestamp": "05:00",
                "category": "OUTLIER",
                "message": "RedStone observation is an outlier ($9,000.00) relative to consensus cluster. Isolated without corruption.",
                "severity": "SUCCESS",
            })

        elif scen_type == "DISAGREEMENT":
            if t_sec < 2400:
                events.append({
                    "timestamp": "05:00",
                    "category": "CIRCUIT_BREAKER",
                    "message": "Bimodal disagreement detected across oracle networks ($4,050 vs $4,450). Emergency halt engaged",
                    "severity": "CRITICAL",
                })
            else:
                events.append({
                    "timestamp": "40:00",
                    "category": "MARKET_CHECK",
                    "message": "Terminal market reference ($4,050.00) corroborates Group A cluster. Switched to RESTRICTED mode (50% LTV)",
                    "severity": "WARNING",
                })

        elif scen_type == "OUTAGE" and t_sec >= 300:
            events.append({
                "timestamp": "05:00",
                "category": "FAULT_TOLERANCE",
                "message": "Chronicle feed stale and API3 failed. Quorum preserved across 4 active independent feeds",
                "severity": "WARNING",
            })

        elif scen_type == "RECOVERY":
            if t_sec >= 900:
                events.append({
                    "timestamp": "15:00",
                    "category": "DEVIATION",
                    "message": "External feeds diverge to $4,180.00 while Multipli remains at $4,320.00",
                    "severity": "WARNING",
                })
            if t_sec >= 1800:
                events.append({
                    "timestamp": "30:00",
                    "category": "RESTRICTION",
                    "message": "Conservative restriction active at $4,150.00 (50% LTV)",
                    "severity": "ALERT",
                })
            if t_sec >= 2700:
                events.append({
                    "timestamp": "45:00",
                    "category": "RECONVERGENCE",
                    "message": "External feeds reconverging back toward Multipli OSM ($4,310.00)",
                    "severity": "INFO",
                })
            if t_sec >= 3300:
                events.append({
                    "timestamp": "55:00",
                    "category": "RESTORED",
                    "message": "Consensus restored within normal 0.50% tolerance band. 80% LTV re-enabled.",
                    "severity": "SUCCESS",
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
                f"and restricted downstream LTV to 50%, preventing unbacked collateral overstatement and bad debt."
            )
        elif scen_type == "OUTLIER":
            return (
                f"One oracle feed submitted an anomalous outlier quote ($9,000.00). Deterministic price-band clustering "
                f"isolated the outlier to cluster 'OUTLIER', preserving consensus across {consensus.cluster_size} eligible feeds "
                f"at ${consensus.consensus_price:.2f} without disrupting protocol operations."
            )
        elif scen_type == "DISAGREEMENT":
            if decision.market_reference_used:
                return (
                    f"External oracles split into bimodal clusters ($4,050 vs $4,450). Terminal market reference ($4,050.00) "
                    f"corroborated Group A. AEGIS enforced MARKET_CORROBORATED with a restricted 50% LTV ceiling."
                )
            else:
                return (
                    "External oracle networks split into contradictory bimodal groups ($4,050 vs $4,450) without consensus. "
                    "AEGIS triggered ORACLE_INSTABILITY with circuit breaker HALTED to protect system solvency."
                )
        elif scen_type == "OUTAGE":
            return (
                f"Two oracle feeds are unavailable (Chronicle stale, API3 failed). AEGIS successfully maintained quorum "
                f"across {consensus.cluster_size} active feeds at ${consensus.consensus_price:.2f} under SOURCE_DEGRADED."
            )
        elif scen_type == "RECOVERY":
            if decision.state == "HEALTHY_CONSENSUS":
                return (
                    f"External oracle consensus successfully reconverged with Multipli OSM at ${consensus.consensus_price:.2f}. "
                    f"Consensus is restored within normal tolerance (<= 0.50%), restoring standard 80% LTV."
                )
            else:
                return (
                    f"Dynamic recovery in progress. External oracles (${consensus.consensus_price:.2f}) are reconverging "
                    f"toward Multipli OSM (${multipli_obs.price:.2f}). Status: {decision.state}."
                )
        else:
            return f"AEGIS Cross-Oracle Risk Layer is actively monitoring multi-oracle consensus. Status: {decision.state}."
