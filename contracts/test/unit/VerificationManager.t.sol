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

contract VerificationManagerTest is Test {
    ValidatorRegistry registry;
    MarketAttestor marketAttestor;
    AEGISEvidenceEngine evidenceEngine;
    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    AEGISVerificationManager manager;
    MockOSM mockOsm;

    address owner = address(0xAA1);
    uint256 attestorPk = 0xA11CE;
    address attestor;

    // 5 Validator Nodes
    uint256 op1Pk = 0x101; address op1; // Lane 1 Kalman
    uint256 op2Pk = 0x102; address op2; // Lane 2 Huber
    uint256 op3Pk = 0x103; address op3; // Lane 3 JSD
    uint256 op4Pk = 0x104; address op4; // Lane 4 OU
    uint256 op5Pk = 0x105; address op5; // Lane 5 CUSUM

    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    AEGISVerificationManager.DiagnosticPayload emptyDiag = AEGISVerificationManager.DiagnosticPayload({
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

        // Register 5 operators for 5 methodology lanes
        registry.registerValidator(op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(op2, LANE_2_HUBER, keccak256("H1"));
        registry.registerValidator(op3, LANE_3_JSD, keccak256("J1"));
        registry.registerValidator(op4, LANE_4_OU, keccak256("O1"));
        registry.registerValidator(op5, LANE_5_CUSUM, keccak256("C1"));

        mockOsm = new MockOSM(2500 * WAD);
        vm.stopPrank();
    }

    function _createStandardRound(bool ouNotApplicable) internal returns (uint256) {
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
            ouNotApplicable: ouNotApplicable
        });

        vm.prank(owner);
        return manager.createRound(assetId, address(mockOsm), timing, qConfig);
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

        vm.warp(10500); // Reset for next commit if in loop
    }

    function test_FullVerificationLifecycle_HealthyConsensus() public {
        uint256 rId = _createStandardRound(false);

        // Commit & reveal across 5 lanes (all agreeing at $2500)
        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 1);
        _commitAndReveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 2);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, emptyDiag, 3);
        _commitAndReveal(rId, op4, LANE_4_OU, 0, 0, 0, false, emptyDiag, 4);
        _commitAndReveal(rId, op5, LANE_5_CUSUM, 0, 0, 0, false, emptyDiag, 5);

        // Advance to revealEnd (12000)
        vm.warp(12000);

        // Step 1: Aggregate validator evidence
        manager.aggregateValidatorEvidence(rId);
        AEGISVerificationManager.VerificationRound memory rAfterAgg = manager.getRound(rId);
        assertEq(rAfterAgg.pDec, 2500 * WAD);

        // Step 2: Submit terminal market attestation ($2500)
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 2500 * WAD,
            timestamp: 12000,
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);
        manager.submitMarketAttestation(rId, att, abi.encodePacked(r, s, v));

        // Step 3: Read OSM and evaluate evidence
        manager.readOsmAndEvaluateEvidence(rId);
        AEGISVerificationManager.VerificationRound memory rAfterOsm = manager.getRound(rId);
        assertEq(rAfterOsm.pOsm, 2500 * WAD);
        assertEq(uint8(rAfterOsm.state), uint8(AEGISVerificationManager.RoundState.DECISION_READY));

        // Step 4: Execute decision and finalize
        manager.executeDecisionAndFinalize(rId);

        AEGISVerificationManager.VerificationRound memory rFinal = manager.getRound(rId);
        assertEq(rFinal.pFinal, 2500 * WAD);
        assertEq(uint8(rFinal.finalStatus), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));

        // Verify AEGISPriceRouter received finalized price
        (uint256 routerPrice, IAEGISPriceFeed.OracleStatus routerStatus,) = priceRouter.getPrice(assetId);
        assertEq(routerPrice, 2500 * WAD);
        assertEq(uint8(routerStatus), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));
    }

    function test_SingleLaneQuorumProhibition() public {
        uint256 rId = _createStandardRound(false);

        // Even if 3 operators reveal, if they are all in Lane 1, distinct applicable lanes = 1 < 3
        address op1B = address(0xB1);
        address op1C = address(0xB2);
        vm.startPrank(owner);
        registry.registerValidator(op1B, LANE_1_KALMAN, keccak256("K1B"));
        registry.registerValidator(op1C, LANE_1_KALMAN, keccak256("K1C"));
        vm.stopPrank();

        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 1);
        _commitAndReveal(rId, op1B, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 2);
        _commitAndReveal(rId, op1C, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 3);

        vm.warp(12000);
        manager.aggregateValidatorEvidence(rId);

        AEGISVerificationManager.VerificationRound memory r = manager.getRound(rId);
        // Quorum fails because N_lanes = 1 < 3! A single lane cannot self-certify!
        assertEq(uint8(r.state), uint8(AEGISVerificationManager.RoundState.INSUFFICIENT_QUORUM));
    }

    function test_NotApplicableOU_PassesQuorum() public {
        // Asset where OU is marked NOT_APPLICABLE
        uint256 rId = _createStandardRound(true);

        // Submit reveals for Lane 1 (Kalman), Lane 3 (JSD), Lane 5 (CUSUM) -> 3 distinct applicable lanes!
        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 1);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, emptyDiag, 2);
        _commitAndReveal(rId, op5, LANE_5_CUSUM, 0, 0, 0, false, emptyDiag, 3);

        vm.warp(12000);
        manager.aggregateValidatorEvidence(rId);

        AEGISVerificationManager.VerificationRound memory r = manager.getRound(rId);
        // Quorum is met! OU being NOT_APPLICABLE did not trigger failure!
        assertEq(uint8(r.state), uint8(AEGISVerificationManager.RoundState.AGGREGATED));
        assertEq(r.pDec, 2500 * WAD);
    }

    function test_OsmReadFailure_Fallback() public {
        uint256 rId = _createStandardRound(false);

        _commitAndReveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 1);
        _commitAndReveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 2490 * WAD, 2510 * WAD, false, emptyDiag, 2);
        _commitAndReveal(rId, op3, LANE_3_JSD, 0, 0, 0, false, emptyDiag, 3);
        _commitAndReveal(rId, op4, LANE_4_OU, 0, 0, 0, false, emptyDiag, 4);

        vm.warp(12000);
        manager.aggregateValidatorEvidence(rId);

        // Submit market attestation
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: 2500 * WAD,
            timestamp: 12000,
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);
        manager.submitMarketAttestation(rId, att, abi.encodePacked(r, s, v));

        // Configure MockOSM to revert
        mockOsm.setShouldRevert(true);

        // OSM read fails gracefully -> transitions to OSM_READ_FAILED
        manager.readOsmAndEvaluateEvidence(rId);
        AEGISVerificationManager.VerificationRound memory roundRec = manager.getRound(rId);
        assertEq(uint8(roundRec.state), uint8(AEGISVerificationManager.RoundState.OSM_READ_FAILED));

        // Failsafe execution: P_DEC and P_MARKET agree (< 200 BPS) -> fallback to P_DEC with warning
        manager.executeDecisionAndFinalize(rId);
        (uint256 routerPrice, IAEGISPriceFeed.OracleStatus routerStatus,) = priceRouter.getPrice(assetId);
        assertEq(routerPrice, 2500 * WAD);
        assertEq(uint8(routerStatus), uint8(IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY));
    }
}
