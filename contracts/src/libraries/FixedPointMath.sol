// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title FixedPointMath
/// @notice Arithmetic operations for 18-decimal fixed-point numbers (WAD) and Basis Points (BPS).
/// @dev Internal AEGIS price representation is standard 18-decimal WAD (1 WAD = 1e18).
library FixedPointMath {
    uint256 internal constant WAD = 1e18;
    uint256 internal constant BPS_DIVISOR = 10000;

    error DivisionByZero();
    error ZeroDenominator();

    /// @notice Multiplies two WAD numbers, rounding down
    function wadMul(uint256 x, uint256 y) internal pure returns (uint256) {
        if (x == 0 || y == 0) return 0;
        return (x * y) / WAD;
    }

    /// @notice Divides two WAD numbers, rounding down
    function wadDiv(uint256 x, uint256 y) internal pure returns (uint256) {
        if (y == 0) revert DivisionByZero();
        return (x * WAD) / y;
    }

    /// @notice Returns the absolute difference between two numbers
    function absDiff(uint256 a, uint256 b) internal pure returns (uint256) {
        return a >= b ? a - b : b - a;
    }

    /// @notice Computes relative deviation |a - b| / b in basis points (1 BPS = 0.01% = 0.0001)
    /// @param a Test value
    /// @param b Reference baseline value (must be non-zero)
    /// @return devBps Relative deviation expressed in integer basis points
    function relativeDeviationBps(uint256 a, uint256 b) internal pure returns (uint256 devBps) {
        if (b == 0) revert ZeroDenominator();
        uint256 diff = absDiff(a, b);
        return (diff * BPS_DIVISOR) / b;
    }

    /// @notice Converts a WAD fraction (where 1e18 = 100%) to Basis Points (10000 = 100%)
    function wadToBps(uint256 wadValue) internal pure returns (uint256) {
        return (wadValue * BPS_DIVISOR) / WAD;
    }

    /// @notice Converts Basis Points (10000 = 100%) to a WAD value (1e18 = 100%)
    function bpsToWad(uint256 bps) internal pure returns (uint256) {
        return (bps * WAD) / BPS_DIVISOR;
    }

    /// @notice Multiplies an amount by a basis point factor: (amount * bps) / 10000
    function mulBps(uint256 amount, uint256 bps) internal pure returns (uint256) {
        return (amount * bps) / BPS_DIVISOR;
    }
}
