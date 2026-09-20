// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";

contract DecisionEngineTest is Test {
    AEGISDecisionEngine decisionEngine;
    address owner = address(0xAA1);
    bytes32 assetId = bytes32("XAU/USD");
    uint256 roundId = 1;
    uint256 constant WAD = 1e18;

    function setUp() public {
        vm.prank(owner);
        decisionEngine = new AEGISDecisionEngine(owner);
    }

    function test_Decision_HealthyConsensus() public {
        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: 20,
            devDecMarketBps: 15,
            devOsmDecBps: 25,
            anomalyBitmask: 0,
            anomalyCount: 0,
            hasHighDislocation: false,
            hasExtremeDislocation: false
        });

        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            roundId,
            100 * WAD, // OSM
            100 * WAD, // DEC
            100 * WAD, // MKT
            20,        // Dispersion BPS
            ev
        );

        assertEq(res.pFinal, 100 * WAD);
        assertEq(uint8(res.oracleStatus), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));
        assertEq(uint8(res.actionCode), uint8(AEGISDecisionEngine.ActionCode.ACCEPT_CONSENSUS));
        assertEq(res.effectiveHaircutBps, 0);
    }

    function test_Decision_DispersedUncertainty() public {
        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: 50,
            devDecMarketBps: 50,
            devOsmDecBps: 50,
            anomalyBitmask: 0,
            anomalyCount: 0,
            hasHighDislocation: false,
            hasExtremeDislocation: false
        });

        // Dispersion = 200 BPS >= 150 max allowed
        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            roundId,
            100 * WAD,
            102 * WAD,
            100 * WAD,
            200, // 200 BPS dispersion
            ev
        );

        // Conservative min(pDec, pMarket) = $100
        assertEq(res.pFinal, 100 * WAD);
        assertEq(uint8(res.oracleStatus), uint8(IAEGISPriceFeed.OracleStatus.DISPERSED_UNCERTAINTY));
        assertEq(uint8(res.actionCode), uint8(AEGISDecisionEngine.ActionCode.FREEZE_NEW_BORROWS));
    }

    function test_Decision_OsmStale_DecMarketAgree() public {
        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: 550, // Critical deviation
            devDecMarketBps: 20,  // Very close
            devOsmDecBps: 540,
            anomalyBitmask: 0,
            anomalyCount: 0,
            hasHighDislocation: true,
            hasExtremeDislocation: false
        });

        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            roundId,
            945 * 1e17, // OSM 94.5
            100 * WAD,  // DEC 100
            100 * WAD,  // MKT 100
            20,
            ev
        );

        assertEq(res.pFinal, 100 * WAD);
        assertEq(uint8(res.oracleStatus), uint8(IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY));
        assertEq(uint8(res.actionCode), uint8(AEGISDecisionEngine.ActionCode.RESTRICT_LTV));
    }

    function test_Decision_AbnormalDeviation_HaircutApplied() public {
        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: 550,
            devDecMarketBps: 550,
            devOsmDecBps: 100,
            anomalyBitmask: 0x0F,
            anomalyCount: 3, // Multiple diagnostic alerts
            hasHighDislocation: true,
            hasExtremeDislocation: false
        });

        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            roundId,
            945 * 1e17,
            100 * WAD,
            945 * 1e17,
            20,
            ev
        );

        // Base price is min(pDec, pMarket) = 94.5. 5% haircut = 94.5 * 0.95 = 89.775
        uint256 expected = (945 * 1e17 * 9500) / 10000;
        assertEq(res.pFinal, expected);
        assertEq(uint8(res.oracleStatus), uint8(IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION));
        assertEq(uint8(res.actionCode), uint8(AEGISDecisionEngine.ActionCode.RESTRICT_LTV));
        assertEq(res.effectiveHaircutBps, 500);
    }

    function test_Decision_ExtremeDislocation_CircuitBreaker() public {
        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: 1500,
            devDecMarketBps: 1200,
            devOsmDecBps: 1400,
            anomalyBitmask: 0xFF,
            anomalyCount: 4,
            hasHighDislocation: true,
            hasExtremeDislocation: true
        });

        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            roundId,
            80 * WAD,
            100 * WAD,
            120 * WAD,
            500,
            ev
        );

        assertEq(res.pFinal, 0);
        assertEq(uint8(res.oracleStatus), uint8(IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER));
        assertEq(uint8(res.actionCode), uint8(AEGISDecisionEngine.ActionCode.TRIGGER_CIRCUIT_BREAKER));
    }
}
