// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IOSM
/// @notice Minimal read-only interface for delayed Oracle Security Module (OSM).
/// @dev In Multipli / Maker architectures, the OSM delays upstream spot prices by a fixed delay.
/// AEGIS verification runs concurrently during this delay and reads P_OSM once matured.
/// Note: Production Multipli private contract ABI remains TO_VERIFY; this interface abstracts the read boundary.
interface IOSM {
    /// @notice Read current matured delayed price
    /// @return price Normalized 18-decimal price if available
    /// @return hasPrice True if price is set and valid
    function readPrice() external view returns (uint256 price, bool hasPrice);
}
