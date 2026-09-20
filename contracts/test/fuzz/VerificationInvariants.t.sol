// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {FixedPointMath} from "../../src/libraries/FixedPointMath.sol";
import {AggregatorLib} from "../../src/libraries/AggregatorLib.sol";
import {AEGISDecisionEngine} from "../../src/AEGISDecisionEngine.sol";
import {AEGISEvidenceEngine} from "../../src/AEGISEvidenceEngine.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";

contract VerificationInvariantsTest is Test {
    using FixedPointMath for uint256;

    AEGISDecisionEngine decisionEngine;
    AEGISPriceRouter priceRouter;
    MarketAttestor marketAttestor;

    address owner = address(0xAA1);
    address caller = address(0xBB2);
    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    function setUp() public {
        vm.startPrank(owner);
        decisionEngine = new AEGISDecisionEngine(owner);
        priceRouter = new AEGISPriceRouter(owner);
        priceRouter.setVerificationManager(caller);
        priceRouter.setAssetMaxStaleness(assetId, 3600);
        marketAttestor = new MarketAttestor(owner);
        vm.stopPrank();
        vm.warp(10000);
    }

    /// @notice Invariant: Relative deviation is 0 for identical prices and correctly bounded for positive prices.
    function testFuzz_FixedPointMath_RelativeDeviation(uint128 p1, uint128 p2) public pure {
        vm.assume(p1 > 1e12 && p1 < 1e30);
        vm.assume(p2 > 1e12 && p2 < 1e30);

        uint256 dev = FixedPointMath.relativeDeviationBps(p1, p2);
        uint256 diff = p1 > p2 ? uint256(p1 - p2) : uint256(p2 - p1);
        uint256 minVal = p1 < p2 ? uint256(p1) : uint256(p2);
        if (p1 == p2 || (diff * 10000) < minVal) {
            assertEq(dev, 0);
        } else {
            assertTrue(dev > 0);
        }
    }

    /// @notice Invariant: Tier 1 within-lane aggregated price is strictly bounded by [min(inputs), max(inputs)].
    function testFuzz_Tier1_AggregationBounded(uint128 price1, uint128 price2, uint128 price3) public pure {
        vm.assume(price1 > 1e12 && price1 < 1e28);
        vm.assume(price2 > 1e12 && price2 < 1e28);
        vm.assume(price3 > 1e12 && price3 < 1e28);

        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](3);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operatorId: bytes32(uint256(1)),
            operator: address(0x1),
            price: price1,
            uncertaintyValue: 1e10,
            uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
            isGated: false
        });
        subs[1] = AggregatorLib.OperatorPriceSubmission({
            operatorId: bytes32(uint256(2)),
            operator: address(0x2),
            price: price2,
            uncertaintyValue: 1e10,
            uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
            isGated: false
        });
        subs[2] = AggregatorLib.OperatorPriceSubmission({
            operatorId: bytes32(uint256(3)),
            operator: address(0x3),
            price: price3,
            uncertaintyValue: 1e10,
            uncertaintyType: AggregatorLib.UncertaintyType.CI95_HALF_WIDTH,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);

        uint128 minPrice = price1 < price2 ? (price1 < price3 ? price1 : price3) : (price2 < price3 ? price2 : price3);
        uint128 maxPrice = price1 > price2 ? (price1 > price3 ? price1 : price3) : (price2 > price3 ? price2 : price3);

        assertTrue(est.price >= minPrice);
        assertTrue(est.price <= maxPrice);
    }

    /// @notice Invariant: Tier 2 blended price P_DEC is strictly bounded by [min(P_K, P_H), max(P_K, P_H)].
    function testFuzz_Tier2_CrossLaneBounded(
        uint128 pKalman,
        uint64 sigmaKalman,
        uint128 pHuber,
        uint64 sigmaHuber
    ) public pure {
        vm.assume(pKalman > 1e12 && pKalman < 1e28);
        vm.assume(pHuber > 1e12 && pHuber < 1e28);
        vm.assume(sigmaKalman > 1e6 && sigmaKalman < 1e20);
        vm.assume(sigmaHuber > 1e6 && sigmaHuber < 1e20);

        AggregatorLib.CanonicalLaneEstimate memory kalman = AggregatorLib.CanonicalLaneEstimate({
            price: pKalman,
            sigmaLane: sigmaKalman,
            operatorCount: 1,
            isGated: false,
            isValid: true
        });
        AggregatorLib.CanonicalLaneEstimate memory huber = AggregatorLib.CanonicalLaneEstimate({
            price: pHuber,
            sigmaLane: sigmaHuber,
            operatorCount: 1,
            isGated: false,
            isValid: true
        });

        AggregatorLib.Tier2AggregationResult memory res = AggregatorLib.synthesizeTier2(kalman, huber);
        assertTrue(res.success);

        uint128 minP = pKalman < pHuber ? pKalman : pHuber;
        uint128 maxP = pKalman > pHuber ? pKalman : pHuber;

        assertTrue(res.pDec >= minP);
        assertTrue(res.pDec <= maxP);
    }

    /// @notice Invariant: Decision Engine protective haircut never inflates asset price.
    function testFuzz_DecisionEngine_HaircutNeverInflates(
        uint128 pOsm,
        uint128 pDec,
        uint128 pMarket
    ) public {
        vm.assume(pOsm > 1e12 && pOsm < 1e28);
        vm.assume(pDec > 1e12 && pDec < 1e28);
        vm.assume(pMarket > 1e12 && pMarket < 1e28);

        AEGISEvidenceEngine.EvidenceRecord memory ev = AEGISEvidenceEngine.EvidenceRecord({
            devOsmMarketBps: FixedPointMath.relativeDeviationBps(pOsm, pMarket),
            devDecMarketBps: FixedPointMath.relativeDeviationBps(pDec, pMarket),
            devOsmDecBps: FixedPointMath.relativeDeviationBps(pOsm, pDec),
            anomalyBitmask: 0,
            anomalyCount: 0,
            hasHighDislocation: false,
            hasExtremeDislocation: false
        });

        AEGISDecisionEngine.DecisionResult memory res = decisionEngine.executeDecision(
            assetId,
            1,
            pOsm,
            pDec,
            pMarket,
            20,
            ev
        );

        if (res.oracleStatus != IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER) {
            uint128 maxInput = pOsm > pDec ? (pOsm > pMarket ? pOsm : pMarket) : (pDec > pMarket ? pDec : pMarket);
            assertTrue(res.pFinal <= maxInput);
        } else {
            assertEq(res.pFinal, 0);
        }
    }

    /// @notice Invariant: Price Router strictly enforces staleness window and rejects reads past expiry.
    function testFuzz_PriceRouter_Staleness(uint32 warpSeconds) public {
        vm.assume(warpSeconds < 100000);

        vm.prank(caller);
        priceRouter.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);

        vm.warp(block.timestamp + warpSeconds);

        if (warpSeconds <= 3600) {
            (uint256 p,,) = priceRouter.getPrice(assetId);
            assertEq(p, 2500 * WAD);
        } else {
            vm.expectRevert();
            priceRouter.getPrice(assetId);
        }
    }

    /// @notice Invariant: Market attestations signed by unauthorized keys always revert.
    function testFuzz_MarketAttestor_UnauthorizedSigner(uint256 unauthorizedPk, uint128 price) public {
        vm.assume(unauthorizedPk > 0 && unauthorizedPk < type(uint128).max);
        vm.assume(price > 1e12 && price < 1e28);

        address unauthorizedAddress = vm.addr(unauthorizedPk);
        vm.assume(unauthorizedAddress != owner);

        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: 1,
            price: price,
            timestamp: block.timestamp,
            sourceId: keccak256("TEST"),
            nonce: 1
        });

        bytes32 digest = marketAttestor.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(unauthorizedPk, digest);

        vm.expectRevert();
        marketAttestor.verifyAttestation(att, abi.encodePacked(r, s, v), block.timestamp - 300);
    }
}
