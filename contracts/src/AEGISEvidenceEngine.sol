// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FixedPointMath} from "./libraries/FixedPointMath.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

// Anomaly Bitmask Constants
uint16 constant FLAG_KALMAN_GATED = 1 << 0;               // 0x0001
uint16 constant FLAG_JSD_DIVERGENT = 1 << 1;              // 0x0002
uint16 constant FLAG_OU_JUMP = 1 << 2;                   // 0x0004
uint16 constant FLAG_CUSUM_TRIPPED = 1 << 3;             // 0x0008
uint16 constant FLAG_DEV_OSM_MARKET_HIGH = 1 << 4;       // 0x0010
uint16 constant FLAG_DEV_DEC_MARKET_HIGH = 1 << 5;       // 0x0020
uint16 constant FLAG_DEV_OSM_DEC_HIGH = 1 << 6;          // 0x0040
uint16 constant FLAG_EXTREME_DISLOCATION = 1 << 7;       // 0x0080

/// @title AEGISEvidenceEngine
/// @notice Computes triangular deviations and synthesizes compact evidence bitmasks on-chain.
/// @dev Ingests terminal prices (P_OSM, P_DEC, P_MARKET) and diagnostic consensus flags to produce
/// an immutable EvidenceRecord consumed by the AEGISDecisionEngine.
contract AEGISEvidenceEngine is Ownable {
    using FixedPointMath for uint256;

    uint16 public constant BIT_KALMAN_GATED = FLAG_KALMAN_GATED;
    uint16 public constant BIT_JSD_DIVERGENT = FLAG_JSD_DIVERGENT;
    uint16 public constant BIT_OU_JUMP = FLAG_OU_JUMP;
    uint16 public constant BIT_CUSUM_TRIPPED = FLAG_CUSUM_TRIPPED;
    uint16 public constant BIT_DEV_OSM_MARKET_HIGH = FLAG_DEV_OSM_MARKET_HIGH;
    uint16 public constant BIT_DEV_DEC_MARKET_HIGH = FLAG_DEV_DEC_MARKET_HIGH;
    uint16 public constant BIT_DEV_OSM_DEC_HIGH = FLAG_DEV_OSM_DEC_HIGH;
    uint16 public constant BIT_EXTREME_DISLOCATION = FLAG_EXTREME_DISLOCATION;

    struct DiagnosticFlags {
        bool kalmanGated;
        bool jsdDivergent;
        bool ouJumpCandidate;
        bool cusumTripped;
        bool ouNotApplicable;
    }

    struct EvidenceRecord {
        uint256 devOsmMarketBps;   // |P_OSM - P_MARKET| / P_MARKET in BPS
        uint256 devDecMarketBps;   // |P_DEC - P_MARKET| / P_MARKET in BPS
        uint256 devOsmDecBps;      // |P_OSM - P_DEC| / P_DEC in BPS
        uint16 anomalyBitmask;     // Bitwise flags combining diagnostics & deviations
        uint8 anomalyCount;        // Active diagnostic count
        bool hasHighDislocation;   // True if any deviation >= warnThresholdBps
        bool hasExtremeDislocation;// True if any deviation >= extremeThresholdBps
    }

    // Configurable thresholds in basis points (1 BPS = 0.01%)
    uint256 public warnThresholdBps = 150;     // 1.50%
    uint256 public criticalThresholdBps = 500; // 5.00%
    uint256 public extremeThresholdBps = 1000; // 10.00%

    event EvidenceThresholdsUpdated(uint256 warnBps, uint256 criticalBps, uint256 extremeBps);
    event EvidenceEvaluated(
        bytes32 indexed assetId,
        uint256 indexed roundId,
        uint256 devOsmMarketBps,
        uint256 devDecMarketBps,
        uint256 devOsmDecBps,
        uint16 anomalyBitmask
    );

    error ZeroPrice(string priceSource);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Updates threshold parameters
    function setThresholds(
        uint256 newWarnBps,
        uint256 newCriticalBps,
        uint256 newExtremeBps
    ) external onlyOwner {
        warnThresholdBps = newWarnBps;
        criticalThresholdBps = newCriticalBps;
        extremeThresholdBps = newExtremeBps;
        emit EvidenceThresholdsUpdated(newWarnBps, newCriticalBps, newExtremeBps);
    }

    /// @notice Evaluates triangular deviations and packs evidence into an EvidenceRecord.
    /// @param assetId Asset identifier
    /// @param roundId Verification round ID
    /// @param pOsm Price from delayed OSM
    /// @param pDec Price from decentralized validator aggregation
    /// @param pMarket Price from terminal market attestation
    /// @param diag Diagnostic consensus flags from validators
    /// @return record The complete structured evidence record
    function evaluateEvidence(
        bytes32 assetId,
        uint256 roundId,
        uint256 pOsm,
        uint256 pDec,
        uint256 pMarket,
        DiagnosticFlags calldata diag
    ) external returns (EvidenceRecord memory record) {
        if (pOsm == 0) revert ZeroPrice("P_OSM");
        if (pDec == 0) revert ZeroPrice("P_DEC");
        if (pMarket == 0) revert ZeroPrice("P_MARKET");

        uint256 devOsmMarket = FixedPointMath.relativeDeviationBps(pOsm, pMarket);
        uint256 devDecMarket = FixedPointMath.relativeDeviationBps(pDec, pMarket);
        uint256 devOsmDec = FixedPointMath.relativeDeviationBps(pOsm, pDec);

        uint16 bitmask = 0;
        uint8 anomalies = 0;

        if (diag.kalmanGated) {
            bitmask |= FLAG_KALMAN_GATED;
            anomalies++;
        }
        if (diag.jsdDivergent) {
            bitmask |= FLAG_JSD_DIVERGENT;
            anomalies++;
        }
        if (diag.ouJumpCandidate && !diag.ouNotApplicable) {
            bitmask |= FLAG_OU_JUMP;
            anomalies++;
        }
        if (diag.cusumTripped) {
            bitmask |= FLAG_CUSUM_TRIPPED;
            anomalies++;
        }

        if (devOsmMarket >= warnThresholdBps) {
            bitmask |= FLAG_DEV_OSM_MARKET_HIGH;
        }
        if (devDecMarket >= warnThresholdBps) {
            bitmask |= FLAG_DEV_DEC_MARKET_HIGH;
        }
        if (devOsmDec >= warnThresholdBps) {
            bitmask |= FLAG_DEV_OSM_DEC_HIGH;
        }

        bool highDislocation = (devOsmMarket >= warnThresholdBps ||
            devDecMarket >= warnThresholdBps ||
            devOsmDec >= warnThresholdBps);

        bool extremeDislocation = (devOsmMarket >= extremeThresholdBps ||
            devDecMarket >= extremeThresholdBps ||
            devOsmDec >= extremeThresholdBps);

        if (extremeDislocation) {
            bitmask |= FLAG_EXTREME_DISLOCATION;
        }

        record = EvidenceRecord({
            devOsmMarketBps: devOsmMarket,
            devDecMarketBps: devDecMarket,
            devOsmDecBps: devOsmDec,
            anomalyBitmask: bitmask,
            anomalyCount: anomalies,
            hasHighDislocation: highDislocation,
            hasExtremeDislocation: extremeDislocation
        });

        emit EvidenceEvaluated(
            assetId,
            roundId,
            devOsmMarket,
            devDecMarket,
            devOsmDec,
            bitmask
        );
    }
}
