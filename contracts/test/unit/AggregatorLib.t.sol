// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {AggregatorLib} from "../../src/libraries/AggregatorLib.sol";
import {FixedPointMath} from "../../src/libraries/FixedPointMath.sol";

contract AggregatorLibTest is Test {
    using FixedPointMath for uint256;

    uint256 constant WAD = 1e18;

    function test_Tier1_SingleOperator() public pure {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](1);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x1),
            price: 100 * WAD,
            uncertaintyLower: 98 * WAD,
            uncertaintyUpper: 102 * WAD,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);
        assertEq(est.price, 100 * WAD);
        assertTrue(est.isValid);
        assertFalse(est.isGated);
        assertEq(est.operatorCount, 1);
        // CI width = 4 WAD, sigma = (4 * 100) / 392 = 1.02 WAD
        // IQR for n=1 is 0
        assertApproxEqAbs(est.sigmaLane, 1020408163265306122, 1e12);
    }

    function test_Tier1_ThreeOperators_MedianAndDispersion() public pure {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](3);
        // Operator 1: 100
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x1),
            price: 100 * WAD,
            uncertaintyLower: 99 * WAD,
            uncertaintyUpper: 101 * WAD,
            isGated: false
        });
        // Operator 2: 102 (outlier)
        subs[1] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x2),
            price: 102 * WAD,
            uncertaintyLower: 100 * WAD,
            uncertaintyUpper: 104 * WAD,
            isGated: false
        });
        // Operator 3: 99
        subs[2] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x3),
            price: 99 * WAD,
            uncertaintyLower: 98 * WAD,
            uncertaintyUpper: 100 * WAD,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);
        // Median of [99, 100, 102] is 100
        assertEq(est.price, 100 * WAD);
        assertEq(est.operatorCount, 3);
        // Range for n=3 is 102 - 99 = 3 WAD
        // sigmaLane = medianSigma + range
        assertTrue(est.sigmaLane > 3 * WAD);
    }

    function test_Tier1_GatingConsensus() public pure {
        AggregatorLib.OperatorPriceSubmission[] memory subs = new AggregatorLib.OperatorPriceSubmission[](3);
        subs[0] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x1),
            price: 100 * WAD,
            uncertaintyLower: 99 * WAD,
            uncertaintyUpper: 101 * WAD,
            isGated: true
        });
        subs[1] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x2),
            price: 101 * WAD,
            uncertaintyLower: 100 * WAD,
            uncertaintyUpper: 102 * WAD,
            isGated: true
        });
        subs[2] = AggregatorLib.OperatorPriceSubmission({
            operator: address(0x3),
            price: 100 * WAD,
            uncertaintyLower: 99 * WAD,
            uncertaintyUpper: 101 * WAD,
            isGated: false
        });

        AggregatorLib.CanonicalLaneEstimate memory est = AggregatorLib.aggregateLaneTier1(subs);
        // 2 of 3 are gated -> canonically gated
        assertTrue(est.isGated);
    }

    function test_Tier2_DualLane_InverseVarianceBlend() public pure {
        // Kalman: $100, sigma = 1 WAD
        AggregatorLib.CanonicalLaneEstimate memory kalman = AggregatorLib.CanonicalLaneEstimate({
            price: 100 * WAD,
            sigmaLane: 1 * WAD,
            operatorCount: 2,
            isGated: false,
            isValid: true
        });
        // Huber: $102, sigma = 1 WAD
        AggregatorLib.CanonicalLaneEstimate memory huber = AggregatorLib.CanonicalLaneEstimate({
            price: 102 * WAD,
            sigmaLane: 1 * WAD,
            operatorCount: 2,
            isGated: false,
            isValid: true
        });

        AggregatorLib.Tier2AggregationResult memory res = AggregatorLib.synthesizeTier2(kalman, huber);
        assertTrue(res.success);
        assertFalse(res.kalmanGated);
        assertFalse(res.isDegraded);
        // Equal variance -> 50/50 blend -> $101
        assertEq(res.pDec, 101 * WAD);
        assertEq(res.lambdaKalmanBps, 5000);
        // Dispersion |100 - 102| / 102 = 1.96% = ~196 BPS
        assertApproxEqAbs(res.validatorDispersionBps, 196, 5);
    }

    function test_Tier2_KalmanGated_HuberServesAlone() public pure {
        // Kalman: flash spike $150, but gated
        AggregatorLib.CanonicalLaneEstimate memory kalman = AggregatorLib.CanonicalLaneEstimate({
            price: 150 * WAD,
            sigmaLane: 1 * WAD,
            operatorCount: 2,
            isGated: true,
            isValid: true
        });
        // Huber: uncontaminated $100
        AggregatorLib.CanonicalLaneEstimate memory huber = AggregatorLib.CanonicalLaneEstimate({
            price: 100 * WAD,
            sigmaLane: 1 * WAD,
            operatorCount: 2,
            isGated: false,
            isValid: true
        });

        AggregatorLib.Tier2AggregationResult memory res = AggregatorLib.synthesizeTier2(kalman, huber);
        assertTrue(res.success);
        assertTrue(res.kalmanGated);
        // P_DEC must be uncontaminated Huber price alone ($100)
        assertEq(res.pDec, 100 * WAD);
        assertEq(res.lambdaKalmanBps, 0);
    }

    function test_Tier2_DegradedSingleLane() public pure {
        AggregatorLib.CanonicalLaneEstimate memory kalman = AggregatorLib.CanonicalLaneEstimate({
            price: 0,
            sigmaLane: 0,
            operatorCount: 0,
            isGated: false,
            isValid: false
        });
        AggregatorLib.CanonicalLaneEstimate memory huber = AggregatorLib.CanonicalLaneEstimate({
            price: 100 * WAD,
            sigmaLane: 1 * WAD,
            operatorCount: 1,
            isGated: false,
            isValid: true
        });

        AggregatorLib.Tier2AggregationResult memory res = AggregatorLib.synthesizeTier2(kalman, huber);
        assertTrue(res.success);
        assertTrue(res.isDegraded);
        assertEq(res.pDec, 100 * WAD);
    }

    function test_Tier2_QuorumFailure_NoPriceEstimators() public pure {
        AggregatorLib.CanonicalLaneEstimate memory kalman = AggregatorLib.CanonicalLaneEstimate({
            price: 0,
            sigmaLane: 0,
            operatorCount: 0,
            isGated: false,
            isValid: false
        });
        AggregatorLib.CanonicalLaneEstimate memory huber = AggregatorLib.CanonicalLaneEstimate({
            price: 0,
            sigmaLane: 0,
            operatorCount: 0,
            isGated: false,
            isValid: false
        });

        AggregatorLib.Tier2AggregationResult memory res = AggregatorLib.synthesizeTier2(kalman, huber);
        assertFalse(res.success);
        assertEq(res.pDec, 0);
    }
}
