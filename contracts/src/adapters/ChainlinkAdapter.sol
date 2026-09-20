// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {AggregatorV3Interface} from "../mocks/MockOracleFeeds.sol";

/// @title ChainlinkAdapter
/// @notice Standardized adapter reading from Chainlink AggregatorV3 contracts.
contract ChainlinkAdapter is IOracleAdapter {
    AggregatorV3Interface public immutable aggregator;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600; // 1 hour max allowable staleness

    constructor(address _aggregator) {
        require(_aggregator != address(0), "Invalid aggregator address");
        aggregator = AggregatorV3Interface(_aggregator);
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try aggregator.latestRoundData() returns (
            uint80 /* roundId */,
            int256 answer,
            uint256 /* startedAt */,
            uint256 updatedAt,
            uint80 /* answeredInRound */
        ) {
            if (answer <= 0 || updatedAt == 0 || updatedAt > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: updatedAt,
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "Chainlink"
                });
            }

            uint8 decimals = aggregator.decimals();
            uint256 normalizedPrice;
            if (decimals < 18) {
                normalizedPrice = uint256(answer) * (10 ** (18 - decimals));
            } else if (decimals > 18) {
                normalizedPrice = uint256(answer) / (10 ** (decimals - 18));
            } else {
                normalizedPrice = uint256(answer);
            }

            bool isFresh = (block.timestamp - updatedAt) <= MAX_STALENESS;

            return OracleObservation({
                price: normalizedPrice,
                updatedAt: updatedAt,
                confidence: 0,
                hasConfidence: false,
                valid: isFresh,
                sourceId: "Chainlink"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "Chainlink"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "Chainlink";
    }
}
