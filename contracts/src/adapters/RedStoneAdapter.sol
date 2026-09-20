// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {IRedStoneFeed} from "../mocks/MockOracleFeeds.sol";

/// @title RedStoneAdapter
/// @notice Standardized adapter reading from RedStone data feed contracts.
contract RedStoneAdapter is IOracleAdapter {
    IRedStoneFeed public immutable redstoneFeed;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600;

    constructor(address _redstoneFeed) {
        require(_redstoneFeed != address(0), "Invalid redstone feed address");
        redstoneFeed = IRedStoneFeed(_redstoneFeed);
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try redstoneFeed.getValue() returns (uint256 price, uint256 timestamp) {
            if (price == 0 || timestamp == 0 || timestamp > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: timestamp,
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "RedStone"
                });
            }

            bool isFresh = (block.timestamp - timestamp) <= MAX_STALENESS;

            return OracleObservation({
                price: price, // Normalized 18 decimals WAD
                updatedAt: timestamp,
                confidence: 0,
                hasConfidence: false,
                valid: isFresh,
                sourceId: "RedStone"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "RedStone"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "RedStone";
    }
}
