// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {MarketAttestor} from "../../src/MarketAttestor.sol";

contract MarketAttestorTest is Test {
    MarketAttestor attestorContract;
    address owner = address(0xAA1);
    uint256 attestorPk = 0xA11CE;
    address attestor;
    uint256 unauthorizedPk = 0xBAD;
    address unauthorized;

    bytes32 assetId = bytes32("XAU/USD");
    uint256 roundId = 1;
    uint256 price = 2500 * 1e18;
    bytes32 sourceId = keccak256("BINANCE+COINBASE");

    function setUp() public {
        vm.warp(10000);
        attestor = vm.addr(attestorPk);
        unauthorized = vm.addr(unauthorizedPk);

        vm.prank(owner);
        attestorContract = new MarketAttestor(owner);

        vm.prank(owner);
        attestorContract.setAttestorAuthorization(attestor, true);
    }

    function _signAttestation(
        uint256 pk,
        MarketAttestor.MarketAttestation memory att
    ) internal view returns (bytes memory) {
        bytes32 digest = attestorContract.getAttestationDigest(att);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function test_VerifyAttestation_Success() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: price,
            timestamp: block.timestamp,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(attestorPk, att);
        address recovered = attestorContract.verifyAttestation(att, sig, block.timestamp - 300);
        assertEq(recovered, attestor);
    }

    function test_RevertWhen_UnauthorizedAttestor() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: price,
            timestamp: block.timestamp,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(unauthorizedPk, att);
        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.UnauthorizedAttestor.selector, unauthorized));
        attestorContract.verifyAttestation(att, sig, block.timestamp - 300);
    }

    function test_RevertWhen_AttestationReplayed() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: price,
            timestamp: block.timestamp,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(attestorPk, att);
        attestorContract.verifyAttestation(att, sig, block.timestamp - 300);

        // Second call with identical payload reverts
        bytes32 digest = attestorContract.getAttestationDigest(att);
        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.AttestationAlreadyUsed.selector, digest));
        attestorContract.verifyAttestation(att, sig, block.timestamp - 300);
    }

    function test_RevertWhen_TimestampTooOld() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: price,
            timestamp: 1000,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(attestorPk, att);
        vm.expectRevert(abi.encodeWithSelector(MarketAttestor.AttestationTooOld.selector, 1000, 2000));
        attestorContract.verifyAttestation(att, sig, 2000);
    }

    function test_RevertWhen_TimestampInFuture() public {
        uint256 futureTs = block.timestamp + 120; // Skew limit is 60s
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: price,
            timestamp: futureTs,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(attestorPk, att);
        vm.expectRevert();
        attestorContract.verifyAttestation(att, sig, block.timestamp - 100);
    }

    function test_RevertWhen_ZeroPrice() public {
        MarketAttestor.MarketAttestation memory att = MarketAttestor.MarketAttestation({
            assetId: assetId,
            roundId: roundId,
            price: 0,
            timestamp: block.timestamp,
            sourceId: sourceId,
            nonce: 1
        });

        bytes memory sig = _signAttestation(attestorPk, att);
        vm.expectRevert(MarketAttestor.ZeroPrice.selector);
        attestorContract.verifyAttestation(att, sig, block.timestamp - 100);
    }
}
