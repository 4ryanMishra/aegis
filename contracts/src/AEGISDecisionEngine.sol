// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEGISPriceFeed} from "./interfaces/IAEGISPriceFeed.sol";
import {AEGISEvidenceEngine} from "./AEGISEvidenceEngine.sol";
import {FixedPointMath} from "./libraries/FixedPointMath.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title AEGISDecisionEngine
/// @notice Evaluates synthesized evidence against a deterministic safety policy to produce P_FINAL.
/// @dev Deterministically selects the authoritative price, risk classification, and protocol action code.
contract AEGISDecisionEngine is Ownable {
    using FixedPointMath for uint256;

    enum ActionCode {
        ACCEPT_CONSENSUS,       // Standard operation, standard LTV
        RESTRICT_LTV,           // Protective haircut applied to collateral
        FREEZE_NEW_BORROWS,     // New borrowing/minting disabled; repayments allowed
        TRIGGER_CIRCUIT_BREAKER // Emergency circuit breaker tripped; operations halted
    }

    struct DecisionPolicy {
        uint256 warnThresholdBps;        // Normal consensus upper bound (e.g. 150 BPS = 1.5%)
        uint256 criticalThresholdBps;    // Haircut threshold (e.g. 500 BPS = 5.0%)
        uint256 extremeDisputeBps;       // Circuit breaker threshold (e.g. 1000 BPS = 10.0%)
        uint256 maxAllowedDispersionBps; // Maximum validator dispersion before uncertainty state (e.g. 150 BPS)
        uint256 protectiveHaircutBps;    // Collateral haircut applied in abnormal states (e.g. 500 BPS = 5%)
    }

    struct DecisionResult {
        uint256 pFinal;
        IAEGISPriceFeed.OracleStatus oracleStatus;
        ActionCode actionCode;
        uint256 effectiveHaircutBps;
    }

    DecisionPolicy public policy;

    event PolicyUpdated(
        uint256 warnThresholdBps,
        uint256 criticalThresholdBps,
        uint256 extremeDisputeBps,
        uint256 maxAllowedDispersionBps,
        uint256 protectiveHaircutBps
    );

    event DecisionExecuted(
        bytes32 indexed assetId,
        uint256 indexed roundId,
        uint256 pFinal,
        IAEGISPriceFeed.OracleStatus status,
        ActionCode actionCode,
        uint256 effectiveHaircutBps
    );

    constructor(address initialOwner) Ownable(initialOwner) {
        policy = DecisionPolicy({
            warnThresholdBps: 150,        // 1.50%
            criticalThresholdBps: 500,    // 5.00%
            extremeDisputeBps: 1000,      // 10.00%
            maxAllowedDispersionBps: 150, // 1.50%
            protectiveHaircutBps: 500     // 5.00% haircut
        });
    }

    /// @notice Updates the risk and threshold policy parameters
    function setPolicy(DecisionPolicy calldata newPolicy) external onlyOwner {
        policy = newPolicy;
        emit PolicyUpdated(
            newPolicy.warnThresholdBps,
            newPolicy.criticalThresholdBps,
            newPolicy.extremeDisputeBps,
            newPolicy.maxAllowedDispersionBps,
            newPolicy.protectiveHaircutBps
        );
    }

    error ZeroPrice();

    /// @notice Executes the deterministic decision policy.
    /// @param assetId Asset identifier
    /// @param roundId Verification round ID
    /// @param pOsm Baseline delayed price from OSM
    /// @param pDec Synthesized decentralized price from validator consensus
    /// @param pMarket Attested terminal market price
    /// @param dispersionBps Relative dispersion between methodology price lanes
    /// @param evidence The structured EvidenceRecord computed by the EvidenceEngine
    /// @return result The authoritative P_FINAL, OracleStatus, and ActionCode
    function executeDecision(
        bytes32 assetId,
        uint256 roundId,
        uint256 pOsm,
        uint256 pDec,
        uint256 pMarket,
        uint256 dispersionBps,
        AEGISEvidenceEngine.EvidenceRecord calldata evidence
    ) external returns (DecisionResult memory result) {
        if (pOsm == 0) revert ZeroPrice();

        // Case 1: Extreme Triangulation Dislocation (Irreconcilable Oracle Dispute)
        // Trigger circuit breaker if independent feeds (P_DEC and P_MARKET) diverge extremely,
        // or if extreme dislocation occurs while P_DEC and P_MARKET fail to agree.
        if (
            evidence.devDecMarketBps >= policy.extremeDisputeBps ||
            (evidence.hasExtremeDislocation && evidence.devDecMarketBps >= policy.warnThresholdBps) ||
            (evidence.devOsmDecBps >= policy.extremeDisputeBps && evidence.devDecMarketBps >= policy.extremeDisputeBps)
        ) {
            result = DecisionResult({
                pFinal: 0,
                oracleStatus: IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER,
                actionCode: ActionCode.TRIGGER_CIRCUIT_BREAKER,
                effectiveHaircutBps: 10000 // 100% restriction
            });
            emit DecisionExecuted(assetId, roundId, 0, result.oracleStatus, result.actionCode, 10000);
            return result;
        }

        // Case 2: Dispersed Uncertainty (High Validator Operator / Lane Disagreement)
        if (dispersionBps >= policy.maxAllowedDispersionBps) {
            // Take conservative minimum between P_DEC and P_MARKET to safeguard collateral
            uint256 conservativePrice = pDec < pMarket ? pDec : pMarket;
            result = DecisionResult({
                pFinal: conservativePrice,
                oracleStatus: IAEGISPriceFeed.OracleStatus.DISPERSED_UNCERTAINTY,
                actionCode: ActionCode.FREEZE_NEW_BORROWS,
                effectiveHaircutBps: policy.protectiveHaircutBps
            });
            emit DecisionExecuted(assetId, roundId, conservativePrice, result.oracleStatus, result.actionCode, policy.protectiveHaircutBps);
            return result;
        }

        // Case 3: Abnormal Deviation / Diagnostic Anomaly Trips
        if (evidence.anomalyCount >= 2 || evidence.devOsmMarketBps >= policy.criticalThresholdBps) {
            // Sub-case 3A: P_DEC and P_MARKET agree closely, but OSM is stale/dislocated
            if (evidence.devDecMarketBps < policy.warnThresholdBps && evidence.devOsmMarketBps >= policy.warnThresholdBps) {
                // Decentralized consensus matches real-time market: substitute OSM with P_DEC, flag suspected inconsistency
                result = DecisionResult({
                    pFinal: pDec,
                    oracleStatus: IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY,
                    actionCode: ActionCode.RESTRICT_LTV,
                    effectiveHaircutBps: policy.protectiveHaircutBps
                });
            } else {
                // Sub-case 3B: Significant cross-system anomaly: apply protective haircut to conservative price
                uint256 basePrice = pDec < pMarket ? pDec : pMarket;
                uint256 haircutPrice = (basePrice * (10000 - policy.protectiveHaircutBps)) / 10000;
                result = DecisionResult({
                    pFinal: haircutPrice,
                    oracleStatus: IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION,
                    actionCode: ActionCode.RESTRICT_LTV,
                    effectiveHaircutBps: policy.protectiveHaircutBps
                });
            }
            emit DecisionExecuted(assetId, roundId, result.pFinal, result.oracleStatus, result.actionCode, result.effectiveHaircutBps);
            return result;
        }

        // Case 4: Moderate OSM Divergence (P_DEC and P_MARKET agree, single mild anomaly)
        if (evidence.devOsmMarketBps >= policy.warnThresholdBps && evidence.devDecMarketBps < policy.warnThresholdBps) {
            result = DecisionResult({
                pFinal: pDec,
                oracleStatus: IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY,
                actionCode: ActionCode.RESTRICT_LTV,
                effectiveHaircutBps: 0
            });
            emit DecisionExecuted(assetId, roundId, pDec, result.oracleStatus, result.actionCode, 0);
            return result;
        }

        // Case 5: Healthy Consensus
        result = DecisionResult({
            pFinal: pDec,
            oracleStatus: IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS,
            actionCode: ActionCode.ACCEPT_CONSENSUS,
            effectiveHaircutBps: 0
        });

        emit DecisionExecuted(assetId, roundId, pDec, result.oracleStatus, result.actionCode, 0);
    }
}
