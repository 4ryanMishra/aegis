// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {
    ValidatorRegistry,
    LANE_1_KALMAN,
    LANE_2_HUBER,
    LANE_3_JSD,
    LANE_4_OU,
    LANE_5_CUSUM
} from "../../src/ValidatorRegistry.sol";

contract ValidatorRegistryTest is Test {
    ValidatorRegistry registry;
    address owner = address(0xAA1);
    bytes32 opId1 = keccak256("OPERATOR_ONE");
    bytes32 opId2 = keccak256("OPERATOR_TWO");
    bytes32 opId3 = keccak256("OPERATOR_THREE");

    address op1 = address(0xB01);
    address op2 = address(0xB02);
    address op3 = address(0xB03);
    address unauthorized = address(0xDEAD);

    function setUp() public {
        vm.prank(owner);
        registry = new ValidatorRegistry(owner);
    }

    function test_RegisterValidator_Success() public {
        bytes32 meta = keccak256("NODE_KALMAN_1");
        vm.prank(owner);
        registry.registerValidator(opId1, op1, LANE_1_KALMAN, meta);

        assertTrue(registry.isValidatorActive(op1));
        assertEq(registry.getValidatorLane(op1), LANE_1_KALMAN);
        assertEq(registry.getValidatorOperatorId(op1), opId1);

        ValidatorRegistry.ValidatorRecord memory record = registry.getValidator(op1);
        assertEq(record.operatorId, opId1);
        assertEq(record.operator, op1);
        assertEq(record.laneId, LANE_1_KALMAN);
        assertEq(record.metadataHash, meta);
        assertTrue(record.isActive);
    }

    function test_MultipleOperatorsPerLane() public {
        vm.startPrank(owner);
        registry.registerValidator(opId1, op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(opId2, op2, LANE_1_KALMAN, keccak256("K2"));
        registry.registerValidator(opId3, op3, LANE_2_HUBER, keccak256("H1"));
        vm.stopPrank();

        address[] memory kalmanOps = registry.getLaneOperators(LANE_1_KALMAN);
        assertEq(kalmanOps.length, 2);
        assertEq(kalmanOps[0], op1);
        assertEq(kalmanOps[1], op2);

        address[] memory huberOps = registry.getLaneOperators(LANE_2_HUBER);
        assertEq(huberOps.length, 1);
        assertEq(huberOps[0], op3);
    }

    function test_RevertWhen_NonOwnerRegisters() public {
        vm.prank(unauthorized);
        vm.expectRevert();
        registry.registerValidator(opId1, op1, LANE_1_KALMAN, keccak256("K1"));
    }

    function test_RevertWhen_InvalidLaneId() public {
        vm.startPrank(owner);
        vm.expectRevert(abi.encodeWithSelector(ValidatorRegistry.InvalidLaneId.selector, uint8(0)));
        registry.registerValidator(opId1, op1, 0, keccak256("INVALID"));

        vm.expectRevert(abi.encodeWithSelector(ValidatorRegistry.InvalidLaneId.selector, uint8(6)));
        registry.registerValidator(opId2, op2, 6, keccak256("INVALID"));
        vm.stopPrank();
    }

    function test_RevertWhen_DuplicateRegistration() public {
        vm.startPrank(owner);
        registry.registerValidator(opId1, op1, LANE_1_KALMAN, keccak256("K1"));
        vm.expectRevert(abi.encodeWithSelector(ValidatorRegistry.ValidatorAlreadyRegistered.selector, op1));
        registry.registerValidator(opId1, op1, LANE_2_HUBER, keccak256("K2"));
        vm.stopPrank();
    }

    function test_LaneRoleClassification() public view {
        assertEq(uint8(registry.getLaneRole(LANE_1_KALMAN)), uint8(ValidatorRegistry.LaneRole.PRICE_ESTIMATOR));
        assertEq(uint8(registry.getLaneRole(LANE_2_HUBER)), uint8(ValidatorRegistry.LaneRole.PRICE_ESTIMATOR));
        assertEq(uint8(registry.getLaneRole(LANE_3_JSD)), uint8(ValidatorRegistry.LaneRole.DIAGNOSTIC));
        assertEq(uint8(registry.getLaneRole(LANE_4_OU)), uint8(ValidatorRegistry.LaneRole.DIAGNOSTIC));
        assertEq(uint8(registry.getLaneRole(LANE_5_CUSUM)), uint8(ValidatorRegistry.LaneRole.DIAGNOSTIC));

        assertTrue(registry.isPriceEstimatorLane(LANE_1_KALMAN));
        assertTrue(registry.isPriceEstimatorLane(LANE_2_HUBER));
        assertFalse(registry.isPriceEstimatorLane(LANE_3_JSD));

        assertTrue(registry.isDiagnosticLane(LANE_3_JSD));
        assertTrue(registry.isDiagnosticLane(LANE_4_OU));
        assertTrue(registry.isDiagnosticLane(LANE_5_CUSUM));
        assertFalse(registry.isDiagnosticLane(LANE_1_KALMAN));
    }

    function test_SetStatusAndMetadata() public {
        vm.startPrank(owner);
        registry.registerValidator(opId1, op1, LANE_1_KALMAN, keccak256("INIT"));

        registry.setValidatorStatus(op1, false);
        assertFalse(registry.isValidatorActive(op1));

        registry.setValidatorStatus(op1, true);
        assertTrue(registry.isValidatorActive(op1));
        vm.stopPrank();

        bytes32 newMeta = keccak256("NEW_META");
        vm.prank(op1);
        registry.updateMetadataHash(op1, newMeta);

        ValidatorRegistry.ValidatorRecord memory record = registry.getValidator(op1);
        assertEq(record.metadataHash, newMeta);
    }
}
