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
/// @dev Explicitly decouples operator identity from methodology lanes: multiple independent operators
/// can register and operate within the same methodology lane.
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

    struct ValidatorInfo {
        address operator;
        uint8 laneId;
        bool isActive;
        bytes32 metadataHash;
        uint64 registeredAt;
    }

    mapping(address => ValidatorInfo) private _validators;
    mapping(uint8 => address[]) private _laneOperators;

    event ValidatorRegistered(address indexed operator, uint8 indexed laneId, bytes32 metadataHash);
    event ValidatorStatusUpdated(address indexed operator, bool indexed isActive);
    event ValidatorMetadataUpdated(address indexed operator, bytes32 indexed metadataHash);

    error InvalidOperatorAddress();
    error InvalidLaneId(uint8 laneId);
    error ValidatorAlreadyRegistered(address operator);
    error ValidatorNotRegistered(address operator);

    constructor(address initialOwner) Ownable(initialOwner) {}

    /// @notice Registers a new validator operator under a canonical methodology lane
    /// @param operator The Ethereum address of the validator operator
    /// @param laneId The canonical methodology lane ID (1 to 5)
    /// @param metadataHash Cryptographic hash of validator operational metadata / node info
    function registerValidator(
        address operator,
        uint8 laneId,
        bytes32 metadataHash
    ) external onlyOwner {
        if (operator == address(0)) revert InvalidOperatorAddress();
        if (laneId < 1 || laneId > 5) revert InvalidLaneId(laneId);
        if (_validators[operator].operator != address(0)) revert ValidatorAlreadyRegistered(operator);

        _validators[operator] = ValidatorInfo({
            operator: operator,
            laneId: laneId,
            isActive: true,
            metadataHash: metadataHash,
            registeredAt: uint64(block.timestamp)
        });

        _laneOperators[laneId].push(operator);

        emit ValidatorRegistered(operator, laneId, metadataHash);
    }

    /// @notice Activates or deactivates a validator operator
    function setValidatorStatus(address operator, bool isActive) external onlyOwner {
        if (_validators[operator].operator == address(0)) revert ValidatorNotRegistered(operator);
        _validators[operator].isActive = isActive;
        emit ValidatorStatusUpdated(operator, isActive);
    }

    /// @notice Updates validator operational metadata hash
    function updateMetadataHash(address operator, bytes32 metadataHash) external {
        if (msg.sender != owner() && msg.sender != operator) revert OwnableUnauthorizedAccount(msg.sender);
        if (_validators[operator].operator == address(0)) revert ValidatorNotRegistered(operator);
        _validators[operator].metadataHash = metadataHash;
        emit ValidatorMetadataUpdated(operator, metadataHash);
    }

    /// @notice Returns full validator info
    function getValidator(address operator) external view returns (ValidatorInfo memory) {
        return _validators[operator];
    }

    /// @notice Checks if an operator is currently active
    function isValidatorActive(address operator) external view returns (bool) {
        return _validators[operator].isActive;
    }

    /// @notice Returns the methodology lane of a validator operator
    function getValidatorLane(address operator) external view returns (uint8) {
        return _validators[operator].laneId;
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
