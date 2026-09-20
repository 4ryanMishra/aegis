// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {AEGISPriceRouter} from "../../src/AEGISPriceRouter.sol";
import {IAEGISPriceFeed} from "../../src/interfaces/IAEGISPriceFeed.sol";

contract PriceRouterTest is Test {
    AEGISPriceRouter router;
    address owner = address(0xAA1);
    address manager = address(0xBB2);
    address unauthorized = address(0xDEAD);
    bytes32 assetId = bytes32("XAU/USD");
    uint256 constant WAD = 1e18;

    function setUp() public {
        vm.warp(10000);
        vm.prank(owner);
        router = new AEGISPriceRouter(owner);

        vm.prank(owner);
        router.setVerificationManager(manager);
    }

    function test_UpdatePrice_Success() public {
        vm.prank(manager);
        router.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);

        (uint256 price, IAEGISPriceFeed.OracleStatus status, uint256 timestamp) = router.getPrice(assetId);
        assertEq(price, 2500 * WAD);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS));
        assertEq(timestamp, 10000);
    }

    function test_RevertWhen_UnauthorizedCaller() public {
        vm.prank(unauthorized);
        vm.expectRevert(abi.encodeWithSelector(AEGISPriceRouter.UnauthorizedCaller.selector, unauthorized));
        router.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);
    }

    function test_RevertWhen_PriceStale() public {
        vm.prank(manager);
        router.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);

        // Advance time past default max staleness (7200s)
        vm.warp(block.timestamp + 7201);

        vm.expectRevert(abi.encodeWithSelector(AEGISPriceRouter.PriceStale.selector, assetId, 7201, 7200));
        router.getPrice(assetId);
    }

    function test_CustomAssetStaleness() public {
        vm.prank(owner);
        router.setAssetMaxStaleness(assetId, 3600); // 1 hour

        vm.prank(manager);
        router.updatePrice(assetId, 1, 2500 * WAD, IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS);

        vm.warp(block.timestamp + 3500);
        (uint256 price, , ) = router.getPrice(assetId);
        assertEq(price, 2500 * WAD);

        vm.warp(block.timestamp + 101);
        vm.expectRevert(abi.encodeWithSelector(AEGISPriceRouter.PriceStale.selector, assetId, 3601, 3600));
        router.getPrice(assetId);
    }

    function test_RevertWhen_NoPriceAvailable() public {
        bytes32 unknownAsset = bytes32("UNKNOWN");
        vm.expectRevert(abi.encodeWithSelector(AEGISPriceRouter.NoPriceAvailable.selector, unknownAsset));
        router.getPrice(unknownAsset);
    }

    function test_CircuitBreaker_AllowsZeroPrice() public {
        vm.prank(manager);
        router.updatePrice(assetId, 1, 0, IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER);

        (uint256 price, IAEGISPriceFeed.OracleStatus status, ) = router.getPrice(assetId);
        assertEq(price, 0);
        assertEq(uint8(status), uint8(IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER));
    }
}
