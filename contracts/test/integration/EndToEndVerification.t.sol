// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {
    AEGISVerificationManager,
    LANE_1_KALMAN,
    LANE_2_HUBER,
    LANE_3_JSD,
    LANE_4_OU,
    LANE_5_CUSUM
} from "../../src/AEGISVerificationManager.sol";
import {ValidatorRegistry} from "../../src/ValidatorRegistry.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {MockOSM} from "../mocks/MockOSM.sol";
import {MockMultipliConsumer} from "../mocks/MockMultipliConsumer.sol";

contract EndToEndVerificationTest is Test {
    ValidatorRegistry registry;
    MarketAttestor marketAttestor;
    AEGISEvidenceEngine evidenceEngine;
    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    AEGISVerificationManager manager;
    MockOSM mockOsm;
    MockMultipliConsumer multipliConsumer;

    address owner = address(0xAA1);
    uint256 attestorPk = 0xA11CE;
    address attestor;

    // 5 Validator Nodes
    uint256 op1Pk = 0x101; address op1;
    uint256 op2Pk = 0x102; address op2;
    uint256 op3Pk = 0x103; address op3;
    uint256 op4Pk = 0x104; address op4;
    uint256 op5Pk = 0x105; address op5;

    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    AEGISVerificationManager.DiagnosticPayload normalDiag = AEGISVerificationManager.DiagnosticPayload({
        jsdDivergent: false,
        ouJumpCandidate: false,
        cusumTripped: false
    });

    function setUp() public {
        vm.warp(10000);
        attestor = vm.addr(attestorPk);
        op1 = vm.addr(op1Pk);
        op2 = vm.addr(op2Pk);
        op3 = vm.addr(op3Pk);
        op4 = vm.addr(op4Pk);
        op5 = vm.addr(op5Pk);

        vm.startPrank(owner);
        registry = new ValidatorRegistry(owner);
        marketAttestor = new MarketAttestor(owner);
        evidenceEngine = new AEGISEvidenceEngine(owner);
        decisionEngine = new AEGISDecisionEngine(owner);
        priceRouter = new AEGISPriceRouter(owner);

        manager = new AEGISVerificationManager(
            owner,
            address(registry),
            address(marketAttestor),
            address(evidenceEngine),
            address(decisionEngine),
            address(priceRouter)
        );

        priceRouter.setVerificationManager(address(manager));
        marketAttestor.setAttestorAuthorization(attestor, true);

        multipliConsumer = new MockMultipliConsumer(address(priceRouter));

        // Register 5 operators across 5 lanes
        registry.registerValidator(op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(op2, LANE_2_HUBER, keccak256("H1"));
        registry.registerValidator(op3, LANE_3_JSD, keccak256("J1"));
        registry.registerValidator(op4, LANE_4_OU, keccak256("O1"));
        registry.registerValidator(op5, LANE_5_CUSUM, keccak256("C1"));

        mockOsm = new MockOSM(2500 * WAD);
        vm.stopPrank();
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

        vm.prank(op);
        manager.commit(rId, commitHash);

        vm.warp(11500);

        vm.prank(op);
        manager.reveal(rId, laneId, price, uLow, uHigh, isGated, diag, evHash, nonce);

        vm.warp(10500);
    }

    function test_EndToEnd_T0_to_T1_ParallelVerification_HealthyConsensus() public {
        // T0 (10000): OSM observation entered delay queue.
        // Concurrently, AEGIS verification round opens (zero double-delay!)
        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 3,
            minDistinctOperators: 3,
            minDistinctApplicableLanes: 3,
            ouNotApplicable: false
        });

        vm.prank(owner);
        uint256 rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);

        // T0 -> T1: Concurrent execution during the 1-hour OSM window
        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 1);
        _commitAndReveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 2);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, normalDiag, 3);
        _commitAndReveal(rId, op4, LANE_4_OU, 0, 0, 0, false, normalDiag, 4);
        _commitAndReveal(rId, op5, LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 5);

        // Prepare terminal market attestation at window end
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

        // T1 (12000): 1-hour OSM delay matures. P_OSM is available.
        vm.warp(12000);

        // Atomic keeper execution via finalizeRoundWithAttestation
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(sigR, sigS, v));

        // Post-T1: Check that NO second OSM delay was added, OSM was never written to
        (uint256 osmPrice,) = mockOsm.readPrice();
        assertEq(osmPrice, 2500 * WAD); // Pure read-only inspection

        // Multipli protocol consumes EXACTLY ONE authoritative P_FINAL
        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status,) = priceRouter.getPrice(assetId);
        assertEq(finalPrice, 2500 * WAD);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));

        // Downstream borrowing evaluated under standard 80% LTV
        // Collateral: 10 XAU = $25,000. 80% LTV = $20,000 max borrow.
        (bool approved, string memory reason, ) = multipliConsumer.evaluateBorrow(
            assetId,
            10 * WAD,
            18000 * WAD // Request $18,000 debt
        );
        assertTrue(approved);
        assertEq(reason, "APPROVED");
    }

    function test_EndToEnd_DislocatedOSM_RestrictedLTV() public {
        // Upstream OSM is attacked or stale at $3000 (+20% dislocation)
        mockOsm.setPrice(3000 * WAD, true);

        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 3,
            minDistinctOperators: 3,
            minDistinctApplicableLanes: 3,
            ouNotApplicable: false
        });

        vm.prank(owner);
        uint256 rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);

        // Real market & honest validators agree at true market price: $2500
        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 1);
        _commitAndReveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 2);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, normalDiag, 3);
        _commitAndReveal(rId, op4, LANE_4_OU, 0, 0, 0, false, normalDiag, 4);
        _commitAndReveal(rId, op5, LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 5);

        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 2500 * WAD,
            timestamp: 12000,
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 sigR, bytes32 sigS) = vm.sign(attestorPk, digest);

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(sigR, sigS, v));

        // Decision Engine detected OSM dislocation: replaced corrupted $3000 with decentralized $2500!
        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status,) = priceRouter.getPrice(assetId);
        assertEq(finalPrice, 2500 * WAD);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY));

        // Multipli consumer automatically applies RESTRICTED_LTV (60%) instead of standard 80%!
        // Collateral: 10 XAU = $25,000. 60% LTV = $15,000 max borrow.
        // A requested debt of $18,000 must be REJECTED!
        (bool approved, string memory reason, ) = multipliConsumer.evaluateBorrow(
            assetId,
            10 * WAD,
            18000 * WAD
        );
        assertFalse(approved);
        assertEq(reason, "EXCEEDS_LTV_LIMIT");

        // A safe debt of $14,000 is approved
        (bool approvedSafe, string memory reasonSafe, ) = multipliConsumer.evaluateBorrow(
            assetId,
            10 * WAD,
            14000 * WAD
        );
        assertTrue(approvedSafe);
        assertEq(reasonSafe, "APPROVED");
    }

    function test_EndToEnd_ExtremeTurmoil_CircuitBreakerHaltsProtocol() public {
        // Complete market chaos: OSM = 1500, DEC = 2500, MKT = 3500 (>10% dislocation across all)
        mockOsm.setPrice(1500 * WAD, true);

        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 3,
            minDistinctOperators: 3,
            minDistinctApplicableLanes: 3,
            ouNotApplicable: false
        });

        vm.prank(owner);
        uint256 rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);

        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 1);
        _commitAndReveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, normalDiag, 2);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, normalDiag, 3);
        _commitAndReveal(rId, op4, LANE_4_OU, 0, 0, 0, false, normalDiag, 4);
        _commitAndReveal(rId, op5, LANE_5_CUSUM, 0, 0, 0, false, normalDiag, 5);

        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 3500 * WAD, // Terminal market diverged by 40%
            timestamp: 12000,
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 sigR, bytes32 sigS) = vm.sign(attestorPk, digest);

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(sigR, sigS, v));

        // Circuit breaker tripped! Status is HALTED_CIRCUIT_BREAKER
        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status,) = priceRouter.getPrice(assetId);
        assertEq(finalPrice, 0);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER));

        // Multipli lending engine completely freezes new debt
        (bool approved, string memory reason, ) = multipliConsumer.evaluateBorrow(
            assetId,
            10 * WAD,
            1000 * WAD
        );
        assertFalse(approved);
        assertEq(reason, "CIRCUIT_BREAKER_ACTIVE");
    }
}
