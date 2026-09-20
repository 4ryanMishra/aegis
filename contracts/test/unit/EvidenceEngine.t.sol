// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {
    AEGISEvidenceEngine,
    FLAG_DEV_OSM_MARKET_HIGH,
    FLAG_DEV_OSM_DEC_HIGH,
    FLAG_OU_JUMP
} from "../../src/AEGISEvidenceEngine.sol";

contract EvidenceEngineTest is Test {
    AEGISEvidenceEngine engine;
    address owner = address(0xAA1);
    bytes32 assetId = bytes32("XAU/USD");
    uint256 roundId = 1;
    uint256 constant WAD = 1e18;

    function setUp() public {
        vm.prank(owner);
        engine = new AEGISEvidenceEngine(owner);
    }

    function test_EvaluateEvidence_HealthyConsensus() public {
        // All feeds agree at $100
        AEGISEvidenceEngine.DiagnosticFlags memory diag = AEGISEvidenceEngine.DiagnosticFlags({
            kalmanGated: false,
            jsdDivergent: false,
            ouJumpCandidate: false,
            cusumTripped: false,
            ouNotApplicable: false
        });

        AEGISEvidenceEngine.EvidenceRecord memory record = engine.evaluateEvidence(
            assetId,
            roundId,
            100 * WAD, // OSM
            100 * WAD, // DEC
            100 * WAD, // MARKET
            diag
        );

        assertEq(record.devOsmMarketBps, 0);
        assertEq(record.devDecMarketBps, 0);
        assertEq(record.devOsmDecBps, 0);
        assertEq(record.anomalyBitmask, 0);
        assertEq(record.anomalyCount, 0);
        assertFalse(record.hasHighDislocation);
        assertFalse(record.hasExtremeDislocation);
    }

    function test_EvaluateEvidence_OsmStale_DecMarketAgree() public {
        // OSM is stale at $90, while DEC and MARKET are at $100
        AEGISEvidenceEngine.DiagnosticFlags memory diag = AEGISEvidenceEngine.DiagnosticFlags({
            kalmanGated: false,
            jsdDivergent: false,
            ouJumpCandidate: false,
            cusumTripped: false,
            ouNotApplicable: false
        });

        AEGISEvidenceEngine.EvidenceRecord memory record = engine.evaluateEvidence(
            assetId,
            roundId,
            90 * WAD,  // OSM
            100 * WAD, // DEC
            100 * WAD, // MARKET
            diag
        );

        // |90 - 100| / 100 = 10% = 1000 BPS
        assertEq(record.devOsmMarketBps, 1000);
        assertEq(record.devDecMarketBps, 0);
        assertEq(record.devOsmDecBps, 1000);

        assertTrue(record.hasHighDislocation);
        assertTrue(record.hasExtremeDislocation);
        assertTrue((record.anomalyBitmask & FLAG_DEV_OSM_MARKET_HIGH) > 0);
        assertTrue((record.anomalyBitmask & FLAG_DEV_OSM_DEC_HIGH) > 0);
    }

    function test_EvaluateEvidence_DiagnosticsAndNotApplicableOU() public {
        // Case A: OU Jump candidate active and applicable
        AEGISEvidenceEngine.DiagnosticFlags memory diag1 = AEGISEvidenceEngine.DiagnosticFlags({
            kalmanGated: true,
            jsdDivergent: true,
            ouJumpCandidate: true,
            cusumTripped: true,
            ouNotApplicable: false
        });

        AEGISEvidenceEngine.EvidenceRecord memory rec1 = engine.evaluateEvidence(
            assetId,
            roundId,
            100 * WAD,
            100 * WAD,
            100 * WAD,
            diag1
        );

        assertEq(rec1.anomalyCount, 4);
        assertTrue((rec1.anomalyBitmask & FLAG_OU_JUMP) > 0);

        // Case B: OU flagged NOT_APPLICABLE for asset
        AEGISEvidenceEngine.DiagnosticFlags memory diag2 = AEGISEvidenceEngine.DiagnosticFlags({
            kalmanGated: false,
            jsdDivergent: false,
            ouJumpCandidate: true,
            cusumTripped: false,
            ouNotApplicable: true
        });

        AEGISEvidenceEngine.EvidenceRecord memory rec2 = engine.evaluateEvidence(
            assetId,
            roundId,
            100 * WAD,
            100 * WAD,
            100 * WAD,
            diag2
        );

        assertEq(rec2.anomalyCount, 0);
        assertEq(rec2.anomalyBitmask & FLAG_OU_JUMP, 0);
    }
}
