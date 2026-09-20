"""
Keeper Orchestrator (Phase 4C).
Orchestrates the entire AEGIS verification lifecycle respecting state machine windows and timing:
T0 (Open Round & Commits) -> Reveals -> Market Attestation -> Finalize -> Protocol Execution.
"""

from dataclasses import dataclass
from enum import IntEnum
import time
from typing import Dict, List, Any, Optional
import numpy as np

from .validator_client import ValidatorNodeClient, LaneType, keccak256


class OracleStatus(IntEnum):
    HEALTHY_CONSENSUS = 0
    SUSPECTED_INCONSISTENCY = 1
    EVIDENCE_OF_ABNORMAL_DEVIATION = 2
    DISPERSED_UNCERTAINTY = 3
    HALTED_CIRCUIT_BREAKER = 4


class ProtocolActionState(IntEnum):
    NORMAL = 0
    RESTRICTED = 1
    HALTED = 2


@dataclass
class VerificationRoundRecord:
    round_id: int
    asset_id: str
    p_osm: float
    p_dec: float
    p_market: float
    p_final: float
    oracle_status: OracleStatus
    protocol_state: ProtocolActionState
    deviations_bps: Dict[str, int]
    diagnostic_flags: Dict[str, bool]
    reveals_count: int
    distinct_operators: int
    distinct_lanes: int
    validator_summaries: List[Dict[str, Any]]
    execution_log: List[str]


class KeeperOrchestrator:
    """
    Coordinates multi-lane validator clients and drives verification rounds.
    Can run in pure deterministic simulation mode or via JSON-RPC.
    """

    def __init__(self, chain_id: int = 31337, manager_address: str = "0x5FbDB2315678afecb367f032d93F642f64180aa3"):
        self.chain_id = chain_id
        self.manager_address = manager_address
        self.validators: List[ValidatorNodeClient] = []
        self.next_round_id = 1

    def register_validator(self, validator: ValidatorNodeClient):
        self.validators.append(validator)

    def orchestrate_round(
        self,
        asset_id: str,
        p_osm_price: float,
        market_quotes: List[float],
        p_market_price: float,
        anchor_price: float = 100.0,
        is_rwa: bool = True,
        ou_not_applicable: bool = False,
        osm_failure: bool = False,
    ) -> VerificationRoundRecord:
        """
        Executes a complete end-to-end verification round.
        """
        round_id = self.next_round_id
        self.next_round_id += 1
        log: List[str] = []

        log.append(f"[T0] Opened Verification Round #{round_id} for {asset_id}. Baseline P_OSM = ${p_osm_price:.2f}")

        # Step 1: Validator Methodology Computation & Commitments
        commitments = []
        reveal_payloads = []
        val_summaries = []
        seen_op_ids = set()
        seen_lanes = set()

        for val in self.validators:
            # Execute Python quantitative methodology
            out = val.execute_methodology(
                market_quotes=market_quotes,
                anchor_price=anchor_price,
                is_rwa=is_rwa,
                ou_not_applicable=ou_not_applicable,
            )

            commit_hash, nonce, reveal_params = val.generate_commitment(
                round_id=round_id,
                chain_id=self.chain_id,
                manager_address=self.manager_address,
                methodology_output=out,
            )

            commitments.append((val, commit_hash))
            reveal_payloads.append((val, reveal_params, out))
            seen_op_ids.add(val.operator_id_str)
            seen_lanes.add(int(val.lane_id))

            val_summaries.append({
                "operator_id": val.operator_id_str,
                "operator_address": val.operator_address,
                "lane_id": int(val.lane_id),
                "price": out["price"],
                "uncertainty": out["uncertainty_val"],
                "is_gated": out["is_gated"],
                "diagnostic_flags": out["diagnostic_payload"],
            })

            log.append(
                f"[Commit Window] Validator {val.operator_id_str} (Lane {val.lane_id.name}) submitted commitment: 0x{commit_hash.hex()[:16]}..."
            )

        # Step 2: Reveal Phase
        log.append(f"[Reveal Window] Opening reveals for {len(reveal_payloads)} submitted validators.")
        price_submissions_lane1 = []
        price_submissions_lane2 = []
        diag_jsd = False
        diag_ou = False
        diag_cusum = False

        for val, rev, out in reveal_payloads:
            log.append(
                f"  - Revealed Lane {val.lane_id}: Price=${out['price']:.2f}, Uncertainty=±${out['uncertainty_val']:.2f}"
            )
            if val.lane_id == LaneType.LANE_1_KALMAN:
                price_submissions_lane1.append((out["price"], max(out["uncertainty_val"] / 1.96, 1e-4)))
            elif val.lane_id == LaneType.LANE_2_HUBER:
                price_submissions_lane2.append((out["price"], max(out["uncertainty_val"] / 1.96, 1e-4)))

            if out["diagnostic_payload"]["jsdDivergent"]:
                diag_jsd = True
            if out["diagnostic_payload"]["ouJumpCandidate"]:
                diag_ou = True
            if out["diagnostic_payload"]["cusumTripped"]:
                diag_cusum = True

        # Step 3: Quorum Evaluation
        total_reveals = len(reveal_payloads)
        distinct_operators = len(seen_op_ids)
        distinct_lanes = len(seen_lanes)
        quorum_met = total_reveals >= 3 and distinct_operators >= 3 and distinct_lanes >= 3

        log.append(
            f"[Quorum] Reveals: {total_reveals}, Distinct Operators: {distinct_operators}, Distinct Lanes: {distinct_lanes} -> Met: {quorum_met}"
        )

        # Step 4: Two-Tier Aggregation to synthesize P_DEC
        p_dec = p_osm_price
        if len(price_submissions_lane1) > 0 and len(price_submissions_lane2) > 0:
            # Tier 1 Within-lane median
            p_k = float(np.median([p for p, _ in price_submissions_lane1]))
            sig_k = float(np.median([s for _, s in price_submissions_lane1]))

            p_h = float(np.median([p for p, _ in price_submissions_lane2]))
            sig_h = float(np.median([s for _, s in price_submissions_lane2]))

            # Tier 2 Cross-lane inverse-variance synthesis
            w_k = 1.0 / (sig_k ** 2)
            w_h = 1.0 / (sig_h ** 2)
            p_dec = (w_k * p_k + w_h * p_h) / (w_k + w_h)
            log.append(f"[Tier 2 Aggregation] P_Kalman = ${p_k:.2f}, P_Huber = ${p_h:.2f} -> P_DEC = ${p_dec:.2f}")
        elif len(price_submissions_lane1) > 0:
            p_dec = float(np.median([p for p, _ in price_submissions_lane1]))
        elif len(price_submissions_lane2) > 0:
            p_dec = float(np.median([p for p, _ in price_submissions_lane2]))

        # Step 5: Market Attestation & Triangular Evidence
        log.append(f"[Market Attestation] Received EIP-712 Attestation: P_MARKET = ${p_market_price:.2f}")

        # Compute deviations in Basis Points
        dev_osm_mkt_bps = int(round(abs(p_osm_price - p_market_price) / max(p_market_price, 1e-4) * 10000))
        dev_dec_mkt_bps = int(round(abs(p_dec - p_market_price) / max(p_market_price, 1e-4) * 10000))
        dev_osm_dec_bps = int(round(abs(p_osm_price - p_dec) / max(p_dec, 1e-4) * 10000))

        log.append(
            f"[Evidence Engine] Triangular Deviations: d(OSM, MKT)={dev_osm_mkt_bps} BPS, d(DEC, MKT)={dev_dec_mkt_bps} BPS, d(OSM, DEC)={dev_osm_dec_bps} BPS"
        )

        # Step 6: Decision Engine Policy Matrix
        oracle_status = OracleStatus.HEALTHY_CONSENSUS
        protocol_state = ProtocolActionState.NORMAL
        p_final = p_dec

        if osm_failure:
            log.append("[Failsafe] Upstream OSM failed/reverted. Fallback to conservative P_DEC.")
            oracle_status = OracleStatus.SUSPECTED_INCONSISTENCY
            protocol_state = ProtocolActionState.RESTRICTED
            p_final = p_dec
        elif dev_osm_dec_bps > 2000 or dev_dec_mkt_bps > 2000:
            # Extreme dislocation (>20%)
            log.append("[Decision Engine] Extreme triangular dislocation detected. Triggering Circuit Breaker.")
            oracle_status = OracleStatus.HALTED_CIRCUIT_BREAKER
            protocol_state = ProtocolActionState.HALTED
            p_final = 0.0
        elif dev_osm_dec_bps > 400 or dev_dec_mkt_bps > 400 or dev_osm_mkt_bps > 400:
            # Abnormal deviation (>4%)
            log.append("[Decision Engine] Material deviation detected. Applying protective haircut and RESTRICTED LTV.")
            oracle_status = OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
            protocol_state = ProtocolActionState.RESTRICTED
            # Conservative lower price among validated feeds
            p_final = min(p_dec, p_market_price)
        else:
            # Healthy Consensus
            log.append(f"[Decision Engine] Feeds in agreement. Authoritative P_FINAL = ${p_final:.2f}")
            oracle_status = OracleStatus.HEALTHY_CONSENSUS
            protocol_state = ProtocolActionState.NORMAL

        # Step 7: Downstream Protocol State Evaluation
        log.append(f"[Mock Protocol] Protocol State: {protocol_state.name} (LTV = 80% if NORMAL, 50% if RESTRICTED, FROZEN if HALTED)")

        return VerificationRoundRecord(
            round_id=round_id,
            asset_id=asset_id,
            p_osm=p_osm_price,
            p_dec=p_dec,
            p_market=p_market_price,
            p_final=p_final,
            oracle_status=oracle_status,
            protocol_state=protocol_state,
            deviations_bps={
                "osm_mkt": dev_osm_mkt_bps,
                "dec_mkt": dev_dec_mkt_bps,
                "osm_dec": dev_osm_dec_bps,
            },
            diagnostic_flags={
                "jsd_divergent": diag_jsd,
                "ou_jump_candidate": diag_ou,
                "cusum_tripped": diag_cusum,
            },
            reveals_count=total_reveals,
            distinct_operators=distinct_operators,
            distinct_lanes=distinct_lanes,
            validator_summaries=val_summaries,
            execution_log=log,
        )
