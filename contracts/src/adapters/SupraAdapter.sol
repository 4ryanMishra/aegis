// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {ISupraRouter} from "../mocks/MockOracleFeeds.sol";

/// @title SupraAdapter
/// @notice Standardized adapter reading from Supra DORA oracle routers.
contract SupraAdapter is IOracleAdapter {
    ISupraRouter public immutable supraRouter;
    uint256 public immutable pairId;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600;

    constructor(address _supraRouter, uint256 _pairId) {
        require(_supraRouter != address(0), "Invalid supra router address");
        supraRouter = ISupraRouter(_supraRouter);
        pairId = _pairId;
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try supraRouter.getSvalue(pairId) returns (
            uint256 /* round */,
            int256 price,
            uint256 timestamp,
            uint256 decimals
        ) {
            if (price <= 0 || timestamp == 0 || timestamp > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: timestamp,
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "Supra"
                });
            }

            uint256 normalizedPrice;
            if (decimals < 18) {
                normalizedPrice = uint256(price) * (10 ** (18 - decimals));
            } else if (decimals > 18) {
                normalizedPrice = uint256(price) / (10 ** (decimals - 18));
            } else {
                normalizedPrice = uint256(price);
            }

            bool isFresh = (block.timestamp - timestamp) <= MAX_STALENESS;

            return OracleObservation({
                price: normalizedPrice,
                updatedAt: timestamp,
                confidence: 0,
                hasConfidence: false,
                valid: isFresh,
                sourceId: "Supra"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "Supra"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "Supra";
    }
}
