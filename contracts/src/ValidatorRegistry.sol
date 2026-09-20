// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

uint8 constant LANE_1_KALMAN = 1;
uint8 constant LANE_2_HUBER = 2;
uint8 constant LANE_3_JSD = 3;
uint8 constant LANE_4_OU = 4;
uint8 constant LANE_5_CUSUM = 5;

/// @title ValidatorRegistry
/// @notice Manages validator operator identities, methodology lane assignments, and operational status.
/// @dev Explicitly decouples organizational operator identities (operatorId) from Ethereum wallet addresses:
/// multiple signing wallets may be authorized under the same operatorId, but quorum and lane aggregation
/// treat the operatorId as the canonical unit of organizational identity. Address diversity is not equivalent
/// to organizational/operator independence.
contract ValidatorRegistry is Ownable {
    uint8 public constant CANONICAL_LANE_1_KALMAN = LANE_1_KALMAN;
    uint8 public constant CANONICAL_LANE_2_HUBER = LANE_2_HUBER;
    uint8 public constant CANONICAL_LANE_3_JSD = LANE_3_JSD;
    uint8 public constant CANONICAL_LANE_4_OU = LANE_4_OU;
    uint8 public constant CANONICAL_LANE_5_CUSUM = LANE_5_CUSUM;

    enum LaneRole {
        UNASSIGNED,
        PRICE_ESTIMATOR,
        DIAGNOSTIC
    }

    struct ValidatorRecord {
        bytes32 operatorId;    // Organizational / legal / staking identity
        address operator;      // Authorized signing address
        uint8 laneId;          // Methodology lane (1 to 5)
        bool isActive;         // Active operational status
        bytes32 metadataHash;  // Institutional provenance metadata
        uint64 registeredAt;   // Registration block timestamp
    }

    mapping(address => ValidatorRecord) private _validators;
    mapping(bytes32 => address[]) private _operatorAddresses;
    mapping(uint8 => address[]) private _laneOperators;

    event ValidatorRegistered(
        bytes32 indexed operatorId,
        address indexed operator,
        uint8 indexed laneId,
        bytes32 metadataHash
    );
    event ValidatorStatusUpdated(address indexed operator, bool indexed isActive);
    event ValidatorLaneUpdated(address indexed operator, uint8 indexed previousLane, uint8 indexed newLane);
    event ValidatorMetadataUpdated(address indexed operator, bytes32 indexed metadataHash);

    error InvalidOperatorId();
    error InvalidOperatorAddress();
    error InvalidLaneId(uint8 laneId);
    error ValidatorAlreadyRegistered(address operator);
    error ValidatorNotRegistered(address operator);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Registers a new validator signing address under an organizational operator ID and methodology lane
    /// @param operatorId Unique governance/institutional operator identity
    /// @param operator The Ethereum address of the validator signing node
    /// @param laneId The canonical methodology lane ID (1 to 5)
    /// @param metadataHash Cryptographic hash of validator operational metadata / node info
    function registerValidator(
        bytes32 operatorId,
        address operator,
        uint8 laneId,
        bytes32 metadataHash
    ) external onlyOwner {
        if (operatorId == bytes32(0)) revert InvalidOperatorId();
        if (operator == address(0)) revert InvalidOperatorAddress();
        if (laneId < 1 || laneId > 5) revert InvalidLaneId(laneId);
        if (_validators[operator].operator != address(0)) revert ValidatorAlreadyRegistered(operator);

        _validators[operator] = ValidatorRecord({
            operatorId: operatorId,
            operator: operator,
            laneId: laneId,
            isActive: true,
            metadataHash: metadataHash,
            registeredAt: uint64(block.timestamp)
        });

        _operatorAddresses[operatorId].push(operator);
        _laneOperators[laneId].push(operator);

        emit ValidatorRegistered(operatorId, operator, laneId, metadataHash);
    }

    /// @notice Activates or deactivates a validator operator
    function setValidatorStatus(address operator, bool isActive) external onlyOwner {
        if (_validators[operator].operator == address(0)) revert ValidatorNotRegistered(operator);
        _validators[operator].isActive = isActive;
        emit ValidatorStatusUpdated(operator, isActive);
    }

    /// @notice Updates the methodology lane assignment for a registered validator address
    function setValidatorLane(address operator, uint8 newLaneId) external onlyOwner {
        if (_validators[operator].operator == address(0)) revert ValidatorNotRegistered(operator);
        if (newLaneId < 1 || newLaneId > 5) revert InvalidLaneId(newLaneId);

        uint8 previousLane = _validators[operator].laneId;
        _validators[operator].laneId = newLaneId;
        _laneOperators[newLaneId].push(operator);

        emit ValidatorLaneUpdated(operator, previousLane, newLaneId);
    }

    /// @notice Updates validator operational metadata hash
    function updateMetadataHash(address operator, bytes32 metadataHash) external {
        if (msg.sender != owner() && msg.sender != operator) revert OwnableUnauthorizedAccount(msg.sender);
        if (_validators[operator].operator == address(0)) revert ValidatorNotRegistered(operator);
        _validators[operator].metadataHash = metadataHash;
        emit ValidatorMetadataUpdated(operator, metadataHash);
    }

    /// @notice Returns full validator record
    function getValidator(address operator) external view returns (ValidatorRecord memory) {
        return _validators[operator];
    }

    /// @notice Returns the organizational operator ID for a validator address
    function getValidatorOperatorId(address operator) external view returns (bytes32) {
        return _validators[operator].operatorId;
    }

    /// @notice Checks if an operator address is currently active
    function isValidatorActive(address operator) external view returns (bool) {
        return _validators[operator].isActive;
    }

    /// @notice Returns the methodology lane of a validator operator
    function getValidatorLane(address operator) external view returns (uint8) {
        return _validators[operator].laneId;
    }

    /// @notice Returns all signing addresses registered under an organizational operator ID
    function getOperatorAddresses(bytes32 operatorId) external view returns (address[] memory) {
        if (operatorId == bytes32(0)) revert InvalidOperatorId();
        return _operatorAddresses[operatorId];
    }

    /// @notice Returns all operators registered under a methodology lane
    function getLaneOperators(uint8 laneId) external view returns (address[] memory) {
        if (laneId < 1 || laneId > 5) revert InvalidLaneId(laneId);
        return _laneOperators[laneId];
    }

    /// @notice Resolves the role classification for a methodology lane
    function getLaneRole(uint8 laneId) public pure returns (LaneRole) {
        if (laneId == LANE_1_KALMAN || laneId == LANE_2_HUBER) {
            return LaneRole.PRICE_ESTIMATOR;
        } else if (laneId == LANE_3_JSD || laneId == LANE_4_OU || laneId == LANE_5_CUSUM) {
            return LaneRole.DIAGNOSTIC;
        }
        return LaneRole.UNASSIGNED;
    }

    /// @notice Convenience helper checking if a lane is a price estimator
    function isPriceEstimatorLane(uint8 laneId) external pure returns (bool) {
        return (laneId == LANE_1_KALMAN || laneId == LANE_2_HUBER);
    }

    /// @notice Convenience helper checking if a lane is a diagnostic evidence lane
    function isDiagnosticLane(uint8 laneId) external pure returns (bool) {
        return (laneId == LANE_3_JSD || laneId == LANE_4_OU || laneId == LANE_5_CUSUM);
    }
}
