// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ValidatorRegistry, LANE_1_KALMAN, LANE_2_HUBER, LANE_3_JSD, LANE_4_OU, LANE_5_CUSUM} from "../../src/ValidatorRegistry.sol";
import {AEGISVerificationManager} from "../../src/AEGISVerificationManager.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {AggregatorLib} from "../../src/libraries/AggregatorLib.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {MockOSM} from "../mocks/MockOSM.sol";

contract StateSecurityAdversarialTest is Test {
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

    bytes32 constant OP_ID_1 = keccak256("ORGANIZATION_ONE");
    bytes32 constant OP_ID_2 = keccak256("ORGANIZATION_TWO");
    bytes32 constant OP_ID_3 = keccak256("ORGANIZATION_THREE");
    bytes32 constant OP_ID_4 = keccak256("ORGANIZATION_FOUR");
    bytes32 constant OP_ID_5 = keccak256("ORGANIZATION_FIVE");

    address op1 = address(0x101);
    address op1_alt = address(0x102); // Same operator ID (OP_ID_1), different address
    address op2 = address(0x201);
    address op3 = address(0x301);
    address op4 = address(0x401);
    address op5 = address(0x501);
    address unauth = address(0x999);

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

        // Register default operators
        registry.registerValidator(OP_ID_1, op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(OP_ID_2, op2, LANE_2_HUBER, keccak256("H1"));
        registry.registerValidator(OP_ID_3, op3, LANE_3_JSD, keccak256("J1"));
        registry.registerValidator(OP_ID_4, op4, LANE_4_OU, keccak256("O1"));
        registry.registerValidator(OP_ID_5, op5, LANE_5_CUSUM, keccak256("C1"));

        vm.stopPrank();
        vm.warp(10000);
    }

    function _createDefaultRound() internal returns (uint256 rId) {
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
        rId = manager.createRound(assetId, address(mockOsm), timing, qConfig);
    }

    function _commit(
        uint256 rId,
        address op,
        bytes32 opId,
        uint8 laneId,
        uint256 price,
        uint256 uVal,
        AggregatorLib.UncertaintyType uType,
        bool isGated,
        AEGISVerificationManager.DiagnosticPayload memory diag,
        bytes32 evHash,
        uint256 nonce
    ) internal {
        bytes32 payloadHash = keccak256(
            abi.encode(opId, laneId, price, uVal, uType, isGated, diag, evHash)
        );
        bytes32 commitHash = keccak256(
            abi.encode(block.chainid, address(manager), rId, op, payloadHash, nonce)
        );
        vm.warp(10500);
        vm.prank(op);
        manager.commit(rId, commitHash);
    }

    function _reveal(
        uint256 rId,
        address op,
        uint8 laneId,
        uint256 price,
        uint256 uVal,
        AggregatorLib.UncertaintyType uType,
        bool isGated,
        AEGISVerificationManager.DiagnosticPayload memory diag,
        bytes32 evHash,
        uint256 nonce
    ) internal {
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

    /// @notice 1. Same operatorId with multiple addresses counts as ONE distinct operator in quorum.
    function test_Adversarial_SameOperatorId_MultipleAddresses_CountsAsOne() public {
        vm.prank(owner);
        registry.registerValidator(OP_ID_1, op1_alt, LANE_2_HUBER, keccak256("H1_ALT"));

        uint256 rId = _createDefaultRound();

        // op1 (OP_ID_1) in Lane 1
        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);
        _reveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // op1_alt (also OP_ID_1) in Lane 2
        _commit(rId, op1_alt, OP_ID_1, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("2"), 2);
        _reveal(rId, op1_alt, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("2"), 2);

        // op3 (OP_ID_3) in Lane 3
        _commit(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("3"), 3);
        _reveal(rId, op3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("3"), 3);

        // Total reveals: 3, Distinct lanes: 3, BUT distinct operator identities: 2 (OP_ID_1 and OP_ID_3)
        // Min distinct operators is 3 -> Quorum must fail!
        vm.warp(12000);
        manager.aggregateValidatorEvidence(rId);

        AEGISVerificationManager.VerificationRound memory round = manager.getRound(rId);
        assertEq(uint8(round.state), uint8(AEGISVerificationManager.RoundState.INSUFFICIENT_QUORUM));
    }

    /// @notice 2. One operator identity cannot satisfy operator quorum by itself across 5 wallets.
    function test_Adversarial_OneOperatorCannotSatisfyOperatorQuorum() public {
        address[5] memory addrs = [address(0x801), address(0x802), address(0x803), address(0x804), address(0x805)];
        vm.startPrank(owner);
        for (uint8 i = 0; i < 5; i++) {
            registry.registerValidator(OP_ID_1, addrs[i], i + 1, keccak256(abi.encode("NODE", i)));
        }
        vm.stopPrank();

        uint256 rId = _createDefaultRound();

        for (uint8 i = 0; i < 5; i++) {
            uint256 price = (i < 2) ? 2500 * WAD : 0;
            _commit(rId, addrs[i], OP_ID_1, i + 1, price, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("E"), i + 1);
            _reveal(rId, addrs[i], i + 1, price, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("E"), i + 1);
        }

        vm.warp(12000);
        manager.aggregateValidatorEvidence(rId);

        AEGISVerificationManager.VerificationRound memory round = manager.getRound(rId);
        assertEq(uint8(round.state), uint8(AEGISVerificationManager.RoundState.INSUFFICIENT_QUORUM));
    }

    /// @notice 3. Same operatorId with multiple addresses cannot double-influence Tier 1 lane aggregation.
    function test_Adversarial_SameOperatorId_MultipleAddresses_CannotDoubleInfluenceLane() public {
        vm.prank(owner);
        registry.registerValidator(OP_ID_1, op1_alt, LANE_1_KALMAN, keccak256("K1_ALT"));

        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);
        _commit(rId, op1_alt, OP_ID_1, LANE_1_KALMAN, 2600 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("2"), 2);

        _reveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Second reveal under same operatorId in same lane reverts
        vm.warp(11500);
        vm.prank(op1_alt);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.DuplicateOperatorInLane.selector, OP_ID_1, LANE_1_KALMAN));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2600 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("2"),
                nonce: 2
            })
        );
    }

    /// @notice 4. Unauthorized address cannot submit commitments or reveals.
    function test_Adversarial_UnauthorizedAddressCannotSubmit() public {
        uint256 rId = _createDefaultRound();

        vm.warp(10500);
        vm.prank(unauth);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.UnauthorizedValidator.selector, unauth));
        manager.commit(rId, keccak256("FAKE_COMMIT"));
    }

    /// @notice 5. Validator deactivation mid-round prevents reveal.
    function test_Adversarial_ValidatorDeactivationMidRound() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Governance deactivates op1 before reveal
        vm.prank(owner);
        registry.setValidatorStatus(op1, false);

        vm.warp(11500);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.UnauthorizedValidator.selector, op1));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    /// @notice 6. OperatorId mutation mid-round prevents reveal.
    function test_Adversarial_OperatorIdMutationMidRound() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Governance registers op1 under new operatorId OP_ID_2 (e.g. key takeover / reassignment)
        vm.startPrank(owner);
        registry.setValidatorStatus(op1, false);
        // Register new address or update
        vm.stopPrank();

        vm.warp(11500);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.UnauthorizedValidator.selector, op1));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    /// @notice 7. Lane mutation mid-round prevents reveal.
    function test_Adversarial_LaneMutationMidRound() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Governance moves op1 to Lane 2
        vm.prank(owner);
        registry.setValidatorLane(op1, LANE_2_HUBER);

        vm.warp(11500);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.IdentityOrLaneMutated.selector, OP_ID_1, OP_ID_1, LANE_1_KALMAN, LANE_2_HUBER));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    /// @notice 8. Validator lane mismatch (reveal claiming a different lane than registered) is rejected.
    function test_Adversarial_ValidatorLaneMismatch() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        vm.warp(11500);
        vm.prank(op1);
        // Attempt reveal claiming Lane 2
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.IdentityOrLaneMutated.selector, OP_ID_1, OP_ID_1, LANE_1_KALMAN, LANE_1_KALMAN));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_2_HUBER,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    function externalAggregateLaneTier1(
        AggregatorLib.OperatorPriceSubmission[] calldata subs
    ) external pure returns (AggregatorLib.CanonicalLaneEstimate memory) {
        return AggregatorLib.aggregateLaneTier1(subs);
    }

    /// @notice 9. Mixed uncertainty semantics within a lane are rejected.
    function test_Adversarial_MixedUncertaintySemantics_Rejected() public {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](2);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operatorId: OP_ID_1,
            operator: op1,
            price: 2500 * WAD,
            uncertaintyValue: 10 * WAD,
            uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
            isGated: false
        });
        subs[1] = AggregatorLib.OperatorPriceSubmission({
            operatorId: OP_ID_2,
            operator: op2,
            price: 2500 * WAD,
            uncertaintyValue: 10 * WAD,
            uncertaintyType: AggregatorLib.UncertaintyType.ABSOLUTE_STD,
            isGated: false
        });

        vm.expectRevert(AggregatorLib.MixedUncertaintySemantics.selector);
        this.externalAggregateLaneTier1(subs);
    }

    /// @notice 10. Unsupported uncertainty type is rejected from pricing.
    function test_Adversarial_UnsupportedUncertaintyType_Rejected() public {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](1);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operatorId: OP_ID_1,
            operator: op1,
            price: 2500 * WAD,
            uncertaintyValue: 10 * WAD,
            uncertaintyType: AggregatorLib.UncertaintyType.SOURCE_CONFIDENCE,
            isGated: false
        });

        vm.expectRevert(abi.encodeWithSelector(AggregatorLib.UnsupportedUncertaintySemantics.selector, AggregatorLib.UncertaintyType.SOURCE_CONFIDENCE));
        this.externalAggregateLaneTier1(subs);
    }

    /// @notice 11. CI95_HALF_WIDTH converts strictly via sigma = halfWidth / 1.96.
    function test_Adversarial_ValidCI95HalfWidthConversion() public pure {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](1);
        // Set half-width = 1.96 * 10 WAD = 19.6 WAD = 196 * 1e17
        uint256 halfWidth = 196 * 1e17;
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operatorId: keccak256("OP"),
            operator: address(0x1),
            price: 2500 * WAD,
            uncertaintyValue: halfWidth,
            uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);
        // sigma = (196 * 1e17 * 100) / 196 = 100 * 1e17 = 10 WAD
        uint256 expectedSigma = 10 * WAD;
        assertEq(est.sigmaLane, expectedSigma);
    }

    /// @notice 12. Stale market attestation is rejected.
    function test_Adversarial_StaleMarketAttestation_Rejected() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: 1,
            price: 2500 * WAD,
            timestamp: 5000, // Very old timestamp
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);

        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.AttestationTooOld.selector, 5000, 8400));
        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), 8400);
    }

    /// @notice 13. Future market attestation exceeding clock skew is rejected.
    function test_Adversarial_FutureTimestamp_Rejected() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: 1,
            price: 2500 * WAD,
            timestamp: block.timestamp + 500, // Beyond 60s allowed skew
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);

        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.AttestationFutureTimestamp.selector, block.timestamp + 500, block.timestamp + 60));
        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), 1000);
    }

    /// @notice 14. Replayed market attestation signature is rejected.
    function test_Adversarial_ReplayedAttestation_Rejected() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: 1,
            price: 2500 * WAD,
            timestamp: block.timestamp,
            sourceId: keccak256("MKT"),
            nonce: 1
        });
        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, digest);

        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), block.timestamp - 100);

        // Replay attempt
        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.AttestationAlreadyUsed.selector, digest));
        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), block.timestamp - 100);
    }

    /// @notice 15. Repeated round finalization is rejected.
    function test_Adversarial_RepeatedFinalization_Rejected() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);
        _commit(rId, op2, OP_ID_2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("2"), 2);
        _commit(rId, op3, OP_ID_3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("3"), 3);
        _commit(rId, op4, OP_ID_4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("4"), 4);
        _commit(rId, op5, OP_ID_5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("5"), 5);

        _reveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);
        _reveal(rId, op2, LANE_2_HUBER, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("2"), 2);
        _reveal(rId, op3, LANE_3_JSD, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("3"), 3);
        _reveal(rId, op4, LANE_4_OU, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("4"), 4);
        _reveal(rId, op5, LANE_5_CUSUM, 0, 0, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("5"), 5);

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

        vm.warp(12000);
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(r, s, v));

        // Attempt second finalization
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.AlreadyFinalized.selector, rId));
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(r, s, v));
    }

    /// @notice 16. Finalization after expiry is rejected and marks round EXPIRED.
    function test_Adversarial_FinalizationAfterExpiry_Fails() public {
        uint256 rId = _createDefaultRound();

        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);
        _reveal(rId, op1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

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

        // Warp past finalizationDeadline (13600)
        vm.warp(14000);

        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.RoundExpired.selector, rId, 14000, 13600));
        manager.finalizeRoundWithAttestation(rId, att, abi.encodePacked(r, s, v));

        // Explicitly expire the round
        manager.expireRound(rId);
        AEGISVerificationManager.VerificationRound memory round = manager.getRound(rId);
        assertEq(uint8(round.state), uint8(AEGISVerificationManager.RoundState.EXPIRED));
    }

    /// @notice 17. Unauthorized price router updates revert.
    function test_Adversarial_PriceRouterUnauthorizedUpdate_Reverts() public {
        vm.prank(unauth);
        vm.expectRevert(abi.encodeWithSelector(AEGISPriceRouter.UnauthorizedCaller.selector, unauth));
        priceRouter.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);
    }

    /// @notice 18. Commit attempt after commit window closes is rejected.
    function test_Adversarial_CommitAfterCommitPhase_Reverts() public {
        uint256 rId = _createDefaultRound();
        bytes32 payloadHash = keccak256(abi.encode(OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1")));
        bytes32 commitHash = keccak256(abi.encode(block.chainid, address(manager), rId, op1, payloadHash, uint256(1)));

        // Warp past revealStart (11000)
        vm.warp(11001);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.WindowClosed.selector, "COMMIT", 11001, 11000));
        manager.commit(rId, commitHash);
    }

    /// @notice 19. Reveal attempt before reveal window opens is rejected.
    function test_Adversarial_RevealBeforeRevealStart_Reverts() public {
        uint256 rId = _createDefaultRound();
        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Warp to commit phase (10500), before revealStart (11000)
        vm.warp(10500);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.WindowNotOpen.selector, "REVEAL", 10500, 11000));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    /// @notice 20. Reveal attempt after reveal window closes is rejected.
    function test_Adversarial_RevealAfterRevealEnd_Reverts() public {
        uint256 rId = _createDefaultRound();
        _commit(rId, op1, OP_ID_1, LANE_1_KALMAN, 2500 * WAD, 10 * WAD, AggregatorLib.UncertaintyType.CI95_HALF_WIDTH, false, normalDiag, keccak256("1"), 1);

        // Warp past revealEnd (12000)
        vm.warp(12001);
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.WindowClosed.selector, "REVEAL", 12001, 12000));
        manager.reveal(
            AEGISVerificationManager.RevealParams({
                roundId: rId,
                laneId: LANE_1_KALMAN,
                price: 2500 * WAD,
                uncertaintyValue: 10 * WAD,
                uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
                isGated: false,
                diagPayload: normalDiag,
                evidenceHash: keccak256("1"),
                nonce: 1
            })
        );
    }

    /// @notice 21. Extreme uncertainty values (0 or massive 1e30) are safely bounded without division-by-zero or overflow.
    function test_Adversarial_ExtremeUncertaintyValues_HandledSafely() public pure {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](3);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operatorId: keccak256("OP1"),
            operator: address(0x1),
            price: 2500 * WAD,
            uncertaintyValue: 0, // Zero uncertainty
            uncertaintyType: AggregatorLib.UncertaintyType.ABSOLUTE_STD,
            isGated: false
        });
        subs[1] = AggregatorLib.OperatorPriceSubmission({
            operatorId: keccak256("OP2"),
            operator: address(0x2),
            price: 2500 * WAD,
            uncertaintyValue: 1e30, // Extremely large uncertainty
            uncertaintyType: AggregatorLib.UncertaintyType.ABSOLUTE_STD,
            isGated: false
        });
        subs[2] = AggregatorLib.OperatorPriceSubmission({
            operatorId: keccak256("OP3"),
            operator: address(0x3),
            price: 2500 * WAD,
            uncertaintyValue: 10 * WAD,
            uncertaintyType: AggregatorLib.UncertaintyType.ABSOLUTE_STD,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);
        assertEq(est.price, 2500 * WAD);
        assertGt(est.sigmaLane, 0);
    }

    /// @notice 22. EIP-712 signature generated with wrong verifyingContract address is rejected.
    function test_Adversarial_WrongVerifyingContract_SignatureRejected() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: 1,
            price: 2500 * WAD,
            timestamp: block.timestamp,
            sourceId: keccak256("MKT"),
            nonce: 1
        });

        // Compute digest using wrong contract address (e.g. address(0xDEAD))
        bytes32 wrongDomainSeparator = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("AEGISMarketAttestor")),
                keccak256(bytes("1")),
                block.chainid,
                address(0xDEAD)
            )
        );
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("MarketAttestation(bytes32 assetId,uint256 roundId,uint256 price,uint64 timestamp,bytes32 sourceId,uint256 nonce)"),
                att.assetId,
                att.roundId,
                att.price,
                att.timestamp,
                att.sourceId,
                att.nonce
            )
        );
        bytes32 forgedDigest = keccak256(abi.encodePacked("\x19\x01", wrongDomainSeparator, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(attestorPk, forgedDigest);

        // Verification must fail because recovered signer will not match authorized attestor
        vm.expectRevert();
        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), block.timestamp - 100);
    }
}

