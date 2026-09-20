// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {
    AEGISVerificationManager,
    LANE_1_KALMAN,
    LANE_2_HUBER
} from "../../src/AEGISVerificationManager.sol";
import {ValidatorRegistry} from "../../src/ValidatorRegistry.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {MockOSM} from "../mocks/MockOSM.sol";

contract CommitRevealTest is Test {
    ValidatorRegistry registry;
    MarketAttestor marketAttestor;
    AEGISEvidenceEngine evidenceEngine;
    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    AEGISVerificationManager manager;
    MockOSM mockOsm;

    address owner = address(0xAA1);
    uint256 op1Pk = 0x101;
    address op1;
    uint256 op2Pk = 0x102;
    address op2;
    address unauthorized = address(0xDEAD);

    bytes32 assetId = bytes32("XAU/USD");
    uint256 roundId;
    uint256 constant WAD = 1e18;

    AEGISVerificationManager.DiagnosticPayload emptyDiag = AEGISVerificationManager.DiagnosticPayload({
        jsdDivergent: false,
        ouJumpCandidate: false,
        cusumTripped: false
    });

    function setUp() public {
        vm.warp(10000);
        op1 = vm.addr(op1Pk);
        op2 = vm.addr(op2Pk);

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

        // Register op1 for Lane 1 Kalman, op2 for Lane 2 Huber
        registry.registerValidator(op1, LANE_1_KALMAN, keccak256("K1"));
        registry.registerValidator(op2, LANE_2_HUBER, keccak256("H1"));

        mockOsm = new MockOSM(2500 * WAD);

        // Open round: commit [10000, 11000), reveal [11000, 12000), deadline 13600
        AEGISVerificationManager.RoundTiming memory timing = AEGISVerificationManager.RoundTiming({
            commitStart: 10000,
            revealStart: 11000,
            revealEnd: 12000,
            finalizationDeadline: 13600
        });
        AEGISVerificationManager.QuorumConfig memory qConfig = AEGISVerificationManager.QuorumConfig({
            minTotalQuorum: 2,
            minDistinctOperators: 2,
            minDistinctApplicableLanes: 2,
            ouNotApplicable: false
        });

        roundId = manager.createRound(assetId, address(mockOsm), timing, qConfig);
        vm.stopPrank();
    }

    function _computeCommitHash(
        uint256 rId,
        address operator,
        uint8 laneId,
        uint256 price,
        uint256 uLow,
        uint256 uHigh,
        bool isGated,
        bytes32 evHash,
        uint256 nonce
    ) internal view returns (bytes32) {
        bytes32 payloadHash = keccak256(
            abi.encode(laneId, price, uLow, uHigh, isGated, emptyDiag, evHash)
        );
        return keccak256(
            abi.encode(block.chainid, address(manager), rId, operator, payloadHash, nonce)
        );
    }

    function test_CommitAndReveal_Success() public {
        uint256 price = 2500 * WAD;
        uint256 uLow = 2490 * WAD;
        uint256 uHigh = 2510 * WAD;
        bytes32 evHash = keccak256("OFFCHAIN_KALMAN_TELEMETRY");
        uint256 nonce = 42;

        bytes32 commitHash = _computeCommitHash(
            roundId,
            op1,
            LANE_1_KALMAN,
            price,
            uLow,
            uHigh,
            false,
            evHash,
            nonce
        );

        // Commit during commit window
        vm.prank(op1);
        manager.commit(roundId, commitHash);

        // Warp to reveal window
        vm.warp(11500);

        // Reveal
        vm.prank(op1);
        manager.reveal(
            roundId,
            LANE_1_KALMAN,
            price,
            uLow,
            uHigh,
            false,
            emptyDiag,
            evHash,
            nonce
        );

        assertEq(manager.getRoundRevealsCount(roundId), 1);
        assertTrue(manager.hasRevealed(roundId, op1));
    }

    function test_RevertWhen_CommitmentMismatch_WrongNonce() public {
        uint256 price = 2500 * WAD;
        bytes32 evHash = keccak256("TELEMETRY");
        uint256 realNonce = 42;

        bytes32 commitHash = _computeCommitHash(
            roundId,
            op1,
            LANE_1_KALMAN,
            price,
            2490 * WAD,
            2510 * WAD,
            false,
            evHash,
            realNonce
        );

        vm.prank(op1);
        manager.commit(roundId, commitHash);

        vm.warp(11500);

        // Attempt reveal with wrong nonce
        vm.prank(op1);
        vm.expectRevert(AEGISVerificationManager.CommitmentMismatch.selector);
        manager.reveal(
            roundId,
            LANE_1_KALMAN,
            price,
            2490 * WAD,
            2510 * WAD,
            false,
            emptyDiag,
            evHash,
            999 // Wrong nonce!
        );
    }

    function test_RevertWhen_RevealTwice() public {
        uint256 price = 2500 * WAD;
        bytes32 evHash = keccak256("TELEMETRY");
        uint256 nonce = 42;

        bytes32 commitHash = _computeCommitHash(
            roundId,
            op1,
            LANE_1_KALMAN,
            price,
            2490 * WAD,
            2510 * WAD,
            false,
            evHash,
            nonce
        );

        vm.prank(op1);
        manager.commit(roundId, commitHash);

        vm.warp(11500);

        vm.prank(op1);
        manager.reveal(roundId, LANE_1_KALMAN, price, 2490 * WAD, 2510 * WAD, false, emptyDiag, evHash, nonce);

        // Second reveal
        vm.prank(op1);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.AlreadyRevealed.selector, roundId, op1));
        manager.reveal(roundId, LANE_1_KALMAN, price, 2490 * WAD, 2510 * WAD, false, emptyDiag, evHash, nonce);
    }

    function test_RevertWhen_EarlyOrLateReveal() public {
        uint256 price = 2500 * WAD;
        bytes32 evHash = keccak256("TELEMETRY");
        uint256 nonce = 42;

        bytes32 commitHash = _computeCommitHash(
            roundId,
            op1,
            LANE_1_KALMAN,
            price,
            2490 * WAD,
            2510 * WAD,
            false,
            evHash,
            nonce
        );

        vm.prank(op1);
        manager.commit(roundId, commitHash);

        // Early reveal at t=10500 (reveal starts at 11000)
        vm.prank(op1);
        vm.expectRevert();
        manager.reveal(roundId, LANE_1_KALMAN, price, 2490 * WAD, 2510 * WAD, false, emptyDiag, evHash, nonce);

        // Late reveal at t=12001 (reveal ends at 12000)
        vm.warp(12001);
        vm.prank(op1);
        vm.expectRevert();
        manager.reveal(roundId, LANE_1_KALMAN, price, 2490 * WAD, 2510 * WAD, false, emptyDiag, evHash, nonce);
    }

    function test_RevertWhen_UnauthorizedValidatorCommits() public {
        bytes32 dummyHash = keccak256("DUMMY");
        vm.prank(unauthorized);
        vm.expectRevert(abi.encodeWithSelector(AEGISVerificationManager.UnauthorizedValidator.selector, unauthorized));
        manager.commit(roundId, dummyHash);
    }
}
