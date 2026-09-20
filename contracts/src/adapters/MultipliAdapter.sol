// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "../interfaces/IOracleAdapter.sol";
import {IOSM} from "../interfaces/IOSM.sol";

/// @title MultipliAdapter
/// @notice Standardized adapter reading from Multipli Oracle Security Module (OSM).
contract MultipliAdapter is IOracleAdapter {
    IOSM public immutable osm;
    uint256 public constant WAD = 1e18;

    constructor(address _osm) {
        require(_osm != address(0), "Invalid OSM address");
        osm = IOSM(_osm);
    }

    function getObservation(bytes32 /* assetId */) external view override returns (OracleObservation memory obs) {
        try osm.readPrice() returns (uint256 price, bool hasPrice) {
            if (!hasPrice || price == 0) {
                return OracleObservation({
                    price: 0,
                    updatedAt: block.timestamp,
                    confidence: 0,
                    hasConfidence: false,
                    valid: false,
                    sourceId: "Multipli"
                });
            }

            return OracleObservation({
                price: price, // 18 decimals WAD
                updatedAt: block.timestamp,
                confidence: 0,
                hasConfidence: false,
                valid: true,
                sourceId: "Multipli"
            });
        } catch {
            return OracleObservation({
                price: 0,
                updatedAt: 0,
                confidence: 0,
                hasConfidence: false,
                valid: false,
                sourceId: "Multipli"
            });
        }
    }

    function getProviderName() external pure override returns (string memory) {
        return "Multipli";
    }
}
