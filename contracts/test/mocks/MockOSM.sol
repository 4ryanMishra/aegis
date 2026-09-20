// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOSM} from "../../src/interfaces/IOSM.sol";

/// @title MockOSM
/// @notice Local mock simulating a delayed Oracle Security Module (OSM) for AEGIS testing.
/// @dev Note: This is a local test mock and does NOT claim to represent private Multipli production bytecode.
contract MockOSM is IOSM {
    uint256 public price;
    bool public hasPrice = true;
    bool public shouldRevert = false;

    error MockOSMReverted();

    constructor(uint256 initialPrice) {
        price = initialPrice;
    }

    function setPrice(uint256 newPrice, bool newHasPrice) external {
        price = newPrice;
        hasPrice = newHasPrice;
    }

    function setShouldRevert(bool revertFlag) external {
        shouldRevert = revertFlag;
    }

    /// @inheritdoc IOSM
    function readPrice() external view override returns (uint256, bool) {
        if (shouldRevert) revert MockOSMReverted();
        return (price, hasPrice);
    }
}
