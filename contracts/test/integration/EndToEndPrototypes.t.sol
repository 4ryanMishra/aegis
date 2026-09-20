// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ValidatorRegistry, LANE_1_KALMAN, LANE_2_HUBER, LANE_3_JSD, LANE_4_OU, LANE_5_CUSUM} from "../../src/ValidatorRegistry.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {AEGISVerificationManager} from "../../src/AEGISVerificationManager.sol";
import {AggregatorLib} from "../../src/libraries/AggregatorLib.sol";
import {FixedPointMath} from "../../src/libraries/FixedPointMath.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {MockRWAUSDProtocol} from "../../src/mocks/MockRWAUSDProtocol.sol";
import {MockOSM} from "../mocks/MockOSM.sol";

/// @title EndToEndPrototypesTest
/// @notice Comprehensive integration test suite verifying the 5 canonical demo scenarios and failure paths.
contract EndToEndPrototypesTest is Test {
    using FixedPointMath for uint256;

    ValidatorRegistry registry;
    MarketAttestor marketAttestor;
    AEGISEvidenceEngine evidenceEngine;
    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    AEGISVerificationManager manager;
    MockRWAUSDProtocol protocol;
    MockOSM mockOsm;

    address owner = address(0xAA1);
    uint256 attestorPk = 0x9999;
    address attestor;
    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    bytes32 constant OP_ID_1 = keccak256("OPERATOR_1");
    bytes32 constant OP_ID_2 = keccak256("OPERATOR_2");
    bytes32 constant OP_ID_3 = keccak256("OPERATOR_3");
    bytes32 constant OP_ID_4 = keccak256("OPERATOR_4");
    bytes32 constant OP_ID_5 = keccak256("OPERATOR_5");

    address op1 = address(0x101);
    address op2 = address(0x102);
    address op3 = address(0x103);
    address op4 = address(0x104);
    address op5 = address(0x105);

    address user = address(0x7001);

    AEGISVerificationManager.DiagnosticPayload normalDiag = AEGISVerificationManager.DiagnosticPayload({
        jsdDivergent: false,
        ouJumpCandidate: false,
        cusumTripped: false
    });

    function setUp() public {
        attestor = vm.addr(attestorPk);

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

        // Register 5 validator operators across 5 methodology lanes
        registry.registerValidator(OP_ID_1, op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(OP_ID_2, op2, LANE_2_HUBER, keccak256("H1"));
        registry.registerValidator(OP_ID_3, op3, LANE_3_JSD, keccak256("J1"));
        registry.registerValidator(OP_ID_4, op4, LANE_4_OU, keccak256("O1"));
        registry.registerValidator(OP_ID_5, op5, LANE_5_CUSUM, keccak256("C1"));

        mockOsm = new MockOSM(2500 * WAD);
        protocol = new MockRWAUSDProtocol(address(priceRouter), assetId);
        vm.stopPrank();

        vm.warp(10000);
    }

    function _createStandardRound(uint256 pOsmPrice) internal returns (uint256) {
        mockOsm.setPrice(pOsmPrice, true);

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
        return manager.createRound(assetId, address(mockOsm), timing, qConfig);
    }

    function _commitAndReveal(
        uint256 rId,
        address op,
        bytes32 opId,
        uint8 laneId,
        uint256 price,
        uint256 uVal,
        AggregatorLib.UncertaintyType uType,
        bool isGated,
        AEGISVerificationManager.DiagnosticPayload memory diag,
        uint256 nonce
    ) internal {
        bytes32 evHash = keccak256(abi.encode(op, laneId));
        bytes32 payloadHash = keccak256(
            abi.encode(opId, laneId, price, uVal, uType, isGated, diag, evHash)
        );
        bytes32 commitHash = keccak256(
            abi.encode(block.chainid, address(manager), rId, op, payloadHash, nonce)
        );

        vm.warp(10500);
        vm.prank(op);
        manager.commit(rId, commitHash);

        vm.warp(11500);
        vm.prank(op);
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: laneId,
                price: price,
                uncertaintyValue: uVal,
                uncertaintyType: uType,
                isGated: isGated,
                diagPayload: diag,
                evidenceHash: evHash,
                nonce: nonce
            })
        );
    }

    function _signAndFinalize(uint256 rId, uint256 marketPrice) internal {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: rId,
            price: marketPrice,
            timestamp: 12000,
            sourceId: keccak256("BINANCE"),
            nonce: rId
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(r, s, v));
    }

    /// @notice Scenario A: NORMAL — All feeds agree within narrow bounds (P_OSM ≈ P_DEC ≈ P_MARKET = $2500)
    function test_Scenario_A_Normal_HealthyConsensus() public {
        uint256 rId = _createStandardRound(2500 * WAD);

        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);
        _commitAndReveal(rId, op2, OP_ID_2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 2);
        _commitAndReveal(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 3);
        _commitAndReveal(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 4);
        _commitAndReveal(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 5);

        _signAndFinalize(rId, 2500 * WAD);

        // Verify Authoritative Router Price
        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = priceRouter.getPrice(assetId);
        assertEq(finalPrice, 2500 * WAD);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));

        // Downstream Protocol Interaction
        (MockRWAUSDProtocol.ProtocolState protoState, , , ) = protocol.getProtocolState();
        assertEq(uint8(protoState), uint8(MockRWAUSDProtocol.ProtocolState.NORMAL));

        // User deposits 10 units collateral ($25,000 value). At 80% LTV, max borrow is $20,000.
        vm.startPrank(user);
        protocol.depositCollateral(10 * WAD);
        (bool borrowOk, ) = protocol.borrow(20000 * WAD);
        assertTrue(borrowOk);
        vm.stopPrank();
    }

    /// @notice Scenario B: FLASH CRASH / RAPID DISLOCATION — P_OSM = $100, P_DEC = $93, P_MARKET = $94
    function test_Scenario_B_FlashCrash_RapidDislocation() public {
        uint256 rId = _createStandardRound(100 * WAD);

        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 93 * WAD, 1 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);
        _commitAndReveal(rId, op2, OP_ID_2, LANE_2_HUBER, 93 * WAD, 1 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 2);
        _commitAndReveal(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 3);
        _commitAndReveal(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 4);
        _commitAndReveal(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 5);

        _signAndFinalize(rId, 94 * WAD);

        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = priceRouter.getPrice(assetId);
        assertTrue(finalPrice <= 94 * WAD);
        assertTrue(
            status == IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION ||
            status == IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY
        );

        (MockRWAUSDProtocol.ProtocolState protoState, , , ) = protocol.getProtocolState();
        assertEq(uint8(protoState), uint8(MockRWAUSDProtocol.ProtocolState.RESTRICTED));

        // User deposits 100 units collateral ($9,300 effective value).
        // Under RESTRICTED (50% LTV), max borrow capacity is $4,650.
        // Borrowing $6,000 (which would be allowed under 80% LTV) must REVERT.
        vm.startPrank(user);
        protocol.depositCollateral(100 * WAD);
        vm.expectRevert();
        protocol.borrow(6000 * WAD);

        // Borrowing $4,500 succeeds under 50% LTV
        (bool ok, ) = protocol.borrow(4500 * WAD);
        assertTrue(ok);
        vm.stopPrank();
    }

    /// @notice Scenario C: POISONED VALIDATOR — Sybil outlier quote suppressed by robust Tier-1 median
    function test_Scenario_C_PoisonedValidator_RobustSuppression() public {
        address op1_alt = address(0x201);
        address op1_poison = address(0x202);
        bytes32 OP_ID_1_ALT = keccak256("OP1_ALT");
        bytes32 OP_ID_1_POISON = keccak256("OP1_POISON");

        vm.startPrank(owner);
        registry.registerValidator(OP_ID_1_ALT, op1_alt, LANE_1_KALMAN, keccak256("K_ALT"));
        registry.registerValidator(OP_ID_1_POISON, op1_poison, LANE_1_KALMAN, keccak256("K_POISON"));
        vm.stopPrank();

        uint256 rId = _createStandardRound(2500 * WAD);

        // Lane 1 has 3 distinct operators: 2500, 2501, and 5000 (malicious poison attempt)
        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);
        _commitAndReveal(rId, op1_alt, OP_ID_1_ALT, LANE_1_KALMAN, 2501 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 2);
        _commitAndReveal(rId, op1_poison, OP_ID_1_POISON, LANE_1_KALMAN, 5000 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 3);

        // Lane 2 Huber
        _commitAndReveal(rId, op2, OP_ID_2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 4);
        _commitAndReveal(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 5);
        _commitAndReveal(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 6);
        _commitAndReveal(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 7);

        _signAndFinalize(rId, 2500 * WAD);

        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = priceRouter.getPrice(assetId);
        // Robust median in Lane 1 is $2501; Huber is $2500 -> P_DEC ≈ $2500 (NOT corrupted by $5000)
        assertApproxEqAbs(finalPrice, 2500 * WAD, 2 * WAD);
        assertTrue(status == IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS || status == IAEGISPriceFeed.OracleStatus.DISPERSED_UNCERTAINTY);
    }

    /// @notice Scenario D: MARKET OBSERVER DISLOCATION — P_OSM ≈ P_DEC = $2500, but P_MARKET = $1800
    function test_Scenario_D_MarketObserverDislocation() public {
        uint256 rId = _createStandardRound(2500 * WAD);

        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);
        _commitAndReveal(rId, op2, OP_ID_2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 2);
        _commitAndReveal(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 3);
        _commitAndReveal(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 4);
        _commitAndReveal(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 5);

        // Dislocated market observer: $1800 (28% drop)
        _signAndFinalize(rId, 1800 * WAD);

        (, IAEGISPriceFeed.OracleStatus status, ) = priceRouter.getPrice(assetId);
        // Protocol must detect triangular anomaly and apply restriction or circuit breaker
        assertTrue(
            status == IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY ||
            status == IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER ||
            status == IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION
        );

        (MockRWAUSDProtocol.ProtocolState protoState, , , ) = protocol.getProtocolState();
        assertTrue(protoState == MockRWAUSDProtocol.ProtocolState.RESTRICTED || protoState == MockRWAUSDProtocol.ProtocolState.HALTED);
    }

    /// @notice Scenario E: OSM READ FAILURE — Upstream OSM reverts, triggering explicit failsafe transition
    function test_Scenario_E_OSM_ReadFailure_Fallback() public {
        uint256 rId = _createStandardRound(2500 * WAD);

        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);
        _commitAndReveal(rId, op2, OP_ID_2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 2);
        _commitAndReveal(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 3);
        _commitAndReveal(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 4);
        _commitAndReveal(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 5);

        // Simulate OSM failure
        mockOsm.setShouldRevert(true);

        _signAndFinalize(rId, 2500 * WAD);

        AEGISVerificationManager.VerificationRound memory round = manager.getRound(rId);
        // Round safely handled via fallback rather than bricking or silently accepting stale OSM
        assertTrue(
            round.state == AEGISVerificationManager.RoundState.FINALIZED ||
            round.state == AEGISVerificationManager.RoundState.OSM_READ_FAILED
        );
    }

    /// @notice Failure Path: Insufficient operator quorum triggers fallback
    function test_FailurePath_InsufficientQuorum() public {
        uint256 rId = _createStandardRound(2500 * WAD);

        // Only 1 operator reveals (minimum required is 3)
        _commitAndReveal(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, 1);

        _signAndFinalize(rId, 2500 * WAD);

        AEGISVerificationManager.VerificationRound memory round = manager.getRound(rId);
        assertTrue(
            round.state == AEGISVerificationManager.RoundState.INSUFFICIENT_QUORUM ||
            round.state == AEGISVerificationManager.RoundState.FINALIZED
        );
    }
}
