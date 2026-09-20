// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {FixedPointMath} from "../../src/libraries/FixedPointMath.sol";

/// @title MockMultipliConsumer
/// @notice Local mock simulating a Multipli lending / debt engine consuming verified AEGIS prices.
/// @dev Demonstrates that downstream protocol contracts interact exclusively with ONE finalized
/// price and OracleStatus via getPrice(assetId), without accessing raw validator data or OSM queues.
contract MockMultipliConsumer {
    using FixedPointMath for uint256;

    IAEGISPriceFeed public immutable aegisPriceFeed;

    uint256 public constant STANDARD_LTV_BPS = 8000;   // 80% LTV under HEALTHY_CONSENSUS
    uint256 public constant RESTRICTED_LTV_BPS = 6000; // 60% LTV under abnormal deviation / warnings

    event BorrowEvaluated(
        bytes32 indexed assetId,
        uint256 collateralAmount,
        uint256 requestedDebt,
        bool isApproved,
        string reason
    );

    constructor(address _aegisPriceFeed) {
        aegisPriceFeed = IAEGISPriceFeed(_aegisPriceFeed);
    }

    /// @notice Evaluates borrowing capacity against verified collateral price
    function evaluateBorrow(
        bytes32 assetId,
        uint256 collateralAmount,
        uint256 requestedDebt
    ) external returns (bool isApproved, string memory reason, uint256 effectivePrice) {
        (uint256 price, IAEGISPriceFeed.OracleStatus status, ) = aegisPriceFeed.getPrice(assetId);
        effectivePrice = price;

        if (status == IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER) {
            emit BorrowEvaluated(assetId, collateralAmount, requestedDebt, false, "CIRCUIT_BREAKER_ACTIVE");
            return (false, "CIRCUIT_BREAKER_ACTIVE", price);
        }

        if (status == IAEGISPriceFeed.OracleStatus.DISPERSED_UNCERTAINTY) {
            emit BorrowEvaluated(assetId, collateralAmount, requestedDebt, false, "NEW_DEBT_FROZEN_HIGH_UNCERTAINTY");
            return (false, "NEW_DEBT_FROZEN_HIGH_UNCERTAINTY", price);
        }

        uint256 maxLtvBps = STANDARD_LTV_BPS;
        if (
            status == IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY ||
            status == IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
        ) {
            maxLtvBps = RESTRICTED_LTV_BPS;
        }

        uint256 collateralValue = (collateralAmount * price) / 1e18;
        uint256 maxBorrowCapacity = (collateralValue * maxLtvBps) / 10000;

        if (requestedDebt <= maxBorrowCapacity) {
            emit BorrowEvaluated(assetId, collateralAmount, requestedDebt, true, "APPROVED");
            return (true, "APPROVED", price);
        } else {
            emit BorrowEvaluated(assetId, collateralAmount, requestedDebt, false, "EXCEEDS_LTV_LIMIT");
            return (false, "EXCEEDS_LTV_LIMIT", price);
        }
    }
}
