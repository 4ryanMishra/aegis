// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "./interfaces/IOracleAdapter.sol";

/// @title ConsensusEngine
/// @notice Deterministic price-band agreement clustering for on-chain multi-oracle cross-checking.
contract ConsensusEngine {
    struct ConsensusResult {
        uint256 consensusPrice;      // Median price of largest valid cluster (WAD)
        uint256 clusterSize;         // Number of sources in consensus cluster
        uint256 totalEligible;        // Total valid external observations
        uint256 agreementRatioBps;   // (clusterSize * 10000) / totalEligible (e.g. 8571 = 85.71%)
        uint256 clusterMin;          // Minimum price in cluster (WAD)
        uint256 clusterMax;          // Maximum price in cluster (WAD)
        uint256 clusterSpreadBps;    // (clusterMax - clusterMin) * 10000 / consensusPrice
        bool hasStrongConsensus;     // True if clusterSize >= minQuorum and ratio >= minAgreementRatio
    }

    uint256 public constant WAD = 1e18;
    uint256 public constant BPS_DENOMINATOR = 10000;

    // Configurable thresholds
    uint256 public clusterToleranceBps = 50;       // 0.50% max allowable cluster spread
    uint256 public minQuorum = 3;                  // Minimum 3 feeds to form quorum
    uint256 public minAgreementRatioBps = 6000;    // 60% agreement required for strong consensus

    address public owner;

    event ConsensusConfigUpdated(uint256 toleranceBps, uint256 quorum, uint256 minRatioBps);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function updateConfig(uint256 _toleranceBps, uint256 _minQuorum, uint256 _minRatioBps) external onlyOwner {
        require(_toleranceBps > 0 && _toleranceBps <= 1000, "Invalid tolerance");
        require(_minQuorum >= 2, "Quorum too low");
        require(_minRatioBps >= 4000 && _minRatioBps <= 10000, "Invalid ratio");

        clusterToleranceBps = _toleranceBps;
        minQuorum = _minQuorum;
        minAgreementRatioBps = _minRatioBps;

        emit ConsensusConfigUpdated(_toleranceBps, _minQuorum, _minRatioBps);
    }

    /// @notice Computes deterministic consensus cluster and metrics from oracle observations
    function computeConsensus(IOracleAdapter.OracleObservation[] memory observations) public view returns (ConsensusResult memory res) {
        uint256 n = observations.length;
        res.totalEligible = n;

        if (n == 0) {
            return res;
        }

        if (n == 1) {
            res.consensusPrice = observations[0].price;
            res.clusterSize = 1;
            res.agreementRatioBps = BPS_DENOMINATOR;
            res.clusterMin = observations[0].price;
            res.clusterMax = observations[0].price;
            res.clusterSpreadBps = 0;
            res.hasStrongConsensus = (minQuorum <= 1);
            return res;
        }

        // 1. Extract and sort prices in memory
        uint256[] memory sorted = new uint256[](n);
        for (uint256 i = 0; i < n; i++) {
            sorted[i] = observations[i].price;
        }

        // Insertion sort (efficient for small N <= 15)
        for (uint256 i = 1; i < n; i++) {
            uint256 key = sorted[i];
            uint256 j = i;
            while (j > 0 && sorted[j - 1] > key) {
                sorted[j] = sorted[j - 1];
                j--;
            }
            sorted[j] = key;
        }

        // 2. Find the largest valid cluster [bestStart..bestEnd]
        uint256 bestStart = 0;
        uint256 bestEnd = 0;
        uint256 bestSize = 0;
        uint256 bestSpread = type(uint256).max;

        for (uint256 i = 0; i < n; i++) {
            for (uint256 j = i; j < n; j++) {
                uint256 currentSize = j - i + 1;
                uint256 currentMedian = sorted[i + (currentSize - 1) / 2];

                if (currentMedian == 0) continue;

                uint256 spreadBps = ((sorted[j] - sorted[i]) * BPS_DENOMINATOR) / currentMedian;

                if (spreadBps <= clusterToleranceBps) {
                    if (currentSize > bestSize || (currentSize == bestSize && spreadBps < bestSpread)) {
                        bestSize = currentSize;
                        bestStart = i;
                        bestEnd = j;
                        bestSpread = spreadBps;
                    }
                }
            }
        }

        if (bestSize == 0) {
            // Fallback to overall median if no cluster meets tolerance
            uint256 overallMedian = sorted[n / 2];
            res.consensusPrice = overallMedian;
            res.clusterSize = 1;
            res.agreementRatioBps = (1 * BPS_DENOMINATOR) / n;
            res.clusterMin = sorted[0];
            res.clusterMax = sorted[n - 1];
            res.clusterSpreadBps = ((sorted[n - 1] - sorted[0]) * BPS_DENOMINATOR) / overallMedian;
            res.hasStrongConsensus = false;
            return res;
        }

        uint256 clusterMedian = sorted[bestStart + (bestSize - 1) / 2];
        res.consensusPrice = clusterMedian;
        res.clusterSize = bestSize;
        res.agreementRatioBps = (bestSize * BPS_DENOMINATOR) / n;
        res.clusterMin = sorted[bestStart];
        res.clusterMax = sorted[bestEnd];
        res.clusterSpreadBps = bestSpread;
        res.hasStrongConsensus = (bestSize >= minQuorum) && (res.agreementRatioBps >= minAgreementRatioBps);

        return res;
    }
}
