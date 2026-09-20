// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {IChronicleScribe} from "../mocks/MockOracleFeeds.sol";

/// @title ChronicleAdapter
/// @notice Standardized adapter reading from Chronicle Scribe oracle feeds.
contract ChronicleAdapter is IOracleAdapter {
    IChronicleScribe public immutable scribe;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600;

    constructor(address _scribe) {
        require(_scribe != address(0), "Invalid scribe address");
        scribe = IChronicleScribe(_scribe);
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try scribe.read() returns (uint256 val, uint256 age) {
            if (val == 0 || age > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: 0,
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "Chronicle"
                });
            }

            uint256 updatedAt = block.timestamp >= age ? block.timestamp - age : 0;
            bool isFresh = age <= MAX_STALENESS;

            return OracleObservation({
                price: val, // Chronicle standard is 18 decimals WAD
                updatedAt: updatedAt,
                confidence: 0,
                hasConfidence: false,
                valid: isFresh,
                sourceId: "Chronicle"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "Chronicle"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "Chronicle";
    }
}
