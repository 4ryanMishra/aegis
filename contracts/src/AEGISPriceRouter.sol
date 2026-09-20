// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEGISPriceFeed} from "./interfaces/IAEGISPriceFeed.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title AEGISPriceRouter
/// @notice Single authoritative price router exposing verified P_FINAL to downstream protocols.
/// @dev Downstream contracts (e.g. Multipli Ledger) query getPrice(assetId).
/// Only the authorized AEGISVerificationManager can write finalized prices.
contract AEGISPriceRouter is IAEGISPriceFeed, Ownable {
    struct PriceRecord {
        uint256 price;                     // 18-decimal WAD
        OracleStatus status;               // Health and dispute classification
        uint256 timestamp;                 // Block timestamp of finalization
        uint256 roundId;                   // Canonical verification round ID
    }

    address public verificationManager;
    uint256 public defaultMaxStaleness = 7200; // 2 hours default maximum price age

    mapping(bytes32 => PriceRecord) private _latestPrices;
    mapping(bytes32 => uint256) public assetMaxStaleness;

    event PriceUpdated(
        bytes32 indexed assetId,
        uint256 indexed roundId,
        uint256 price,
        OracleStatus status,
        uint256 timestamp
    );
    event VerificationManagerUpdated(address indexed newManager);
    event StalenessConfigured(bytes32 indexed assetId, uint256 maxStaleness);

    error UnauthorizedCaller(address caller);
    error NoPriceAvailable(bytes32 assetId);
    error PriceStale(bytes32 assetId, uint256 age, uint256 maxAllowed);
    error InvalidPrice();

    modifier onlyManager() {
        if (msg.sender != verificationManager) revert UnauthorizedCaller(msg.sender);
        _;
    }

    constructor(address initialOwner) Ownable(initialOwner) {}

    error InvalidAddress();

    /// @notice Sets the authorized AEGISVerificationManager
    function setVerificationManager(address newManager) external onlyOwner {
        if (newManager == address(0)) revert InvalidAddress();
        verificationManager = newManager;
        emit VerificationManagerUpdated(newManager);
    }

    /// @notice Configures custom maximum staleness per asset
    function setAssetMaxStaleness(bytes32 assetId, uint256 maxStaleness) external onlyOwner {
        assetMaxStaleness[assetId] = maxStaleness;
        emit StalenessConfigured(assetId, maxStaleness);
    }

    /// @notice Sets default maximum price age
    function setDefaultMaxStaleness(uint256 newDefault) external onlyOwner {
        defaultMaxStaleness = newDefault;
    }

    /// @notice Updates the stored finalized price for an asset upon round completion
    /// @param assetId Asset identifier
    /// @param roundId Canonical verification round ID
    /// @param price The authoritative P_FINAL price
    /// @param status The safety status from the Decision Engine
    function updatePrice(
        bytes32 assetId,
        uint256 roundId,
        uint256 price,
        OracleStatus status
    ) external onlyManager {
        if (price == 0 && status != OracleStatus.HALTED_CIRCUIT_BREAKER) {
            revert InvalidPrice();
        }

        _latestPrices[assetId] = PriceRecord({
            price: price,
            status: status,
            timestamp: block.timestamp,
            roundId: roundId
        });

        emit PriceUpdated(assetId, roundId, price, status, block.timestamp);
    }

    /// @inheritdoc IAEGISPriceFeed
    function getPrice(bytes32 assetId) external view override returns (
        uint256 price,
        OracleStatus status,
        uint256 timestamp
    ) {
        PriceRecord memory record = _latestPrices[assetId];
        if (record.timestamp == 0) revert NoPriceAvailable(assetId);

        uint256 allowedAge = assetMaxStaleness[assetId] > 0
            ? assetMaxStaleness[assetId]
            : defaultMaxStaleness;

        uint256 age = block.timestamp - record.timestamp;
        if (age > allowedAge) {
            revert PriceStale(assetId, age, allowedAge);
        }

        return (record.price, record.status, record.timestamp);
    }

    /// @notice Returns full price record including round ID
    function getPriceRecord(bytes32 assetId) external view returns (PriceRecord memory) {
        return _latestPrices[assetId];
    }
}
