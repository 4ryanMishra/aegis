// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {IPyth, PythStructs} from "../mocks/MockOracleFeeds.sol";

/// @title PythAdapter
/// @notice Standardized adapter reading from Pyth Network price feeds with native confidence interval support.
contract PythAdapter is IOracleAdapter {
    IPyth public immutable pyth;
    bytes32 public immutable feedId;
    uint256 public constant WAD = 1e18;
    uint256 public constant MAX_STALENESS = 3600;

    constructor(address _pyth, bytes32 _feedId) {
        require(_pyth != address(0), "Invalid pyth address");
        pyth = IPyth(_pyth);
        feedId = _feedId;
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try pyth.getPriceUnsafe(feedId) returns (PythStructs.Price memory pythPrice) {
            if (pythPrice.price <= 0 || pythPrice.publishTime == 0 || pythPrice.publishTime > block.timestamp) {
                return OracleObservation({
                    price: 0,
                    updatedAt: pythPrice.publishTime,
                    confidence: 0,
                    hasConfidence: true,
                    valid: false,
                    sourceId: "Pyth"
                });
            }

            uint256 normalizedPrice;
            uint256 normalizedConfidence;
            int32 expo = pythPrice.expo;

            // Normalize price to 18 decimals WAD
            if (expo < 0) {
                uint32 absExpo = uint32(-expo);
                if (absExpo <= 18) {
                    normalizedPrice = uint256(int256(pythPrice.price)) * (10 ** (18 - absExpo));
                    normalizedConfidence = uint256(pythPrice.conf) * (10 ** (18 - absExpo));
                } else {
                    normalizedPrice = uint256(int256(pythPrice.price)) / (10 ** (absExpo - 18));
                    normalizedConfidence = uint256(pythPrice.conf) / (10 ** (absExpo - 18));
                }
            } else {
                normalizedPrice = uint256(int256(pythPrice.price)) * (10 ** (18 + uint32(expo)));
                normalizedConfidence = uint256(pythPrice.conf) * (10 ** (18 + uint32(expo)));
            }

            bool isFresh = (block.timestamp - pythPrice.publishTime) <= MAX_STALENESS;

            return OracleObservation({
                price: normalizedPrice,
                updatedAt: pythPrice.publishTime,
                confidence: normalizedConfidence,
                hasConfidence: true,
                valid: isFresh,
                sourceId: "Pyth"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: true,
                valid: false,
                sourceId: "Pyth"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "Pyth";
    }
}
