"""
Validator Node Client (Phase 4C).
Represents an individual validator operator executing quantitative statistical methodologies
and formatting cryptographic commitments and reveals for the AEGIS Verification Manager.
"""

from enum import IntEnum
import hashlib
import json
import secrets
from typing import Dict, Any, Optional, Tuple, List
import numpy as np


class LaneType(IntEnum):
    LANE_1_KALMAN = 1
    LANE_2_HUBER = 2
    LANE_3_JSD = 3
    LANE_4_OU = 4
    LANE_5_CUSUM = 5


class UncertaintyTypeEnum(IntEnum):
    CI95_HALF_WIDTH = 0
    ABSOLUTE_STD = 1
    EMPIRICAL_DISPERSION = 2
    SOURCE_CONFIDENCE = 3
    OTHER_UNSUPPORTED = 4


def keccak256(data: bytes) -> bytes:
    """Computes Keccak-256 (SHA3-256 compatibility or PyCryptodome / hashlib fallback)."""
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except ImportError:
        # Fallback standard sha256 for environments without pycryptodome in mock mode
        return hashlib.sha256(data).digest()


def to_wad(val: float) -> int:
    """Converts a standard float price to 18-decimal fixed-point integer (WAD)."""
    return int(round(val * 1e18))


class ValidatorNodeClient:
    """
    Simulated or RPC-connected Validator Node Client.
    Executes methodology lanes, formats evidence, and produces cryptographic commitments/reveals.
    """

    def __init__(
        self,
        operator_id: str,
        operator_address: str,
        lane_id: LaneType,
        private_key: Optional[str] = None,
    ):
        self.operator_id_str = operator_id
        self.operator_id = keccak256(operator_id.encode("utf-8"))
        self.operator_address = operator_address
        self.lane_id = lane_id
        self.private_key = private_key or "0x" + secrets.token_hex(32)

    def execute_methodology(
        self,
        market_quotes: List[float],
        anchor_price: float = 100.0,
        is_rwa: bool = True,
        ou_not_applicable: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the statistical methodology for this validator's assigned lane.
        Reuses existing Python quantitative calculations.
        """
        quotes = np.array(market_quotes, dtype=float)
        if len(quotes) == 0:
            quotes = np.array([anchor_price])

        price = 0.0
        uncertainty_val = 0.0
        uncertainty_type = UncertaintyTypeEnum.CI95_HALF_WIDTH
        is_gated = False
        diag = {"jsdDivergent": False, "ouJumpCandidate": False, "cusumTripped": False}

        if self.lane_id == LaneType.LANE_1_KALMAN:
            # 1D Recursive Kalman Filter with Innovation Gating
            # Simple 1D state filter
            x_hat = float(quotes[0])
            P = 1.0
            Q = 0.05
            R = 0.5
            gamma = 6.635  # chi2(1, 0.99)

            for z in quotes:
                # Predict
                P_pred = P + Q
                nu = z - x_hat
                S = P_pred + R
                d2 = (nu ** 2) / S
                if d2 > gamma:
                    is_gated = True
                    # Gated innovation
                    continue
                else:
                    K = P_pred / S
                    x_hat = x_hat + K * nu
                    P = (1.0 - K) * P_pred

            price = x_hat
            std_dev = float(np.sqrt(max(P, 1e-4)))
            # 95% CI half-width = 1.96 * std_dev
            uncertainty_val = 1.96 * std_dev
            uncertainty_type = UncertaintyTypeEnum.CI95_HALF_WIDTH

        elif self.lane_id == LaneType.LANE_2_HUBER:
            # Huber M-Estimation via IRLS (k = 1.345)
            med = float(np.median(quotes))
            mad = float(np.median(np.abs(quotes - med)))
            scale = 1.4826 * max(mad, 1e-4)
            k = 1.345
            mu = med
            for _ in range(10):
                residuals = (quotes - mu) / scale
                weights = np.where(np.abs(residuals) <= k, 1.0, k / np.maximum(np.abs(residuals), 1e-6))
                mu_next = float(np.sum(weights * quotes) / np.sum(weights))
                if abs(mu_next - mu) < 1e-5:
                    break
                mu = mu_next
            price = mu
            std_dev = scale / np.sqrt(len(quotes))
            uncertainty_val = 1.96 * std_dev
            uncertainty_type = UncertaintyTypeEnum.CI95_HALF_WIDTH

        elif self.lane_id == LaneType.LANE_3_JSD:
            # Pairwise JSD diagnostic (price forced to 0 for diagnostic lane)
            price = 0.0
            uncertainty_val = 0.0
            uncertainty_type = UncertaintyTypeEnum.OTHER_UNSUPPORTED
            # Check dispersion variance
            if np.std(quotes) > 0.05 * np.mean(quotes):
                diag["jsdDivergent"] = True

        elif self.lane_id == LaneType.LANE_4_OU:
            # Ornstein-Uhlenbeck RWA Mean-Reversion Residual
            price = 0.0
            uncertainty_val = 0.0
            uncertainty_type = UncertaintyTypeEnum.OTHER_UNSUPPORTED
            if is_rwa and not ou_not_applicable:
                latest = float(quotes[-1])
                spread = np.log(latest) - np.log(anchor_price)
                # If absolute spread exceeds 3.5 sigma (~3.5%)
                if abs(spread) >= 0.035:
                    diag["ouJumpCandidate"] = True

        elif self.lane_id == LaneType.LANE_5_CUSUM:
            # Page CUSUM Sequential Drift
            price = 0.0
            uncertainty_val = 0.0
            uncertainty_type = UncertaintyTypeEnum.OTHER_UNSUPPORTED
            if len(quotes) >= 3:
                diffs = np.diff(quotes)
                sigma = max(float(np.std(quotes)), 1e-4)
                z = diffs / sigma
                s_plus = 0.0
                s_minus = 0.0
                k_cusum = 0.5
                h_thresh = 4.0
                for inc in z:
                    s_plus = max(0.0, s_plus + inc - k_cusum)
                    s_minus = max(0.0, s_minus - inc - k_cusum)
                    if s_plus >= h_thresh or s_minus >= h_thresh:
                        diag["cusumTripped"] = True
                        break

        evidence_payload = {
            "operator_id": self.operator_id_str,
            "lane_id": int(self.lane_id),
            "price": price,
            "uncertainty_value": uncertainty_val,
            "uncertainty_type": int(uncertainty_type),
            "is_gated": is_gated,
            "diagnostic_flags": diag,
        }

        evidence_hash = keccak256(json.dumps(evidence_payload, sort_keys=True).encode("utf-8"))

        return {
            "lane_id": int(self.lane_id),
            "price": price,
            "price_wad": to_wad(price),
            "uncertainty_val": uncertainty_val,
            "uncertainty_wad": to_wad(uncertainty_val),
            "uncertainty_type": uncertainty_type,
            "is_gated": is_gated,
            "diagnostic_payload": diag,
            "evidence_hash": evidence_hash,
            "evidence_json": evidence_payload,
        }

    def generate_commitment(
        self,
        round_id: int,
        chain_id: int,
        manager_address: str,
        methodology_output: Dict[str, Any],
        nonce: Optional[int] = None,
    ) -> Tuple[bytes, int, Dict[str, Any]]:
        """
        Computes the cryptographic commitment hash binding:
        (chainid, manager, roundId, operatorAddress, payloadHash, nonce)
        """
        if nonce is None:
            nonce = secrets.randbits(64)

        out = methodology_output

        # Reconstruct payload hash
        payload_data = (
            self.operator_id
            + bytes([out["lane_id"]])
            + out["price_wad"].to_bytes(32, "big")
            + out["uncertainty_wad"].to_bytes(32, "big")
            + bytes([int(out["uncertainty_type"])])
            + bytes([1 if out["is_gated"] else 0])
            + bytes([1 if out["diagnostic_payload"]["jsdDivergent"] else 0])
            + bytes([1 if out["diagnostic_payload"]["ouJumpCandidate"] else 0])
            + bytes([1 if out["diagnostic_payload"]["cusumTripped"] else 0])
            + out["evidence_hash"]
        )
        payload_hash = keccak256(payload_data)

        # Reconstruct commit hash
        commit_data = (
            chain_id.to_bytes(32, "big")
            + bytes.fromhex(manager_address.replace("0x", "").zfill(40))
            + round_id.to_bytes(32, "big")
            + bytes.fromhex(self.operator_address.replace("0x", "").zfill(40))
            + payload_hash
            + nonce.to_bytes(32, "big")
        )
        commit_hash = keccak256(commit_data)

        reveal_params = {
            "roundId": round_id,
            "laneId": out["lane_id"],
            "price": out["price_wad"],
            "uncertaintyValue": out["uncertainty_wad"],
            "uncertaintyType": int(out["uncertainty_type"]),
            "isGated": out["is_gated"],
            "diagPayload": out["diagnostic_payload"],
            "evidenceHash": "0x" + out["evidence_hash"].hex(),
            "nonce": nonce,
        }

        return commit_hash, nonce, reveal_params
