"""
AEGIS Scenario Runner (Phase 4C).
Executes the five canonical verification scenarios in an end-to-end simulated flow:
  Scenario A: Normal Operation (HEALTHY_CONSENSUS) -> Protocol NORMAL (80% LTV)
  Scenario B: Flash Crash Detection (EVIDENCE_OF_ABNORMAL_DEVIATION) -> Protocol RESTRICTED (50% LTV)
  Scenario C: Poisoned Validator Isolation (Median Suppression) -> Protocol NORMAL (80% LTV)
  Scenario D: Market Observer Dislocation (P_DEC != P_MARKET) -> Protocol RESTRICTED (50% LTV)
  Scenario E: Upstream OSM Read Failure -> Protocol Fallback / Failsafe
"""

from typing import Dict, Any, List
import numpy as np

from packages.client.validator_client import ValidatorNodeClient, LaneType
from packages.client.keeper_orchestrator import KeeperOrchestrator, VerificationRoundRecord, OracleStatus, ProtocolActionState


def build_default_validators() -> List[ValidatorNodeClient]:
    """Builds a multi-operator, multi-lane validator set."""
    return [
        ValidatorNodeClient("operator_alpha", "0x1111111111111111111111111111111111111111", LaneType.LANE_1_KALMAN),
        ValidatorNodeClient("operator_beta", "0x2222222222222222222222222222222222222222", LaneType.LANE_1_KALMAN),
        ValidatorNodeClient("operator_gamma", "0x3333333333333333333333333333333333333333", LaneType.LANE_2_HUBER),
        ValidatorNodeClient("operator_delta", "0x4444444444444444444444444444444444444444", LaneType.LANE_2_HUBER),
        ValidatorNodeClient("operator_epsilon", "0x5555555555555555555555555555555555555555", LaneType.LANE_3_JSD),
        ValidatorNodeClient("operator_zeta", "0x6666666666666666666666666666666666666666", LaneType.LANE_4_OU),
        ValidatorNodeClient("operator_eta", "0x7777777777777777777777777777777777777777", LaneType.LANE_5_CUSUM),
    ]


def run_scenario_a() -> VerificationRoundRecord:
    """Scenario A: Normal Operation (HEALTHY_CONSENSUS)"""
    print("\n" + "="*75)
    print("SCENARIO A: Normal Operation (HEALTHY_CONSENSUS)")
    print("="*75)
    
    orchestrator = KeeperOrchestrator()
    for v in build_default_validators():
        orchestrator.register_validator(v)
        
    quotes = [100.0 + np.random.normal(0, 0.05) for _ in range(50)]
    record = orchestrator.orchestrate_round(
        asset_id="RWA_USD_01",
        p_osm_price=100.0,
        market_quotes=quotes,
        p_market_price=100.05,
        anchor_price=100.0,
    )
    
    _print_record(record)
    return record


def run_scenario_b() -> VerificationRoundRecord:
    """Scenario B: Flash Crash Detection (EVIDENCE_OF_ABNORMAL_DEVIATION)"""
    print("\n" + "="*75)
    print("SCENARIO B: Flash Crash Detection (P_OSM stale @ $100, Market @ $93)")
    print("="*75)
    
    orchestrator = KeeperOrchestrator()
    for v in build_default_validators():
        orchestrator.register_validator(v)
        
    quotes = [93.0 + np.random.normal(0, 0.1) for _ in range(50)]
    record = orchestrator.orchestrate_round(
        asset_id="RWA_USD_01",
        p_osm_price=100.0,  # Stale upstream OSM
        market_quotes=quotes,
        p_market_price=93.50,
        anchor_price=100.0,
    )
    
    _print_record(record)
    return record


def run_scenario_c() -> VerificationRoundRecord:
    """Scenario C: Poisoned Validator Isolation via Within-Lane Median"""
    print("\n" + "="*75)
    print("SCENARIO C: Poisoned Validator Isolation (Malicious Quote Suppressed)")
    print("="*75)
    
    orchestrator = KeeperOrchestrator()
    
    # 3 Kalman validators: 2 honest, 1 rogue
    v_k1 = ValidatorNodeClient("op_alpha", "0x1111111111111111111111111111111111111111", LaneType.LANE_1_KALMAN)
    v_k2 = ValidatorNodeClient("op_beta", "0x2222222222222222222222222222222222222222", LaneType.LANE_1_KALMAN)
    v_k_rogue = ValidatorNodeClient("op_rogue", "0x9999999999999999999999999999999999999999", LaneType.LANE_1_KALMAN)
    
    # Override rogue execution to inject $500.0
    orig_exec = v_k_rogue.execute_methodology
    def rogue_exec(**kwargs):
        res = orig_exec(**kwargs)
        res["price"] = 500.0
        res["price_wad"] = int(500.0 * 1e18)
        return res
    v_k_rogue.execute_methodology = rogue_exec
    
    orchestrator.register_validator(v_k1)
    orchestrator.register_validator(v_k2)
    orchestrator.register_validator(v_k_rogue)
    orchestrator.register_validator(ValidatorNodeClient("op_gamma", "0x3333333333333333333333333333333333333333", LaneType.LANE_2_HUBER))
    orchestrator.register_validator(ValidatorNodeClient("op_delta", "0x4444444444444444444444444444444444444444", LaneType.LANE_2_HUBER))
    orchestrator.register_validator(ValidatorNodeClient("op_epsilon", "0x5555555555555555555555555555555555555555", LaneType.LANE_3_JSD))
    orchestrator.register_validator(ValidatorNodeClient("op_zeta", "0x6666666666666666666666666666666666666666", LaneType.LANE_4_OU))
    
    quotes = [100.0 + np.random.normal(0, 0.05) for _ in range(50)]
    record = orchestrator.orchestrate_round(
        asset_id="RWA_USD_01",
        p_osm_price=100.0,
        market_quotes=quotes,
        p_market_price=100.0,
        anchor_price=100.0,
    )
    
    _print_record(record)
    return record


def run_scenario_d() -> VerificationRoundRecord:
    """Scenario D: Market Observer Dislocation (P_DEC ~ $100 != P_MARKET = $70)"""
    print("\n" + "="*75)
    print("SCENARIO D: Market Observer Dislocation (P_DEC != P_MARKET)")
    print("="*75)
    
    orchestrator = KeeperOrchestrator()
    for v in build_default_validators():
        orchestrator.register_validator(v)
        
    quotes = [100.0 + np.random.normal(0, 0.05) for _ in range(50)]
    record = orchestrator.orchestrate_round(
        asset_id="RWA_USD_01",
        p_osm_price=100.0,
        market_quotes=quotes,
        p_market_price=70.0,  # Dislocated market attestor
        anchor_price=100.0,
    )
    
    _print_record(record)
    return record


def run_scenario_e() -> VerificationRoundRecord:
    """Scenario E: Upstream OSM Read Failure"""
    print("\n" + "="*75)
    print("SCENARIO E: Upstream OSM Read Failure -> Failsafe State")
    print("="*75)
    
    orchestrator = KeeperOrchestrator()
    for v in build_default_validators():
        orchestrator.register_validator(v)
        
    quotes = [100.0 + np.random.normal(0, 0.05) for _ in range(50)]
    record = orchestrator.orchestrate_round(
        asset_id="RWA_USD_01",
        p_osm_price=0.0,
        market_quotes=quotes,
        p_market_price=100.0,
        anchor_price=100.0,
        osm_failure=True,
    )
    
    _print_record(record)
    return record


def _print_record(r: VerificationRoundRecord):
    print(f"Round ID:              {r.round_id}")
    print(f"Asset:                 {r.asset_id}")
    print(f"P_OSM:                 ${r.p_osm:.4f}")
    print(f"P_DEC:                 ${r.p_dec:.4f}")
    print(f"P_MARKET:              ${r.p_market:.4f}")
    print(f"P_FINAL:               ${r.p_final:.4f}")
    print(f"Oracle Status:         {r.oracle_status.name}")
    print(f"Protocol State:        {r.protocol_state.name}")
    print(f"Reveals Count:         {r.reveals_count} ({r.distinct_operators} distinct operators, {r.distinct_lanes} lanes)")
    print(f"Deviations (BPS):      OSM-MKT: {r.deviations_bps['osm_mkt']} | DEC-MKT: {r.deviations_bps['dec_mkt']} | OSM-DEC: {r.deviations_bps['osm_dec']}")
    print("Execution Log:")
    for entry in r.execution_log[-4:]:
        print(f"  {entry}")


def run_scenario_by_id(scenario_id: str) -> VerificationRoundRecord:
    scenarios = {
        "A": run_scenario_a,
        "B": run_scenario_b,
        "C": run_scenario_c,
        "D": run_scenario_d,
        "E": run_scenario_e,
    }
    key = scenario_id.upper().replace("SCENARIO_", "").strip()
    if key not in scenarios:
        raise ValueError(f"Unknown scenario ID: {scenario_id}. Choose from A, B, C, D, E.")
    return scenarios[key]()


def run_all_scenarios() -> Dict[str, VerificationRoundRecord]:
    print("\n" + "#"*75)
    print("AEGIS PHASE 4C: END-TO-END VERIFICATION SUITE")
    print("#"*75)
    
    results = {
        "Scenario_A_Normal": run_scenario_a(),
        "Scenario_B_FlashCrash": run_scenario_b(),
        "Scenario_C_PoisonedValidator": run_scenario_c(),
        "Scenario_D_MarketDislocation": run_scenario_d(),
        "Scenario_E_OSMFailure": run_scenario_e(),
    }
    
    print("\n" + "="*75)
    print("ALL 5 SCENARIOS COMPLETED SUCCESSFULLY")
    print("="*75)
    return results


if __name__ == "__main__":
    run_all_scenarios()
