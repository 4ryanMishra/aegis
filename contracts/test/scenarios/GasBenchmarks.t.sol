// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ValidatorRegistry} from "../../src/ValidatorRegistry.sol";
import {AEGISVerificationManager} from "../../src/AEGISVerificationManager.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";
import {MockOSM} from "../mocks/MockOSM.sol";

contract GasBenchmarksTest is Test {
    ValidatorRegistry registry;
    AEGISEvidenceEngine evidenceEngine;
    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    MarketAttestor marketAttestor;
    AEGISVerificationManager manager;
    MockOSM mockOsm;

    address owner = address(0xAA1);
    uint256 attestorPk = 0xBEEF;
    address attestor;
    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    uint8 constant LANE_1_KALMAN = 1;
    uint8 constant LANE_2_HUBER = 2;
    uint8 constant LANE_3_JSD = 3;
    uint8 constant LANE_4_OU = 4;
    uint8 constant LANE_5_CUSUM = 5;

    address[] operators;
    uint8[] lanes;

    AEGISVerificationManager.DiagnosticPayload normalDiag = AEGISVerificationManager.DiagnosticPayload({
        jsdDivergent: false,
        ouJumpCandidate: false,
        cusumTripped: false
    });

    function setUp() public {
        attestor = vm.addr(attestorPk);

        vm.startPrank(owner);
        registry = new ValidatorRegistry(owner);
        evidenceEngine = new AEGISEvidenceEngine(owner);
        decisionEngine = new AEGISDecisionEngine(owner);
        priceRouter = new AEGISPriceRouter(owner);
        marketAttestor = new MarketAttestor(owner);
        marketAttestor.setAttestorAuthorization(attestor, true);

        manager = new AEGISVerificationManager(
            owner,
            address(registry),
            address(marketAttestor),
            address(evidenceEngine),
            address(decisionEngine),
            address(priceRouter)
        );

        priceRouter.setVerificationManager(address(manager));
        mockOsm = new MockOSM(2500 * WAD);

        // Pre-register 10 validator operators across the 5 lanes
        // Lane 1: ops 0, 1 (2 operators)
        // Lane 2: ops 2, 3 (2 operators)
        // Lane 3: ops 4, 5 (2 operators)
        // Lane 4: ops 6, 7 (2 operators)
        // Lane 5: ops 8, 9 (2 operators)
        for (uint256 i = 0; i < 10; i++) {
            address op = vm.addr(0x1000 + i);
            uint8 lane = uint8((i / 2) + 1);
            registry.registerValidator(op, lane, keccak256(abi.encode("Node", i)));
            operators.push(op);
            lanes.push(lane);
        }
        vm.stopPrank();
        vm.warp(10000);
    }

    function _commitAndReveal(
        uint256 rId,
        address op,
        uint8 laneId,
        uint256 price,
        uint256 uLow,
        uint256 uHigh,
        bool isGated,
        AEGISVerificationManager.DiagnosticPayload memory diag,
        uint256 nonce
    ) internal {
        bytes32 evHash = keccak256(abi.encode(op, laneId));
        bytes32 payloadHash = keccak256(
            abi.encode(laneId, price, uLow, uHigh, isGated, diag, evHash)
        );
        bytes32 commitHash = keccak256(
            abi.encode(block.chainid, address(manager), rId, op, payloadHash, nonce)
        );

        vm.warp(10500);
        vm.prank(op);
        manager.commit(rId, commitHash);

        vm.warp(11500);
        vm.prank(op);
        manager.reveal(rId, laneId, price, uLow, uHigh, isGated, diag, evHash, nonce);
    }

    /// @notice Gas Benchmark: Full verification round with 5 validators (1 per lane)
    function test_Benchmark_RoundLifecycle_5Validators() public {
        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 5,
            minDistinctOperators: 5,
            minDistinctApplicableLanes: 5,
            ouNotApplicable: false
        });

        vm.prank(owner);
        uint256 rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);

        // Submit 5 validators (1 per lane)
        _commitAndReveal(rId, operators[0], LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 1);
        _commitAndReveal(rId, operators[2], LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 2);
        _commitAndReveal(rId, operators[4], LANE_3_JSD, 0, 0, 0, false, normalDiag, 3);
        _commitAndReveal(rId, operators[6], LANE_4_OU, 0, 0, 0, false, normalDiag, 4);
        _commitAndReveal(rId, operators[8], LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 5);

        // Market attestation
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 2500 * WAD,
            timestamp: 12000,
            sourceId: keccak256("BINANCE"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 sigR, bytes32 sigS) = vm.sign(attestorPk, digest);

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(sigR, sigS, v));

        (uint256 finalPrice,,) = priceRouter.getPrice(assetId);
        assertEq(finalPrice, 2500 * WAD);
    }

    /// @notice Gas Benchmark: Full verification round with 10 validators (2 per lane across all 5 lanes)
    function test_Benchmark_RoundLifecycle_10Validators() public {
        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 10,
            minDistinctOperators: 10,
            minDistinctApplicableLanes: 5,
            ouNotApplicable: false
        });

        vm.prank(owner);
        uint256 rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);

        // 10 validators: 2 per lane
        _commitAndReveal(rId, operators[0], LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 1);
        _commitAndReveal(rId, operators[1], LANE_1_KALMAN, 2501 * WAD, 2491 * WAD, 2511 * WAD, false, normalDiag, 2);
        _commitAndReveal(rId, operators[2], LANE_2_HUBER, 2499 * WAD, 2489 * WAD, 2509 * WAD, false, normalDiag, 3);
        _commitAndReveal(rId, operators[3], LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 4);
        _commitAndReveal(rId, operators[4], LANE_3_JSD, 0, 0, 0, false, normalDiag, 5);
        _commitAndReveal(rId, operators[5], LANE_3_JSD, 0, 0, 0, false, normalDiag, 6);
        _commitAndReveal(rId, operators[6], LANE_4_OU, 0, 0, 0, false, normalDiag, 7);
        _commitAndReveal(rId, operators[7], LANE_4_OU, 0, 0, 0, false, normalDiag, 8);
        _commitAndReveal(rId, operators[8], LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 9);
        _commitAndReveal(rId, operators[9], LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 10);

        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 2500 * WAD,
            timestamp: 12000,
            sourceId: keccak256("BINANCE"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 sigR, bytes32 sigS) = vm.sign(attestorPk, digest);

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(sigR, sigS, v));

        (uint256 finalPrice,,) = priceRouter.getPrice(assetId);
        assertTrue(finalPrice > 0);
    }
}
