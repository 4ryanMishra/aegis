// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IAEGISPriceFeed} from "./interfaces/IAEGISPriceFeed.sol";
import {IOracleAdapter} from "./interfaces/IOracleAdapter.sol";
import {OracleRegistry} from "./OracleRegistry.sol";
import {ConsensusEngine} from "./ConsensusEngine.sol";
import {RiskDecisionEngine} from "./RiskDecisionEngine.sol";

/// @title AEGISPriceRouter
/// @notice Central on-chain cross-oracle cross-checking router exposing authoritative verified prices to downstream protocols.
contract AEGISPriceRouter is IAEGISPriceFeed {
    OracleRegistry public registry;
    ConsensusEngine public consensusEngine;
    RiskDecisionEngine public decisionEngine;

    // Backward compatibility and overrides
    address public verificationManager;
    uint256 public constant DEFAULT_MAX_STALENESS = 7200; // 2 hours default
    mapping(bytes32 => uint256) public assetMaxStaleness;
    mapping(bytes32 => uint256) public manualOverridePrice;
    mapping(bytes32 => OracleStatus) public manualOverrideStatus;
    mapping(bytes32 => uint256) public manualOverrideTimestamp;
    mapping(bytes32 => bool) public hasManualOverride;

    // Optional simulated market reference
    uint256 public simulatedMarketRefPrice;
    bool public hasSimulatedMarketRef;

    address public owner;

    event VerifiedPriceEvaluated(
        bytes32 indexed assetId,
        uint256 finalPrice,
        OracleStatus status,
        uint256 consensusPrice,
        uint256 multipliPrice,
        uint256 deviationBps
    );
    event PriceUpdated(bytes32 indexed assetId, uint256 roundId, uint256 price, OracleStatus status, uint256 timestamp);

    error UnauthorizedCaller(address caller);
    error PriceStale(bytes32 assetId, uint256 age, uint256 maxStaleness);
    error NoPriceAvailable(bytes32 assetId);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor(address _owner) {
        owner = _owner != address(0) ? _owner : msg.sender;
    }

    function setRegistry(address _registry) external onlyOwner {
        registry = OracleRegistry(_registry);
    }

    function setConsensusEngine(address _consensusEngine) external onlyOwner {
        consensusEngine = ConsensusEngine(_consensusEngine);
    }

    function setDecisionEngine(address _decisionEngine) external onlyOwner {
        decisionEngine = RiskDecisionEngine(_decisionEngine);
    }

    function setVerificationManager(address _vm) external onlyOwner {
        verificationManager = _vm;
    }

    function setAssetMaxStaleness(bytes32 _assetId, uint256 _maxStaleness) external onlyOwner {
        assetMaxStaleness[_assetId] = _maxStaleness;
    }

    function setSimulatedMarketReference(uint256 _price, bool _active) external onlyOwner {
        simulatedMarketRefPrice = _price;
        hasSimulatedMarketRef = _active;
    }

    function updatePrice(bytes32 assetId, uint256 roundId, uint256 price, OracleStatus status) external {
        if (verificationManager != address(0) && msg.sender != verificationManager && msg.sender != owner) {
            revert UnauthorizedCaller(msg.sender);
        }
        manualOverridePrice[assetId] = price;
        manualOverrideStatus[assetId] = status;
        manualOverrideTimestamp[assetId] = block.timestamp;
        hasManualOverride[assetId] = true;
        emit PriceUpdated(assetId, roundId, price, status, block.timestamp);
    }

    /// @inheritdoc IAEGISPriceFeed
    function getPrice(bytes32 assetId) external view override returns (
        uint256 price,
        OracleStatus status,
        uint256 timestamp
    ) {
        if (address(registry) == address(0)) {
            return _getManualPrice(assetId);
        }

        (
            IOracleAdapter.OracleObservation[] memory obs,
            IOracleAdapter.OracleObservation memory multipliObs,
            bool hasMultipli
        ) = registry.getAllObservations(assetId);

        if (obs.length == 0 && !hasMultipli) {
            return _getManualPrice(assetId);
        }

        ConsensusEngine.ConsensusResult memory consensus = consensusEngine.computeConsensus(obs);

        RiskDecisionEngine.DecisionOutput memory decision = decisionEngine.evaluateDecision(
            consensus,
            multipliObs,
            hasMultipli,
            simulatedMarketRefPrice,
            hasSimulatedMarketRef
        );

        return (decision.finalPrice, decision.oracleStatus, block.timestamp);
    }

    function _getManualPrice(bytes32 assetId) internal view returns (uint256, OracleStatus, uint256) {
        if (!hasManualOverride[assetId]) {
            revert NoPriceAvailable(assetId);
        }
        if (manualOverridePrice[assetId] == 0 && manualOverrideStatus[assetId] != OracleStatus.HALTED_CIRCUIT_BREAKER) {
            revert NoPriceAvailable(assetId);
        }
        uint256 maxStaleness = assetMaxStaleness[assetId] > 0 ? assetMaxStaleness[assetId] : DEFAULT_MAX_STALENESS;
        uint256 age = block.timestamp >= manualOverrideTimestamp[assetId] ? block.timestamp - manualOverrideTimestamp[assetId] : 0;
        if (age > maxStaleness) {
            revert PriceStale(assetId, age, maxStaleness);
        }
        return (manualOverridePrice[assetId], manualOverrideStatus[assetId], manualOverrideTimestamp[assetId]);
    }

    /// @notice Comprehensive audit getter providing full on-chain provenance for UI and transparency panels
    function getDetailedAudit(bytes32 assetId) external view returns (
        IOracleAdapter.OracleObservation[] memory observations,
        IOracleAdapter.OracleObservation memory multipliObs,
        bool hasMultipli,
        ConsensusEngine.ConsensusResult memory consensus,
        RiskDecisionEngine.DecisionOutput memory decision
    ) {
        if (address(registry) != address(0)) {
            (observations, multipliObs, hasMultipli) = registry.getAllObservations(assetId);
            if (address(consensusEngine) != address(0)) {
                consensus = consensusEngine.computeConsensus(observations);
            }
            if (address(decisionEngine) != address(0)) {
                decision = decisionEngine.evaluateDecision(
                    consensus,
                    multipliObs,
                    hasMultipli,
                    simulatedMarketRefPrice,
                    hasSimulatedMarketRef
                );
            }
        }
    }
}
