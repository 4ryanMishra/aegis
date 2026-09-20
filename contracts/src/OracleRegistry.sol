// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IOracleAdapter} from "./interfaces/IOracleAdapter.sol";

/// @title OracleRegistry
/// @notice Manages registered oracle adapters, enabled states, and batch observation retrieval.
contract OracleRegistry {
    struct AdapterInfo {
        IOracleAdapter adapter;
        string name;
        bool enabled;
        bool isMultipli;
    }

    address public owner;
    AdapterInfo[] public adapters;
    mapping(address => bool) public isRegistered;

    event AdapterRegistered(address indexed adapter, string name, bool isMultipli);
    event AdapterStatusToggled(address indexed adapter, bool enabled);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerAdapter(address _adapter, string memory _name, bool _isMultipli) external onlyOwner {
        require(_adapter != address(0), "Invalid adapter address");
        require(!isRegistered[_adapter], "Already registered");

        adapters.push(AdapterInfo({
            adapter: IOracleAdapter(_adapter),
            name: _name,
            enabled: true,
            isMultipli: _isMultipli
        }));
        isRegistered[_adapter] = true;

        emit AdapterRegistered(_adapter, _name, _isMultipli);
    }

    function setAdapterStatus(uint256 index, bool enabled) external onlyOwner {
        require(index < adapters.length, "Index out of bounds");
        adapters[index].enabled = enabled;
        emit AdapterStatusToggled(address(adapters[index].adapter), enabled);
    }

    function getAdaptersCount() external view returns (uint256) {
        return adapters.length;
    }

    /// @notice Returns all valid and active observations for the specified asset
    function getAllObservations(bytes32 assetId) external view returns (
        IOracleAdapter.OracleObservation[] memory observations,
        IOracleAdapter.OracleObservation memory multipliObs,
        bool hasMultipli
    ) {
        uint256 total = adapters.length;
        IOracleAdapter.OracleObservation[] memory temp = new IOracleAdapter.OracleObservation[](total);
        uint256 validCount = 0;

        for (uint256 i = 0; i < total; i++) {
            if (!adapters[i].enabled) continue;

            IOracleAdapter.OracleObservation memory obs = adapters[i].adapter.getObservation(assetId);

            if (adapters[i].isMultipli) {
                multipliObs = obs;
                hasMultipli = obs.valid;
            } else if (obs.valid && obs.price > 0) {
                temp[validCount] = obs;
                validCount++;
            }
        }

        observations = new IOracleAdapter.OracleObservation[](validCount);
        for (uint256 j = 0; j < validCount; j++) {
            observations[j] = temp[j];
        }
    }
}
