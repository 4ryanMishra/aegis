// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title MarketAttestor
/// @notice Verifies signed EIP-712 terminal market price observations (P_MARKET).
/// @dev An authorized off-chain market observer signs an attestation payload at the end of the
/// verification window. On-chain contracts verify the cryptographic signature, freshness, and anti-replay.
contract MarketAttestor is EIP712, Ownable {
    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "MarketAttestation(bytes32 assetId,uint256 roundId,uint256 price,uint256 timestamp,bytes32 sourceId,uint256 nonce)"
    );

    struct MarketAttestation {
        bytes32 assetId;
        uint256 roundId;
        uint256 price;       // 18-decimal WAD
        uint256 timestamp;   // Observation timestamp
        bytes32 sourceId;    // Venue or aggregation source identifier
        uint256 nonce;       // Replay-prevention nonce
    }

    mapping(address => bool) public isAuthorizedAttestor;
    mapping(bytes32 => bool) public usedAttestations; // Tracks unique attestation hashes

    uint256 public allowedFutureSkew = 60; // 60 seconds clock skew allowance
    uint256 public maxStalenessWindow = 3600; // 1 hour maximum attestation age

    event MarketAttestationVerified(
        bytes32 indexed assetId,
        uint256 indexed roundId,
        uint256 price,
        address indexed attestor,
        bytes32 sourceId
    );
    event AttestorAuthorizationUpdated(address indexed attestor, bool isAuthorized);
    event TimingParametersUpdated(uint256 allowedFutureSkew, uint256 maxStalenessWindow);

    error UnauthorizedAttestor(address attestor);
    error AttestationAlreadyUsed(bytes32 attestationHash);
    error AttestationTooOld(uint256 timestamp, uint256 minAllowedTimestamp);
    error AttestationFutureTimestamp(uint256 timestamp, uint256 maxAllowedTimestamp);
    error ZeroPrice();

    constructor(address initialOwner) EIP712("AEGISMarketAttestor", "1") Ownable(initialOwner) {}

    /// @notice Authorizes or deauthorizes a market price attestor
    function setAttestorAuthorization(address attestor, bool isAuthorized) external onlyOwner {
        isAuthorizedAttestor[attestor] = isAuthorized;
        emit AttestorAuthorizationUpdated(attestor, isAuthorized);
    }

    /// @notice Configures clock skew and staleness limits
    function setTimingParameters(uint256 newFutureSkew, uint256 newMaxStaleness) external onlyOwner {
        allowedFutureSkew = newFutureSkew;
        maxStalenessWindow = newMaxStaleness;
        emit TimingParametersUpdated(newFutureSkew, newMaxStaleness);
    }

    /// @notice Verifies an EIP-712 market attestation against round constraints and signer authorization.
    /// @param attestation The attestation data payload
    /// @param signature The 65-byte ECDSA signature from the authorized attestor
    /// @param minValidTimestamp The lower bound on acceptable timestamp (e.g. round.revealEnd - maxSlack)
    /// @return attestor The recovered authorized signer address
    function verifyAttestation(
        MarketAttestation calldata attestation,
        bytes calldata signature,
        uint256 minValidTimestamp
    ) external returns (address attestor) {
        if (attestation.price == 0) revert ZeroPrice();

        // Freshness bounds: lower_bound <= timestamp <= block.timestamp + allowed_future_skew
        if (attestation.timestamp < minValidTimestamp) {
            revert AttestationTooOld(attestation.timestamp, minValidTimestamp);
        }
        if (attestation.timestamp > block.timestamp + allowedFutureSkew) {
            revert AttestationFutureTimestamp(attestation.timestamp, block.timestamp + allowedFutureSkew);
        }

        // Compute EIP-712 struct hash
        bytes32 structHash = keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                attestation.assetId,
                attestation.roundId,
                attestation.price,
                attestation.timestamp,
                attestation.sourceId,
                attestation.nonce
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        attestor = ECDSA.recover(digest, signature);

        if (!isAuthorizedAttestor[attestor]) {
            revert UnauthorizedAttestor(attestor);
        }

        // Replay defense
        if (usedAttestations[digest]) {
            revert AttestationAlreadyUsed(digest);
        }
        usedAttestations[digest] = true;

        emit MarketAttestationVerified(
            attestation.assetId,
            attestation.roundId,
            attestation.price,
            attestor,
            attestation.sourceId
        );
    }

    /// @notice Computes digest for external signing convenience
    function getAttestationDigest(MarketAttestation calldata attestation) external view returns (bytes32) {
        bytes32 structHash = keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                attestation.assetId,
                attestation.roundId,
                attestation.price,
                attestation.timestamp,
                attestation.sourceId,
                attestation.nonce
            )
        );
        return _hashTypedDataV4(structHash);
    }
}
