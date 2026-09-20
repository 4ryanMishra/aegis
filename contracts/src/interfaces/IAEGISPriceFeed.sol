// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAEGISPriceFeed
/// @notice Minimal, canonical protocol-facing interface for AEGIS verified price consumption.
/// @dev Downstream protocols (e.g., Multipli Ledger / lending pools) read verified prices exclusively
/// through getPrice(assetId). No raw validator data, intermediate P_DEC, or OSM queues are exposed.
interface IAEGISPriceFeed {
    enum OracleStatus {
        HEALTHY_CONSENSUS,              // Normal operation, standard risk parameters
        SUSPECTED_INCONSISTENCY,        // OSM/Market divergence; substituted with P_DEC
        EVIDENCE_OF_ABNORMAL_DEVIATION, // Significant divergence; protective haircut applied
        DISPERSED_UNCERTAINTY,          // High validator disagreement; new debt restricted
        HALTED_CIRCUIT_BREAKER          // Emergency halt; minting/borrowing frozen
    }

    /// @notice Canonical protocol price query
    /// @param assetId Unique identifier for the asset (e.g. bytes32("XAU/USD"))
    /// @return price Normalized 18-decimal fixed-point price (WAD)
    /// @return status Health and dispute classification
    /// @return timestamp Block timestamp of round finalization
    function getPrice(bytes32 assetId) external view returns (
        uint256 price,
        OracleStatus status,
        uint256 timestamp
    );
}
