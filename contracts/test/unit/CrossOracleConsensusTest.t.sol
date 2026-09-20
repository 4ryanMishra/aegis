// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {IOracleAdapter} from "../../src/interfaces/IOracleAdapter.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {OracleRegistry} from "../../src/OracleRegistry.sol";
import {ConsensusEngine} from "../../src/ConsensusEngine.sol";
import {RiskDecisionEngine} from "../../src/RiskDecisionEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {MockRWAUSDProtocol} from "../../src/mocks/MockRWAUSDProtocol.sol";

import {
    MockChainlinkFeed,
    MockPythFeed,
    MockChronicleFeed,
    MockRedStoneFeed,
    MockSupraFeed,
    MockAPI3Feed,
    MockMultipliOSM
} from "../../src/mocks/MockOracleFeeds.sol";

import {ChainlinkAdapter} from "../../src/adapters/ChainlinkAdapter.sol";
import {PythAdapter} from "../../src/adapters/PythAdapter.sol";
import {ChronicleAdapter} from "../../src/adapters/ChronicleAdapter.sol";
import {RedStoneAdapter} from "../../src/adapters/RedStoneAdapter.sol";
import {SupraAdapter} from "../../src/adapters/SupraAdapter.sol";
import {API3Adapter} from "../../src/adapters/API3Adapter.sol";
import {MultipliAdapter} from "../../src/adapters/MultipliAdapter.sol";

contract CrossOracleConsensusTest is Test {
    OracleRegistry public registry;
    ConsensusEngine public consensusEngine;
    RiskDecisionEngine public decisionEngine;
    AEGISPriceRouter public router;
    MockRWAUSDProtocol public protocol;

    // Mock Feeds
    MockChainlinkFeed public clFeed;
    MockPythFeed public pythFeed;
    MockChronicleFeed public chronFeed;
    MockRedStoneFeed public rsFeed;
    MockSupraFeed public supraFeed;
    MockAPI3Feed public api3Feed;
    MockMultipliOSM public osmFeed;

    // Adapters
    ChainlinkAdapter public clAdapter;
    PythAdapter public pythAdapter;
    ChronicleAdapter public chronAdapter;
    RedStoneAdapter public rsAdapter;
    SupraAdapter public supraAdapter;
    API3Adapter public api3Adapter;
    MultipliAdapter public osmAdapter;

    bytes32 public constant ASSET_XAU = bytes32("XAU/USD");
    bytes32 public constant PYTH_FEED_ID = 0x765d2ba906da5188fbe76e5d80d9890f4a307351a99f3e0774113fae4e35befc;
    uint256 public constant SUPRA_PAIR_ID = 42;

    uint256 public constant WAD = 1e18;

    function setUp() public {
        registry = new OracleRegistry();
        consensusEngine = new ConsensusEngine();
        decisionEngine = new RiskDecisionEngine();
        router = new AEGISPriceRouter(address(this));
        router.setRegistry(address(registry));
        router.setConsensusEngine(address(consensusEngine));
        router.setDecisionEngine(address(decisionEngine));
        protocol = new MockRWAUSDProtocol(address(router), ASSET_XAU);

        // Deploy Mocks with baseline ~$4,320.00 / oz gold
        // 8 decimals for Chainlink & Supra
        clFeed = new MockChainlinkFeed(8, 432000000000); // 4320.00 * 1e8
        pythFeed = new MockPythFeed();
        pythFeed.setPrice(PYTH_FEED_ID, 432010000000, 15000000, -8, block.timestamp); // 4320.10, conf +-0.15
        chronFeed = new MockChronicleFeed(4320500000000000000000); // 4320.50 Wad
        rsFeed = new MockRedStoneFeed(4319800000000000000000); // 4319.80 Wad
        supraFeed = new MockSupraFeed();
        supraFeed.setPrice(SUPRA_PAIR_ID, 432020000000, block.timestamp, 8); // 4320.20
        api3Feed = new MockAPI3Feed(int224(4320300000000000000000)); // 4320.30 Wad
        osmFeed = new MockMultipliOSM(4320000000000000000000); // 4320.00 Wad

        // Deploy Adapters
        clAdapter = new ChainlinkAdapter(address(clFeed));
        pythAdapter = new PythAdapter(address(pythFeed), PYTH_FEED_ID);
        chronAdapter = new ChronicleAdapter(address(chronFeed));
        rsAdapter = new RedStoneAdapter(address(rsFeed));
        supraAdapter = new SupraAdapter(address(supraFeed), SUPRA_PAIR_ID);
        api3Adapter = new API3Adapter(address(api3Feed));
        osmAdapter = new MultipliAdapter(address(osmFeed));

        // Register in Registry
        registry.registerAdapter(address(clAdapter), "Chainlink", false);
        registry.registerAdapter(address(pythAdapter), "Pyth", false);
        registry.registerAdapter(address(chronAdapter), "Chronicle", false);
        registry.registerAdapter(address(rsAdapter), "RedStone", false);
        registry.registerAdapter(address(supraAdapter), "Supra", false);
        registry.registerAdapter(address(api3Adapter), "API3", false);
        registry.registerAdapter(address(osmAdapter), "Multipli", true);
    }

    function test_adapter_normalization() public view {
        IOracleAdapter.OracleObservation memory clObs = clAdapter.getObservation(ASSET_XAU);
        assertEq(clObs.price, 4320 * WAD, "Chainlink 18-dec WAD normalization mismatch");
        assertTrue(clObs.valid, "Chainlink observation should be valid");

        IOracleAdapter.OracleObservation memory pythObs = pythAdapter.getObservation(ASSET_XAU);
        assertEq(pythObs.price, 4320100000000000000000, "Pyth price normalization mismatch");
        assertTrue(pythObs.hasConfidence, "Pyth should support native confidence");
        assertGt(pythObs.confidence, 0, "Pyth confidence should be positive");
    }

    function test_scenario_1_normal_convergence() public view {
        (
            IOracleAdapter.OracleObservation[] memory obs,
            IOracleAdapter.OracleObservation memory multipliObs,
            bool hasMultipli
        ) = registry.getAllObservations(ASSET_XAU);

        assertEq(obs.length, 6, "Expected 6 external feeds");
        assertTrue(hasMultipli, "Expected valid Multipli feed");

        ConsensusEngine.ConsensusResult memory consensus = consensusEngine.computeConsensus(obs);
        assertTrue(consensus.hasStrongConsensus, "Should have strong consensus");
        assertEq(consensus.clusterSize, 6, "All 6 feeds should be in cluster");
        assertLt(consensus.clusterSpreadBps, 50, "Cluster spread should be < 0.5%");

        RiskDecisionEngine.DecisionOutput memory decision = decisionEngine.evaluateDecision(
            consensus,
            multipliObs,
            hasMultipli,
            0,
            false
        );

        assertEq(uint256(decision.state), uint256(RiskDecisionEngine.DecisionState.HEALTHY_CONSENSUS));
        assertEq(uint256(decision.oracleStatus), uint256(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));
        assertEq(decision.finalPrice, 4320 * WAD);
        assertFalse(decision.isConservativeApplied);
    }

    function test_scenario_2_multipli_divergence_hero_flow() public {
        // Market drops to ~$4,050.00 across external feeds while Multipli stays delayed @ $4,380.00
        clFeed.setPrice(405020000000, block.timestamp); // 4050.20
        pythFeed.setPrice(PYTH_FEED_ID, 405100000000, 12000000, -8, block.timestamp); // 4051.00
        chronFeed.setPrice(4049800000000000000000, block.timestamp); // 4049.80
        rsFeed.setPrice(4052100000000000000000, block.timestamp); // 4052.10
        supraFeed.setPrice(SUPRA_PAIR_ID, 405070000000, block.timestamp, 8); // 4050.70
        api3Feed.setPrice(int224(4051400000000000000000), uint32(block.timestamp)); // 4051.40
        osmFeed.setPrice(4380000000000000000000, true); // Stale Multipli @ 4380.00

        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = router.getPrice(ASSET_XAU);

        // Verification assertions
        assertEq(uint256(status), uint256(IAEGISPriceFeed.OracleStatus.EVIDENCE_OF_ABNORMAL_DEVIATION));
        // Conservative valuation chooses min(4380, 4050.85) = ~4050.85
        assertLt(finalPrice, 4053 * WAD);
        assertGt(finalPrice, 4049 * WAD);

        // Downstream protocol consequences:
        // User deposits 10 oz Gold
        address alice = address(0xA11CE);
        vm.startPrank(alice);
        protocol.depositCollateral(10 * WAD);

        // Under RESTRICTED state (50% LTV), max allowed borrow against 10 oz @ $4,050.85 is ~$20,254
        // Attempting to borrow $30,000 (which would have been allowed under stale $4,380 @ 80% = $35,040) must revert!
        vm.expectRevert();
        protocol.borrow(30000 * WAD);

        // Borrowing $20,000 succeeds
        (bool success, ) = protocol.borrow(20000 * WAD);
        assertTrue(success, "Borrow within 50% LTV should succeed");
        vm.stopPrank();
    }

    function test_scenario_3_single_oracle_outlier_rejection() public {
        // One rogue feed reports 9000.00 while other 5 agree @ ~4050.00
        clFeed.setPrice(405000000000, block.timestamp);
        pythFeed.setPrice(PYTH_FEED_ID, 405000000000, 10000000, -8, block.timestamp);
        chronFeed.setPrice(4050000000000000000000, block.timestamp);
        rsFeed.setPrice(9000000000000000000000, block.timestamp); // Outlier
        supraFeed.setPrice(SUPRA_PAIR_ID, 405000000000, block.timestamp, 8);
        api3Feed.setPrice(int224(4050000000000000000000), uint32(block.timestamp));
        osmFeed.setPrice(4050000000000000000000, true);

        (
            IOracleAdapter.OracleObservation[] memory obs,
            ,
        ) = registry.getAllObservations(ASSET_XAU);

        ConsensusEngine.ConsensusResult memory consensus = consensusEngine.computeConsensus(obs);
        assertTrue(consensus.hasStrongConsensus, "Consensus should be preserved");
        assertEq(consensus.clusterSize, 5, "5 honest feeds clustered");
        assertEq(consensus.consensusPrice, 4050 * WAD, "Outlier should not corrupt median");
    }

    function test_scenario_4_multi_oracle_disagreement_halt() public {
        // Group A (3 feeds @ 4050), Group B (3 feeds @ 4500)
        clFeed.setPrice(405000000000, block.timestamp);
        pythFeed.setPrice(PYTH_FEED_ID, 405000000000, 10000000, -8, block.timestamp);
        chronFeed.setPrice(4050000000000000000000, block.timestamp);

        rsFeed.setPrice(4500000000000000000000, block.timestamp);
        supraFeed.setPrice(SUPRA_PAIR_ID, 450000000000, block.timestamp, 8);
        api3Feed.setPrice(int224(4500000000000000000000), uint32(block.timestamp));
        osmFeed.setPrice(4275000000000000000000, true);

        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = router.getPrice(ASSET_XAU);
        assertEq(uint256(status), uint256(IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER));
        assertEq(finalPrice, 0, "No price should be fabricated during unresolvable disagreement");
    }

    function test_scenario_5_source_outage_graceful_degradation() public {
        // Disable 2 feeds in registry, remaining 4 feeds agree @ 4050
        registry.setAdapterStatus(0, false); // Disable Chainlink
        registry.setAdapterStatus(1, false); // Disable Pyth

        chronFeed.setPrice(4050000000000000000000, block.timestamp);
        rsFeed.setPrice(4050000000000000000000, block.timestamp);
        supraFeed.setPrice(SUPRA_PAIR_ID, 405000000000, block.timestamp, 8);
        api3Feed.setPrice(int224(4050000000000000000000), uint32(block.timestamp));
        osmFeed.setPrice(4050000000000000000000, true);

        (uint256 finalPrice, IAEGISPriceFeed.OracleStatus status, ) = router.getPrice(ASSET_XAU);
        assertEq(finalPrice, 4050 * WAD);
        assertEq(uint256(status), uint256(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));
    }
}
