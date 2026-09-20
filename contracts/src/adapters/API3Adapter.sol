// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {IAPI3Reader} from "../mocks/MockOracleFeeds.sol";

/// @title API3Adapter
/// @notice Standardized adapter reading from API3 dAPI reader contracts.
contract API3Adapter is IOracleAdapter {
    IAPI3Reader public immutable api3Reader;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600;

    constructor(address _api3Reader) {
        require(_api3Reader != address(0), "Invalid api3 reader address");
        api3Reader = IAPI3Reader(_api3Reader);
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try api3Reader.read() returns (int224 value, uint32 timestamp) {
            if (value <= 0 || timestamp == 0 || timestamp > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: uint256(timestamp),
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "API3"
                });
            }

            bool isFresh = (block.timestamp - uint256(timestamp)) <= MAX_STALENESS;

            return OracleObservation({
                price: uint256(int256(value)), // API3 dAPI standard is 18 decimals WAD
                updatedAt: uint256(timestamp),
                confidence: 0,
                hasConfidence: false,
                valid: isFresh,
                sourceId: "API3"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "API3"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "API3";
    }
}
