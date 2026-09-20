// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {console} from "forge-std/console.sol";
import {ValidatorRegistry} from "../src/ValidatorRegistry.sol";
import {MarketAttestor} from "../src/MarketAttestor.sol";
import {AEGISEvidenceEngine} from "../src/AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "../src/AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "../src/AEGISPriceRouter.sol";
import {AEGISVerificationManager} from "../src/AEGISVerificationManager.sol";
import {MockRWAUSDProtocol} from "../src/mocks/MockRWAUSDProtocol.sol";

/// @title DeployAEGIS
/// @notice Production-grade deployment script for AEGIS verification layer on EVM testnets.
/// @dev Ingests configuration via environment variables:
/// - PRIVATE_KEY / DEPLOYER_PRIVATE_KEY: Deployer private key
/// - INITIAL_OWNER: Contract governance owner (defaults to deployer)
/// - ATTESTOR_ADDRESS: Authorized market observer signer address
/// - ASSET_ID: Target asset identifier (defaults to "XAU/USD")
contract DeployAEGIS is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envOr("PRIVATE_KEY", uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80));
        address deployer = vm.addr(deployerPrivateKey);
        address owner = vm.envOr("INITIAL_OWNER", deployer);
        address attestor = vm.envOr("ATTESTOR_ADDRESS", deployer);
        bytes32 assetId = vm.envOr("ASSET_ID", bytes32("XAU/USD"));

        console.log("=== Deploying AEGIS Verification Engine ===");
        console.log("Deployer:", deployer);
        console.log("Governance Owner:", owner);
        console.log("Market Attestor:", attestor);
        console.log("Asset ID:", vm.toString(assetId));

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy Core Infrastructure
        ValidatorRegistry registry = new ValidatorRegistry(owner);
        console.log("ValidatorRegistry deployed at:", address(registry));

        MarketAttestor marketAttestor = new MarketAttestor(owner);
        console.log("MarketAttestor deployed at:", address(marketAttestor));

        AEGISEvidenceEngine evidenceEngine = new AEGISEvidenceEngine(owner);
        console.log("AEGISEvidenceEngine deployed at:", address(evidenceEngine));

        AEGISDecisionEngine decisionEngine = new AEGISDecisionEngine(owner);
        console.log("AEGISDecisionEngine deployed at:", address(decisionEngine));

        AEGISPriceRouter priceRouter = new AEGISPriceRouter(owner);
        console.log("AEGISPriceRouter deployed at:", address(priceRouter));

        // 2. Deploy Coordinator Manager
        AEGISVerificationManager manager = new AEGISVerificationManager(
            owner,
            address(registry),
            address(marketAttestor),
            address(evidenceEngine),
            address(decisionEngine),
            address(priceRouter)
        );
        console.log("AEGISVerificationManager deployed at:", address(manager));

        // 3. Configure Inter-Contract Authorizations
        priceRouter.setVerificationManager(address(manager));
        marketAttestor.setAttestorAuthorization(attestor, true);

        // 4. Deploy Mock Downstream Consumer
        MockRWAUSDProtocol protocol = new MockRWAUSDProtocol(address(priceRouter), assetId);
        console.log("MockRWAUSDProtocol deployed at:", address(protocol));

        vm.stopBroadcast();

        console.log("=== AEGIS Deployment Completed Successfully ===");
    }
}
