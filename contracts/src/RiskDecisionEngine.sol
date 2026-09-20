// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ConsensusEngine} from "./ConsensusEngine.sol";
import {IOracleAdapter} from "./interfaces/IOracleAdapter.sol";
import {IAEGISPriceFeed} from "./interfaces/IAEGISPriceFeed.sol";

/// @title RiskDecisionEngine
/// @notice Transparent, deterministic risk policy evaluator mapping cross-oracle agreement into protocol valuation.
contract RiskDecisionEngine {
    enum DecisionState {
        HEALTHY_CONSENSUS,      // Multipli agrees with external consensus
        MULTIPLI_DEVIATION,     // Multipli diverged from consensus; conservative P_FINAL applied
        SOURCE_DEGRADED,        // Some sources stale/offline, quorum maintained
        NO_CONSENSUS,           // No dominant cluster among external sources
        MARKET_CORROBORATED,    // Exception path: external market reference corroborates consensus
        ORACLE_INSTABILITY      // Severe multi-oracle dislocation; circuit breaker halt
    }

    struct DecisionOutput {
        DecisionState state;
        IAEGISPriceFeed.OracleStatus oracleStatus;
        uint256 finalPrice;              // Authoritative protocol valuation (WAD)
        uint256 multipliDeviationBps;    // |P_OSM - P_CONSENSUS| * 10000 / P_CONSENSUS
        bool isConservativeApplied;      // True if min(P_OSM, P_CONSENSUS) was chosen
        string policyRationale;          // Human-readable audit trail
    }

    uint256 public constant WAD = 1e18;
    uint256 public constant BPS_DENOMINATOR = 10000;

    // Configurable Risk Policy Thresholds
    uint256 public normalThresholdBps = 50;       // 0.50% normal tolerance
    uint256 public deviationThresholdBps = 100;   // 1.00% triggers conservative haircut
    uint256 public criticalThresholdBps = 300;    // 3.00% critical divergence

    address public owner;

    event RiskConfigUpdated(uint256 normalBps, uint256 devBps, uint256 critBps);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function updateConfig(uint256 _normalBps, uint256 _devBps, uint256 _critBps) external onlyOwner {
        require(_normalBps < _devBps && _devBps < _critBps, "Invalid threshold ordering");
        normalThresholdBps = _normalBps;
        deviationThresholdBps = _devBps;
        criticalThresholdBps = _critBps;
        emit RiskConfigUpdated(_normalBps, _devBps, _critBps);
    }

    /// @notice Evaluates Multipli OSM against external cross-oracle consensus
    function evaluateDecision(
        ConsensusEngine.ConsensusResult memory consensus,
        IOracleAdapter.OracleObservation memory multipliObs,
        bool hasMultipli,
        uint256 marketRefPrice,
        bool hasMarketRef
    ) public view returns (DecisionOutput memory out) {
        // Case 1: Total lack of consensus among external sources
        if (!consensus.hasStrongConsensus || consensus.consensusPrice == 0) {
            if (hasMarketRef && marketRefPrice > 0 && consensus.consensusPrice > 0) {
                uint256 mktDev = (marketRefPrice > consensus.consensusPrice)
                    ? ((marketRefPrice - consensus.consensusPrice) * BPS_DENOMINATOR) / consensus.consensusPrice
                    : ((consensus.consensusPrice - marketRefPrice) * BPS_DENOMINATOR) / consensus.consensusPrice;

                if (mktDev <= normalThresholdBps) {
                    out.state = DecisionState.MARKET_CORROBORATED;
                    out.oracleStatus = IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY;
                    out.finalPrice = consensus.consensusPrice;
                    out.policyRationale = "No dominant oracle cluster, but terminal market reference corroborates consensus median";
                    return out;
                }
            }

            out.state = DecisionState.ORACLE_INSTABILITY;
            out.oracleStatus = IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER;
            out.finalPrice = 0;
            out.policyRationale = "Oracle ecosystem in bimodal/severe disagreement without resolving reference; emergency halt engaged";
            return out;
        }

        // Case 2: Multipli OSM feed is missing or failed
        if (!hasMultipli || multipliObs.price == 0) {
            out.state = DecisionState.SOURCE_DEGRADED;
            out.oracleStatus = IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY;
            out.finalPrice = consensus.consensusPrice;
            out.policyRationale = "Multipli OSM feed unavailable; routed to authoritative cross-oracle consensus";
            return out;
        }

        // Case 3: Calculate Multipli deviation from cross-oracle consensus
        uint256 devBps;
        if (multipliObs.price > consensus.consensusPrice) {
            devBps = ((multipliObs.price - consensus.consensusPrice) * BPS_DENOMINATOR) / consensus.consensusPrice;
        } else {
            devBps = ((consensus.consensusPrice - multipliObs.price) * BPS_DENOMINATOR) / consensus.consensusPrice;
        }
        out.multipliDeviationBps = devBps;

        // Sub-case A: Normal Convergence (Multipli agrees within 0.5%)
        if (devBps <= normalThresholdBps) {
            out.state = DecisionState.HEALTHY_CONSENSUS;
            out.oracleStatus = IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS;
            out.finalPrice = multipliObs.price;
            out.isConservativeApplied = false;
            out.policyRationale = "Multipli OSM agrees with cross-oracle consensus within normal tolerance (<= 0.50%)";
            return out;
        }

        // Sub-case B: Material Multipli Divergence (e.g. flash crash / delayed OSM)
        out.state = DecisionState.MULTIPLI_DEVIATION;
        out.oracleStatus = devBps >= criticalThresholdBps
            ? IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
            : IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY;

        // Conservative valuation rule: min(P_OSM, P_CONSENSUS)
        if (multipliObs.price <= consensus.consensusPrice) {
            out.finalPrice = multipliObs.price;
        } else {
            out.finalPrice = consensus.consensusPrice;
        }
        out.isConservativeApplied = true;
        out.policyRationale = "Multipli OSM diverged from cross-oracle consensus; conservative valuation min(P_OSM, P_CONSENSUS) enforced to prevent bad debt";

        return out;
    }
}
