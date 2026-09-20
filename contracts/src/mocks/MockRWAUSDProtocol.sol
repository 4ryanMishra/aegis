// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEGISPriceFeed} from "../interfaces/IAEGISPriceFeed.sol";
import {FixedPointMath} from "../libraries/FixedPointMath.sol";

/// @title MockRWAUSDProtocol
/// @notice Demonstrator downstream lending and collateral protocol consuming verified AEGIS prices.
/// @dev Illustrates the operational impact of P_FINAL and OracleStatus on protocol actions:
/// - NORMAL (HEALTHY_CONSENSUS): Standard 80% LTV, full borrowing and minting capacity.
/// - RESTRICTED (SUSPECTED_INCONSISTENCY / ABNORMAL_DEVIATION / DISPERSED_UNCERTAINTY):
///   Conservative 50% LTV, restricted debt ceiling, protective haircut on collateral valuation.
/// - HALTED (HALTED_CIRCUIT_BREAKER): Protocol completely halted, all new debt and minting frozen.
contract MockRWAUSDProtocol {
    using FixedPointMath for uint256;

    enum ProtocolState {
        NORMAL,
        RESTRICTED,
        HALTED
    }

    struct Position {
        uint256 collateralAmount; // 18-decimal WAD
        uint256 debtAmount;       // 18-decimal WAD
        uint64 lastUpdated;
    }

    IAEGISPriceFeed public immutable aegisPriceFeed;
    bytes32 public immutable assetId;

    uint256 public constant WAD = 1e18;
    uint256 public constant STANDARD_LTV_BPS = 8000;   // 80% LTV under NORMAL
    uint256 public constant RESTRICTED_LTV_BPS = 5000; // 50% LTV under RESTRICTED
    uint256 public constant LIQUIDATION_THRESHOLD_BPS = 8500; // 85% LTV

    mapping(address => Position) public positions;
    uint256 public totalProtocolDebt;
    uint256 public totalProtocolCollateral;

    event CollateralDeposited(address indexed user, uint256 amount);
    event DebtMinted(address indexed user, uint256 amount, uint256 effectivePrice, ProtocolState state);
    event DebtRepaid(address indexed user, uint256 amount);
    event PositionLiquidated(address indexed user, address indexed liquidator, uint256 debtRepaid, uint256 collateralSeized);
    event ProtocolStatusEvaluated(bytes32 indexed assetId, uint256 price, IAEGISPriceFeed.OracleStatus oracleStatus, ProtocolState protocolState);

    error ProtocolHaltedByCircuitBreaker();
    error ExceedsMaxLtvLimit(uint256 requestedDebt, uint256 maxAllowedDebt);
    error PositionNotLiquidatable(uint256 currentLtvBps, uint256 thresholdBps);
    error InsufficientCollateral();
    error ZeroAmount();

    constructor(address _aegisPriceFeed, bytes32 _assetId) {
        aegisPriceFeed = IAEGISPriceFeed(_aegisPriceFeed);
        assetId = _assetId;
    }

    /// @notice Returns current protocol operating state based on authoritative AEGIS price feed status
    function getProtocolState() public view returns (ProtocolState state, uint256 price, IAEGISPriceFeed.OracleStatus oracleStatus, uint256 timestamp) {
        (price, oracleStatus, timestamp) = aegisPriceFeed.getPrice(assetId);

        if (oracleStatus == IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER) {
            return (ProtocolState.HALTED, price, oracleStatus, timestamp);
        } else if (
            oracleStatus == IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY ||
            oracleStatus == IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION ||
            oracleStatus == IAEGISPriceFeed.OracleStatus.DISPERSED_UNCERTAINTY
        ) {
            return (ProtocolState.RESTRICTED, price, oracleStatus, timestamp);
        } else {
            return (ProtocolState.NORMAL, price, oracleStatus, timestamp);
        }
    }

    /// @notice Deposits collateral into user position
    function depositCollateral(uint256 amount) external {
        if (amount == 0) revert ZeroAmount();
        positions[msg.sender].collateralAmount += amount;
        positions[msg.sender].lastUpdated = uint64(block.timestamp);
        totalProtocolCollateral += amount;
        emit CollateralDeposited(msg.sender, amount);
    }

    /// @notice Mints RWAUSD debt against deposited collateral under active AEGIS price and LTV constraints
    function borrow(uint256 requestedDebt) external returns (bool success, uint256 effectivePrice) {
        if (requestedDebt == 0) revert ZeroAmount();

        (ProtocolState state, uint256 price, IAEGISPriceFeed.OracleStatus status, ) = getProtocolState();
        emit ProtocolStatusEvaluated(assetId, price, status, state);

        if (state == ProtocolState.HALTED) {
            revert ProtocolHaltedByCircuitBreaker();
        }

        uint256 maxLtvBps = (state == ProtocolState.RESTRICTED) ? RESTRICTED_LTV_BPS : STANDARD_LTV_BPS;

        Position storage pos = positions[msg.sender];
        if (pos.collateralAmount == 0) revert InsufficientCollateral();

        uint256 collateralValue = (pos.collateralAmount * price) / WAD;
        uint256 maxBorrowCapacity = (collateralValue * maxLtvBps) / 10000;
        uint256 newTotalDebt = pos.debtAmount + requestedDebt;

        if (newTotalDebt > maxBorrowCapacity) {
            revert ExceedsMaxLtvLimit(newTotalDebt, maxBorrowCapacity);
        }

        pos.debtAmount = newTotalDebt;
        pos.lastUpdated = uint64(block.timestamp);
        totalProtocolDebt += requestedDebt;

        emit DebtMinted(msg.sender, requestedDebt, price, state);
        return (true, price);
    }

    /// @notice Repays outstanding debt
    function repay(uint256 amount) external {
        if (amount == 0) revert ZeroAmount();
        Position storage pos = positions[msg.sender];
        uint256 actualRepay = amount > pos.debtAmount ? pos.debtAmount : amount;
        pos.debtAmount -= actualRepay;
        pos.lastUpdated = uint64(block.timestamp);
        totalProtocolDebt -= actualRepay;
        emit DebtRepaid(msg.sender, actualRepay);
    }

    /// @notice Evaluates borrowing capacity without executing state changes
    function evaluateBorrowCapacity(address user) external view returns (
        uint256 collateralAmount,
        uint256 currentDebt,
        uint256 price,
        ProtocolState state,
        uint256 maxBorrowCapacity,
        uint256 remainingBorrowCapacity
    ) {
        Position memory pos = positions[user];
        collateralAmount = pos.collateralAmount;
        currentDebt = pos.debtAmount;

        IAEGISPriceFeed.OracleStatus status;
        (state, price, status, ) = getProtocolState();

        if (state == ProtocolState.HALTED || price == 0) {
            return (collateralAmount, currentDebt, price, state, 0, 0);
        }

        uint256 maxLtvBps = (state == ProtocolState.RESTRICTED) ? RESTRICTED_LTV_BPS : STANDARD_LTV_BPS;
        uint256 collateralValue = (collateralAmount * price) / WAD;
        maxBorrowCapacity = (collateralValue * maxLtvBps) / 10000;

        remainingBorrowCapacity = maxBorrowCapacity > currentDebt ? (maxBorrowCapacity - currentDebt) : 0;
    }
}
