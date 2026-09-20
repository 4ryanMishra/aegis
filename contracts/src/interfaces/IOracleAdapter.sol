// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IOracleAdapter
/// @notice Standardized interface for reading normalized price observations across external oracle networks.
/// @dev Implemented by individual adapters (Chainlink, Pyth, Chronicle, RedStone, Supra, API3, Multipli).
interface IOracleAdapter {
    struct OracleObservation {
        uint256 price;          // Normalized 18-decimal fixed-point price (WAD)
        uint256 updatedAt;      // Unix timestamp of observation in seconds
        uint256 confidence;     // Spread/confidence bounds if natively provided (in WAD, 0 if none)
        bool hasConfidence;     // True if native confidence is supported by provider (e.g. Pyth)
        bool valid;             // True if observation passed structural checks (non-zero, non-stale)
        string sourceId;        // Source identifier string (e.g. "Chainlink", "Pyth", "Multipli")
    }

    /// @notice Fetches the latest normalized observation for a specified asset
    /// @param assetId Unique identifier for the asset (e.g. bytes32("XAU/USD"))
    /// @return observation Standardized OracleObservation struct
    function getObservation(bytes32 assetId) external view returns (OracleObservation memory observation);

    /// @notice Returns the human-readable provider name
    function getProviderName() external view returns (string memory);
}
