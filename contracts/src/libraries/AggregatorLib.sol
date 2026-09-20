// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FixedPointMath} from "./FixedPointMath.sol";

/// @title AggregatorLib
/// @notice Implements the Two-Tier Hierarchical Multi-Operator Aggregation for AEGIS (P_DEC).
/// @dev Tier 1: Within-lane robust median and AEGIS conservative dispersion heuristic.
/// Tier 2: Cross-lane inverse-variance weighted synthesis.
/// Diagnostic lanes (Lanes 3, 4, 5) are strictly excluded from P_DEC price calculations.
library AggregatorLib {
    using FixedPointMath for uint256;

    uint256 internal constant WAD = 1e18;
    uint256 internal constant BPS_DIVISOR = 10000;

    // Minimum and maximum uncertainty bounds in BPS (relative to price)
    uint256 internal constant MIN_UNCERTAINTY_BPS = 1;     // 0.01%
    uint256 internal constant MAX_UNCERTAINTY_BPS = 1000;  // 10.00%

    enum UncertaintyType {
        ABSOLUTE_STD,          // Direct standard deviation (sigma)
        CI95_HALF_WIDTH,       // 95% Gaussian Confidence Interval half-width (CI_half = 1.96 * sigma)
        EMPIRICAL_DISPERSION,  // Non-parametric spread (MAD or IQR); unsupported for Gaussian variance weighting
        SOURCE_CONFIDENCE,     // Qualitative source confidence score; unsupported for variance weighting
        OTHER_UNSUPPORTED      // Uncalibrated / non-standard representation
    }

    struct OperatorPriceSubmission {
        bytes32 operatorId;              // Canonical organizational operator identity
        address operator;                // Signing wallet address
        uint256 price;                   // 18-decimal WAD price estimate
        uint256 uncertaintyValue;        // Uncertainty metric (half-width or standard deviation in WAD)
        UncertaintyType uncertaintyType; // Explicit uncertainty semantic representation
        bool isGated;                    // Innovation gating status (Lane 1 Kalman)
    }

    struct CanonicalLaneEstimate {
        uint256 price;           // Canonical median price (WAD)
        uint256 sigmaLane;       // AEGIS conservative dispersion heuristic (WAD)
        uint256 operatorCount;   // Count of revealing operators
        bool isGated;            // Canonical consensus gating status
        bool isValid;            // True if >= 1 valid reveal
    }

    struct Tier2AggregationResult {
        uint256 pDec;            // Final P_DEC (WAD)
        uint256 validatorDispersionBps; // Dispersion between lanes in BPS
        uint256 lambdaKalmanBps; // Weight of Kalman in BPS
        bool kalmanGated;        // True if Kalman was excluded by gating
        bool isDegraded;         // True if only one price estimator lane was active
        bool success;            // True if P_DEC was deterministically formed
    }

    error EmptySubmissions();
    error ZeroDenominator();
    error DuplicateOperatorSubmission(bytes32 operatorId);
    error UnsupportedUncertaintySemantics(UncertaintyType uType);
    error MixedUncertaintySemantics();

    /// @notice Computes Tier 1 Within-Lane Operator Consensus for a single price estimator lane.
    /// @dev Enforces:
    /// 1. Exactly one submission per operatorId within the lane.
    /// 2. Supported and uniform uncertainty semantics across all submissions.
    /// 3. Conservative dispersion heuristic combining median uncertainty and price IQR.
    /// @param submissions Array of operator submissions for this lane.
    /// @return estimate Canonical lane estimate (price, sigmaLane, gating status).
    function aggregateLaneTier1(
        OperatorPriceSubmission[] memory submissions
    ) internal pure returns (CanonicalLaneEstimate memory estimate) {
        uint256 n = submissions.length;
        if (n == 0) {
            return CanonicalLaneEstimate({
                price: 0,
                sigmaLane: 0,
                operatorCount: 0,
                isGated: false,
                isValid: false
            });
        }

        // 1. Enforce unique operatorId within the lane (anti-Sybil / over-influence defense)
        for (uint256 i = 0; i < n; i++) {
            bytes32 opId_i = submissions[i].operatorId;
            for (uint256 j = i + 1; j < n; j++) {
                if (opId_i != bytes32(0) && opId_i == submissions[j].operatorId) {
                    revert DuplicateOperatorSubmission(opId_i);
                }
            }
        }

        // 2. Validate uniform, supported uncertainty semantics
        UncertaintyType baselineType = submissions[0].uncertaintyType;
        if (baselineType != UncertaintyType.CI95_HALF_WIDTH && baselineType != UncertaintyType.ABSOLUTE_STD) {
            revert UnsupportedUncertaintySemantics(baselineType);
        }

        for (uint256 i = 1; i < n; i++) {
            if (submissions[i].uncertaintyType != baselineType) {
                revert MixedUncertaintySemantics();
            }
        }

        uint256[] memory prices = new uint256[](n);
        uint256[] memory sigmas = new uint256[](n);
        uint256 gatedCount = 0;

        for (uint256 i = 0; i < n; i++) {
            prices[i] = submissions[i].price;
            if (submissions[i].isGated) {
                gatedCount++;
            }

            // Mathematical standard deviation conversion:
            // For CI95_HALF_WIDTH: CI_half = 1.96 * sigma => sigma = (half_width * 100) / 196
            // For ABSOLUTE_STD: sigma is supplied directly as uncertaintyValue
            uint256 rawSigma;
            if (baselineType == UncertaintyType.CI95_HALF_WIDTH) {
                rawSigma = (submissions[i].uncertaintyValue * 100) / 196;
            } else {
                rawSigma = submissions[i].uncertaintyValue;
            }

            // Clamp sigma relative to price to prevent zero-division or unbounded variance
            uint256 minSigma = (prices[i] * MIN_UNCERTAINTY_BPS) / BPS_DIVISOR;
            uint256 maxSigma = (prices[i] * MAX_UNCERTAINTY_BPS) / BPS_DIVISOR;
            if (minSigma == 0) minSigma = 1e14; // Fallback 1 BPS of $1
            if (maxSigma <= minSigma) maxSigma = minSigma * 1000;

            if (rawSigma < minSigma) {
                sigmas[i] = minSigma;
            } else if (rawSigma > maxSigma) {
                sigmas[i] = maxSigma;
            } else {
                sigmas[i] = rawSigma;
            }
        }

        // Sort arrays to compute medians and IQR
        _sort(prices);
        _sort(sigmas);

        uint256 medianPrice = _medianSorted(prices);
        uint256 medianSigma = _medianSorted(sigmas);
        uint256 iqrPrice = _iqrSorted(prices);

        // AEGIS canonical lane uncertainty / dispersion estimate:
        // sigma_lane = median(sigma_i) + IQR(price_i)
        // NOTE: This is an AEGIS conservative dispersion heuristic, NOT a statistically exact standard deviation.
        uint256 sigmaLane = medianSigma + iqrPrice;

        // Consensus gating: if >= 50% of operators report gated, lane is canonically gated
        bool isGated = (gatedCount * 2 >= n);

        return CanonicalLaneEstimate({
            price: medianPrice,
            sigmaLane: sigmaLane,
            operatorCount: n,
            isGated: isGated,
            isValid: true
        });
    }

    /// @notice Computes Tier 2 Cross-Lane Methodology Synthesis between Kalman and Huber estimates.
    /// @param kalman Canonical Kalman estimate (Lane 1)
    /// @param huber Canonical Huber estimate (Lane 2)
    /// @return result The aggregated P_DEC result and diagnostic metadata
    function synthesizeTier2(
        CanonicalLaneEstimate memory kalman,
        CanonicalLaneEstimate memory huber
    ) internal pure returns (Tier2AggregationResult memory result) {
        // Case 1: Both lanes valid and eligible (neither gated)
        if (kalman.isValid && huber.isValid && !kalman.isGated) {
            // Dispersion between the two methodology estimates
            uint256 dispersionBps = FixedPointMath.relativeDeviationBps(kalman.price, huber.price);

            // Inverse-variance weights:
            // lambda_K = (1/sigma_K^2) / (1/sigma_K^2 + 1/sigma_H^2) = sigma_H^2 / (sigma_K^2 + sigma_H^2)
            // To prevent overflow when squaring 18-decimal numbers: scale by 1e12 before squaring
            uint256 sK = kalman.sigmaLane / 1e12;
            uint256 sH = huber.sigmaLane / 1e12;
            if (sK == 0) sK = 1;
            if (sH == 0) sH = 1;

            uint256 varK = sK * sK;
            uint256 varH = sH * sH;
            uint256 sumVar = varK + varH;

            // lambda_K in BPS = (varH * 10000) / sumVar
            uint256 lambdaKBps = (varH * BPS_DIVISOR) / sumVar;

            // P_DEC = (lambda_K * P_K + (10000 - lambda_K) * P_H) / 10000
            uint256 pDec = (lambdaKBps * kalman.price + (BPS_DIVISOR - lambdaKBps) * huber.price) / BPS_DIVISOR;

            return Tier2AggregationResult({
                pDec: pDec,
                validatorDispersionBps: dispersionBps,
                lambdaKalmanBps: lambdaKBps,
                kalmanGated: false,
                isDegraded: false,
                success: true
            });
        }

        // Case 2: Kalman is canonically innovation-gated -> Huber alone serves as P_DEC
        if (kalman.isValid && kalman.isGated && huber.isValid) {
            return Tier2AggregationResult({
                pDec: huber.price,
                validatorDispersionBps: 0,
                lambdaKalmanBps: 0,
                kalmanGated: true,
                isDegraded: false,
                success: true
            });
        }

        // Case 3: Only Huber is valid (Kalman offline/unrevealed) -> Huber alone serves with degraded warning
        if (!kalman.isValid && huber.isValid) {
            return Tier2AggregationResult({
                pDec: huber.price,
                validatorDispersionBps: 0,
                lambdaKalmanBps: 0,
                kalmanGated: false,
                isDegraded: true,
                success: true
            });
        }

        // Case 4: Only Kalman is valid (Huber offline/unrevealed) and not gated -> Kalman alone serves degraded
        if (kalman.isValid && !huber.isValid && !kalman.isGated) {
            return Tier2AggregationResult({
                pDec: kalman.price,
                validatorDispersionBps: 0,
                lambdaKalmanBps: BPS_DIVISOR,
                kalmanGated: false,
                isDegraded: true,
                success: true
            });
        }

        // Case 5: Neither lane is capable of providing an uncontaminated price estimate
        return Tier2AggregationResult({
            pDec: 0,
            validatorDispersionBps: 0,
            lambdaKalmanBps: 0,
            kalmanGated: kalman.isGated,
            isDegraded: true,
            success: false
        });
    }

    /// @notice Internal insertion sort for small memory arrays
    function _sort(uint256[] memory arr) private pure {
        uint256 len = arr.length;
        for (uint256 i = 1; i < len; i++) {
            uint256 key = arr[i];
            uint256 j = i;
            while (j > 0 && arr[j - 1] > key) {
                arr[j] = arr[j - 1];
                j--;
            }
            arr[j] = key;
        }
    }

    /// @notice Computes median of a sorted array
    function _medianSorted(uint256[] memory sorted) private pure returns (uint256) {
        uint256 n = sorted.length;
        if (n == 0) return 0;
        if (n % 2 == 1) {
            return sorted[n / 2];
        } else {
            return (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
        }
    }

    /// @notice Computes Interquartile Range (IQR) of a sorted array
    function _iqrSorted(uint256[] memory sorted) private pure returns (uint256) {
        uint256 n = sorted.length;
        if (n <= 1) return 0;
        if (n < 4) {
            // For small sample sizes, return range (max - min) as conservative dispersion
            return sorted[n - 1] - sorted[0];
        }
        uint256 halfLen = n / 2;
        uint256[] memory lowerHalf = new uint256[](halfLen);
        uint256[] memory upperHalf = new uint256[](halfLen);

        for (uint256 i = 0; i < halfLen; i++) {
            lowerHalf[i] = sorted[i];
            upperHalf[i] = sorted[n - halfLen + i];
        }

        uint256 q1 = _medianSorted(lowerHalf);
        uint256 q3 = _medianSorted(upperHalf);

        return q3 >= q1 ? q3 - q1 : 0;
    }
}
