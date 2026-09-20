// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {ValidatorRegistry, LANE_1_KALMAN, LANE_2_HUBER, LANE_3_JSD, LANE_4_OU, LANE_5_CUSUM} from "./ValidatorRegistry.sol";
import {AggregatorLib} from "./libraries/AggregatorLib.sol";
import {FixedPointMath} from "./libraries/FixedPointMath.sol";
import {MarketAttestor} from "./MarketAttestor.sol";
import {AEGISEvidenceEngine} from "./AEGISEvidenceEngine.sol";
import {AEGISDecisionEngine} from "./AEGISDecisionEngine.sol";
import {AEGISPriceRouter} from "./AEGISPriceRouter.sol";
import {IAEGISPriceFeed} from "./interfaces/IAEGISPriceFeed.sol";
import {IOSM} from "./interfaces/IOSM.sol";

/// @title AEGISVerificationManager
/// @notice Core coordinator state machine managing verification rounds, commit-reveal,
/// multi-operator aggregation, market attestation ingestion, and decision routing.
/// @dev ZERO DOUBLE-DELAY ARCHITECTURE:
/// Rounds open at T0 concurrently with the existing 1-hour OSM delay. Validators collect evidence,
/// commit, and reveal during the delay. At T1 (when the OSM matures), keeper finalization executes
/// atomically with zero added latency.
contract AEGISVerificationManager is Ownable, ReentrancyGuard {
    using FixedPointMath for uint256;

    enum RoundState {
        UNINITIALIZED,
        ROUND_CREATED,
        COMMIT_OPEN,
        REVEAL_OPEN,
        AGGREGATED,
        MARKET_EVIDENCE_READY,
        DECISION_READY,
        OSM_READ_FAILED,
        INSUFFICIENT_QUORUM,
        MARKET_EVIDENCE_INVALID,
        EXPIRED,
        FINALIZED,
        DISPUTED
    }

    struct QuorumConfig {
        uint16 minTotalQuorum;             // Minimum total reveal count
        uint16 minDistinctOperators;       // Minimum distinct operatorId identities (not wallet addresses)
        uint16 minDistinctApplicableLanes; // Minimum distinct active/applicable methodology lanes (>=3)
        bool ouNotApplicable;              // True if OU is marked NOT_APPLICABLE for this asset
    }

    struct RoundTiming {
        uint64 commitStart;
        uint64 revealStart;
        uint64 revealEnd;
        uint64 finalizationDeadline;
    }

    struct VerificationRound {
        uint256 roundId;
        bytes32 assetId;
        address osmAddress;
        RoundTiming timing;
        QuorumConfig quorumConfig;
        RoundState state;
        uint256 pOsm;
        uint256 pDec;
        uint256 pMarket;
        uint256 pFinal;
        uint256 validatorDispersionBps;
        IAEGISPriceFeed.OracleStatus finalStatus;
        AEGISDecisionEngine.ActionCode actionCode;
        uint64 finalizedAt;
    }

    struct CommitmentRecord {
        bytes32 commitHash;
        bytes32 operatorId;
        uint8 laneId;
        uint64 commitTimestamp;
        bool exists;
    }

    struct ValidatorRevealRecord {
        bytes32 operatorId;      // Organizational operator identity
        address operator;        // Signing wallet address
        uint8 laneId;            // Methodology lane (1 to 5)
        uint256 price;           // 0 for diagnostic lanes
        uint256 uncertaintyValue;// Half-width or direct std dev in WAD
        AggregatorLib.UncertaintyType uncertaintyType; // Explicit uncertainty semantic
        bytes32 evidenceHash;    // keccak256 of off-chain rich telemetry
        uint64 timestamp;
        bool isGated;            // Kalman innovation gated
    }

    struct DiagnosticPayload {
        bool jsdDivergent;
        bool ouJumpCandidate;
        bool cusumTripped;
    }

    // Core Dependencies
    ValidatorRegistry public immutable validatorRegistry;
    MarketAttestor public immutable marketAttestor;
    AEGISEvidenceEngine public immutable evidenceEngine;
    AEGISDecisionEngine public immutable decisionEngine;
    AEGISPriceRouter public immutable priceRouter;

    // Round Storage
    uint256 public nextRoundId = 1;
    mapping(uint256 => VerificationRound) public rounds;
    mapping(uint256 => mapping(address => CommitmentRecord)) public commitments;
    mapping(uint256 => mapping(address => bool)) public hasRevealed;
    mapping(uint256 => mapping(uint8 => mapping(bytes32 => bool))) internal _laneOperatorRevealed;
    mapping(uint256 => ValidatorRevealRecord[]) internal _roundReveals;
    mapping(uint256 => mapping(uint8 => AggregatorLib.OperatorPriceSubmission[])) internal _lanePriceSubmissions;
    mapping(uint256 => mapping(uint8 => DiagnosticPayload[])) internal _laneDiagnosticPayloads;
    mapping(uint256 => AEGISEvidenceEngine.EvidenceRecord) public roundEvidence;

    // Events
    event RoundCreated(
        uint256 indexed roundId,
        bytes32 indexed assetId,
        address indexed osmAddress,
        uint64 commitStart,
        uint64 revealStart,
        uint64 revealEnd,
        uint64 finalizationDeadline
    );
    event CommitmentSubmitted(
        uint256 indexed roundId,
        address indexed operator,
        bytes32 indexed operatorId,
        uint8 laneId,
        bytes32 commitHash
    );
    event ValidatorRevealed(
        uint256 indexed roundId,
        address indexed operator,
        bytes32 indexed operatorId,
        uint8 laneId,
        uint256 price,
        bytes32 evidenceHash
    );
    event QuorumEvaluated(
        uint256 indexed roundId,
        bool quorumMet,
        uint256 totalReveals,
        uint256 distinctOperators,
        uint256 distinctApplicableLanes
    );
    event RoundAggregated(uint256 indexed roundId, uint256 pDec, uint256 dispersionBps, bool kalmanGated);
    event MarketEvidenceAttached(uint256 indexed roundId, uint256 pMarket, address indexed attestor);
    event OsmReadCompleted(uint256 indexed roundId, uint256 pOsm);
    event OsmReadFailed(uint256 indexed roundId, string reason);
    event RoundFinalized(
        uint256 indexed roundId,
        bytes32 indexed assetId,
        uint256 pFinal,
        IAEGISPriceFeed.OracleStatus status,
        AEGISDecisionEngine.ActionCode actionCode
    );
    event RoundStateChanged(uint256 indexed roundId, RoundState previousState, RoundState newState);

    // Errors
    error InvalidTiming();
    error InvalidQuorumConfig();
    error RoundDoesNotExist(uint256 roundId);
    error InvalidState(RoundState current, RoundState required);
    error UnauthorizedValidator(address caller);
    error IdentityOrLaneMutated(bytes32 committedOpId, bytes32 currentOpId, uint8 committedLane, uint8 currentLane);
    error DuplicateOperatorInLane(bytes32 operatorId, uint8 laneId);
    error CommitmentAlreadyExists(uint256 roundId, address operator);
    error CommitmentDoesNotExist(uint256 roundId, address operator);
    error AlreadyRevealed(uint256 roundId, address operator);
    error CommitmentMismatch();
    error WindowNotOpen(string windowName, uint256 currentTimestamp, uint256 boundaryTimestamp);
    error WindowClosed(string windowName, uint256 currentTimestamp, uint256 boundaryTimestamp);
    error RoundExpired(uint256 roundId, uint256 currentTimestamp, uint256 deadline);
    error AlreadyFinalized(uint256 roundId);

    constructor(
        address initialOwner,
        address _validatorRegistry,
        address _marketAttestor,
        address _evidenceEngine,
        address _decisionEngine,
        address _priceRouter
    ) Ownable(initialOwner) {
        validatorRegistry = ValidatorRegistry(_validatorRegistry);
        marketAttestor = MarketAttestor(_marketAttestor);
        evidenceEngine = AEGISEvidenceEngine(_evidenceEngine);
        decisionEngine = AEGISDecisionEngine(_decisionEngine);
        priceRouter = AEGISPriceRouter(_priceRouter);
    }

    /// @notice Opens a new AEGIS verification round running concurrently with the existing OSM delay.
    function createRound(
        bytes32 assetId,
        address osmAddress,
        RoundTiming calldata timing,
        QuorumConfig calldata quorumConfig
    ) external returns (uint256 roundId) {
        if (
            timing.commitStart >= timing.revealStart ||
            timing.revealStart >= timing.revealEnd ||
            timing.revealEnd >= timing.finalizationDeadline
        ) {
            revert InvalidTiming();
        }
        if (
            quorumConfig.minTotalQuorum == 0 ||
            quorumConfig.minDistinctOperators == 0 ||
            quorumConfig.minDistinctApplicableLanes == 0
        ) {
            revert InvalidQuorumConfig();
        }

        roundId = nextRoundId++;
        rounds[roundId] = VerificationRound({
            roundId: roundId,
            assetId: assetId,
            osmAddress: osmAddress,
            timing: timing,
            quorumConfig: quorumConfig,
            state: RoundState.ROUND_CREATED,
            pOsm: 0,
            pDec: 0,
            pMarket: 0,
            pFinal: 0,
            validatorDispersionBps: 0,
            finalStatus: IAEGISPriceFeed.OracleStatus.HEALTHY_CONSENSUS,
            actionCode: AEGISDecisionEngine.ActionCode.ACCEPT_CONSENSUS,
            finalizedAt: 0
        });

        emit RoundCreated(
            roundId,
            assetId,
            osmAddress,
            timing.commitStart,
            timing.revealStart,
            timing.revealEnd,
            timing.finalizationDeadline
        );
    }

    /// @notice Submits a cryptographic commitment during the commit window.
    /// @dev Snapshots operatorId and laneId to guarantee round consistency.
    function commit(uint256 roundId, bytes32 commitHash) external nonReentrant {
        VerificationRound storage round = rounds[roundId];
        if (round.state == RoundState.UNINITIALIZED) revert RoundDoesNotExist(roundId);

        if (block.timestamp < round.timing.commitStart) {
            revert WindowNotOpen("COMMIT", block.timestamp, round.timing.commitStart);
        }
        if (block.timestamp >= round.timing.revealStart) {
            revert WindowClosed("COMMIT", block.timestamp, round.timing.revealStart);
        }

        if (!validatorRegistry.isValidatorActive(msg.sender)) {
            revert UnauthorizedValidator(msg.sender);
        }

        bytes32 operatorId = validatorRegistry.getValidatorOperatorId(msg.sender);
        uint8 laneId = validatorRegistry.getValidatorLane(msg.sender);
        if (operatorId == bytes32(0)) revert UnauthorizedValidator(msg.sender);

        if (commitments[roundId][msg.sender].exists) {
            revert CommitmentAlreadyExists(roundId, msg.sender);
        }

        commitments[roundId][msg.sender] = CommitmentRecord({
            commitHash: commitHash,
            operatorId: operatorId,
            laneId: laneId,
            commitTimestamp: uint64(block.timestamp),
            exists: true
        });

        if (round.state == RoundState.ROUND_CREATED) {
            _transitionState(round, RoundState.COMMIT_OPEN);
        }

        emit CommitmentSubmitted(roundId, msg.sender, operatorId, laneId, commitHash);
    }

    struct RevealParams {
        uint256 roundId;
        uint8 laneId;
        uint256 price;
        uint256 uncertaintyValue;
        AggregatorLib.UncertaintyType uncertaintyType;
        bool isGated;
        DiagnosticPayload diagPayload;
        bytes32 evidenceHash;
        uint256 nonce;
    }

    /// @notice Reveals validator evidence during the reveal window.
    /// @dev TRUST BOUNDARY: Commit/reveal proves identity, non-repudiation, and anti-copying.
    /// It does not guarantee off-chain mathematical truth, which is triangulated downstream.
    function reveal(RevealParams calldata params) external nonReentrant {
        VerificationRound storage round = rounds[params.roundId];
        if (round.state == RoundState.UNINITIALIZED) revert RoundDoesNotExist(params.roundId);

        if (block.timestamp < round.timing.revealStart) {
            revert WindowNotOpen("REVEAL", block.timestamp, round.timing.revealStart);
        }
        if (block.timestamp >= round.timing.revealEnd) {
            revert WindowClosed("REVEAL", block.timestamp, round.timing.revealEnd);
        }

        CommitmentRecord memory comm = commitments[params.roundId][msg.sender];
        if (!comm.exists) {
            revert CommitmentDoesNotExist(params.roundId, msg.sender);
        }
        if (hasRevealed[params.roundId][msg.sender]) {
            revert AlreadyRevealed(params.roundId, msg.sender);
        }

        // Validator must remain active in registry
        if (!validatorRegistry.isValidatorActive(msg.sender)) {
            revert UnauthorizedValidator(msg.sender);
        }

        // Enforce round consistency against snapshotted commitment identity and lane
        bytes32 currentOpId = validatorRegistry.getValidatorOperatorId(msg.sender);
        uint8 currentLane = validatorRegistry.getValidatorLane(msg.sender);
        if (currentOpId != comm.operatorId || currentLane != comm.laneId || params.laneId != comm.laneId) {
            revert IdentityOrLaneMutated(comm.operatorId, currentOpId, comm.laneId, currentLane);
        }

        // Verify cryptographic commitment matches revealed parameters
        bytes32 payloadHash = keccak256(
            abi.encode(
                comm.operatorId,
                params.laneId,
                params.price,
                params.uncertaintyValue,
                params.uncertaintyType,
                params.isGated,
                params.diagPayload,
                params.evidenceHash
            )
        );
        bytes32 expectedCommitHash = keccak256(
            abi.encode(block.chainid, address(this), params.roundId, msg.sender, payloadHash, params.nonce)
        );

        if (comm.commitHash != expectedCommitHash) {
            revert CommitmentMismatch();
        }

        // Prevent operator over-influence: at most 1 submission per operatorId per lane in a round
        if (_laneOperatorRevealed[params.roundId][params.laneId][comm.operatorId]) {
            revert DuplicateOperatorInLane(comm.operatorId, params.laneId);
        }
        _laneOperatorRevealed[params.roundId][params.laneId][comm.operatorId] = true;
        hasRevealed[params.roundId][msg.sender] = true;

        uint256 effPrice = params.price;
        uint256 effUncertainty = params.uncertaintyValue;

        // Route submission to appropriate lane accumulator
        ValidatorRegistry.LaneRole role = validatorRegistry.getLaneRole(params.laneId);
        if (role == ValidatorRegistry.LaneRole.PRICE_ESTIMATOR) {
            _lanePriceSubmissions[params.roundId][params.laneId].push(
                AggregatorLib.OperatorPriceSubmission({
                    operatorId: comm.operatorId,
                    operator: msg.sender,
                    price: params.price,
                    uncertaintyValue: params.uncertaintyValue,
                    uncertaintyType: params.uncertaintyType,
                    isGated: params.isGated
                })
            );
        } else if (role == ValidatorRegistry.LaneRole.DIAGNOSTIC) {
            // Diagnostic lanes strictly record diagnostic flags; price is forced to 0
            _laneDiagnosticPayloads[params.roundId][params.laneId].push(params.diagPayload);
            effPrice = 0;
            effUncertainty = 0;
        }

        _roundReveals[params.roundId].push(
            ValidatorRevealRecord({
                operatorId: comm.operatorId,
                operator: msg.sender,
                laneId: params.laneId,
                price: effPrice,
                uncertaintyValue: effUncertainty,
                uncertaintyType: params.uncertaintyType,
                evidenceHash: params.evidenceHash,
                timestamp: uint64(block.timestamp),
                isGated: params.isGated
            })
        );

        if (round.state == RoundState.COMMIT_OPEN || round.state == RoundState.ROUND_CREATED) {
            _transitionState(round, RoundState.REVEAL_OPEN);
        }

        emit ValidatorRevealed(params.roundId, msg.sender, comm.operatorId, params.laneId, effPrice, params.evidenceHash);
    }

    /// @notice Evaluates applicability-aware 3D quorum and synthesizes P_DEC via Two-Tier Aggregation.
    function aggregateValidatorEvidence(uint256 roundId) external nonReentrant {
        _aggregateValidatorEvidence(roundId);
    }

    function _aggregateValidatorEvidence(uint256 roundId) internal {
        VerificationRound storage round = rounds[roundId];
        _checkExpiration(round);

        if (block.timestamp < round.timing.revealEnd) {
            revert WindowNotOpen("AGGREGATION", block.timestamp, round.timing.revealEnd);
        }
        if (round.state != RoundState.REVEAL_OPEN && round.state != RoundState.COMMIT_OPEN) {
            revert InvalidState(round.state, RoundState.REVEAL_OPEN);
        }

        // 1. Evaluate Applicability-Aware 3D Quorum (Counting distinct operatorId identities)
        (
            bool quorumMet,
            uint256 totalReveals,
            uint256 distinctOperators,
            uint256 distinctApplicableLanes,
            bool hasPriceEstimator,
            uint256 activeDiagLanes
        ) = _evaluateQuorum(roundId, round.quorumConfig);

        emit QuorumEvaluated(roundId, quorumMet, totalReveals, distinctOperators, distinctApplicableLanes);

        if (!quorumMet || !hasPriceEstimator || activeDiagLanes < 2) {
            _transitionState(round, RoundState.INSUFFICIENT_QUORUM);
            return;
        }

        // 2. Tier 1 Within-Lane Operator Consensus
        AggregatorLib.CanonicalLaneEstimate memory kalmanEst = AggregatorLib.aggregateLaneTier1(
            _lanePriceSubmissions[roundId][LANE_1_KALMAN]
        );
        AggregatorLib.CanonicalLaneEstimate memory huberEst = AggregatorLib.aggregateLaneTier1(
            _lanePriceSubmissions[roundId][LANE_2_HUBER]
        );

        // 3. Tier 2 Cross-Lane Methodology Synthesis
        AggregatorLib.Tier2AggregationResult memory tier2Res = AggregatorLib.synthesizeTier2(
            kalmanEst,
            huberEst
        );

        if (!tier2Res.success) {
            _transitionState(round, RoundState.INSUFFICIENT_QUORUM);
            return;
        }

        round.pDec = tier2Res.pDec;
        round.validatorDispersionBps = tier2Res.validatorDispersionBps;

        _transitionState(round, RoundState.AGGREGATED);

        emit RoundAggregated(roundId, tier2Res.pDec, tier2Res.validatorDispersionBps, tier2Res.kalmanGated);
    }

    /// @notice Ingests and verifies the terminal market price observation (P_MARKET) via EIP-712.
    function submitMarketAttestation(
        uint256 roundId,
        MarketAttestor.MarketAttestation calldata attestation,
        bytes calldata signature
    ) external nonReentrant {
        _submitMarketAttestation(roundId, attestation, signature);
    }

    function _submitMarketAttestation(
        uint256 roundId,
        MarketAttestor.MarketAttestation calldata attestation,
        bytes calldata signature
    ) internal {
        VerificationRound storage round = rounds[roundId];
        _checkExpiration(round);

        if (round.state != RoundState.AGGREGATED) {
            revert InvalidState(round.state, RoundState.AGGREGATED);
        }

        // Verify attestation belongs to this asset and round
        if (attestation.assetId != round.assetId || attestation.roundId != roundId) {
            _transitionState(round, RoundState.MARKET_EVIDENCE_INVALID);
            return;
        }

        // Freshness lower bound: revealEnd minus allowed staleness window (e.g. 1 hour)
        uint256 minValidTimestamp = round.timing.revealEnd > marketAttestor.maxStalenessWindow()
            ? round.timing.revealEnd - marketAttestor.maxStalenessWindow()
            : 0;

        address attestor;
        try marketAttestor.verifyAttestation(attestation, signature, minValidTimestamp) returns (address signer) {
            attestor = signer;
        } catch {
            _transitionState(round, RoundState.MARKET_EVIDENCE_INVALID);
            return;
        }

        round.pMarket = attestation.price;
        _transitionState(round, RoundState.MARKET_EVIDENCE_READY);

        emit MarketEvidenceAttached(roundId, attestation.price, attestor);
    }

    /// @notice Performs read-only inspection of the delayed OSM baseline and synthesizes triangular evidence.
    function readOsmAndEvaluateEvidence(uint256 roundId) external nonReentrant {
        _readOsmAndEvaluateEvidence(roundId);
    }

    function _readOsmAndEvaluateEvidence(uint256 roundId) internal {
        VerificationRound storage round = rounds[roundId];
        _checkExpiration(round);

        if (round.state != RoundState.MARKET_EVIDENCE_READY) {
            revert InvalidState(round.state, RoundState.MARKET_EVIDENCE_READY);
        }

        // Read-only call to delayed OSM
        uint256 pOsm = 0;
        bool hasPrice = false;
        try IOSM(round.osmAddress).readPrice() returns (uint256 price, bool has) {
            pOsm = price;
            hasPrice = has;
        } catch {
            emit OsmReadFailed(roundId, "OSM_REVERTED");
            _transitionState(round, RoundState.OSM_READ_FAILED);
            return;
        }

        if (!hasPrice || pOsm == 0) {
            emit OsmReadFailed(roundId, "OSM_NO_PRICE");
            _transitionState(round, RoundState.OSM_READ_FAILED);
            return;
        }

        round.pOsm = pOsm;
        emit OsmReadCompleted(roundId, pOsm);

        // Synthesize Diagnostic Consensus Flags
        AEGISEvidenceEngine.DiagnosticFlags memory diag = _synthesizeDiagnosticFlags(roundId, round.quorumConfig.ouNotApplicable);

        // Evaluate triangular deviations in EvidenceEngine
        AEGISEvidenceEngine.EvidenceRecord memory record = evidenceEngine.evaluateEvidence(
            round.assetId,
            roundId,
            round.pOsm,
            round.pDec,
            round.pMarket,
            diag
        );

        roundEvidence[roundId] = record;
        _transitionState(round, RoundState.DECISION_READY);
    }

    /// @notice Executes the deterministic decision policy and publishes authoritative P_FINAL to the router.
    function executeDecisionAndFinalize(uint256 roundId) external nonReentrant {
        _executeDecisionAndFinalize(roundId);
    }

    function _executeDecisionAndFinalize(uint256 roundId) internal {
        VerificationRound storage round = rounds[roundId];
        _checkExpiration(round);

        // Normal path: DECISION_READY
        if (round.state == RoundState.DECISION_READY) {
            AEGISEvidenceEngine.EvidenceRecord memory evidence = roundEvidence[roundId];

            AEGISDecisionEngine.DecisionResult memory decision = decisionEngine.executeDecision(
                round.assetId,
                roundId,
                round.pOsm,
                round.pDec,
                round.pMarket,
                round.validatorDispersionBps,
                evidence
            );

            round.pFinal = decision.pFinal;
            round.finalStatus = decision.oracleStatus;
            round.actionCode = decision.actionCode;
            round.finalizedAt = uint64(block.timestamp);

            if (decision.oracleStatus == IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER) {
                _transitionState(round, RoundState.DISPUTED);
            } else {
                _transitionState(round, RoundState.FINALIZED);
            }

            // Publish finalized price to AEGISPriceRouter
            priceRouter.updatePrice(round.assetId, roundId, decision.pFinal, decision.oracleStatus);

            emit RoundFinalized(roundId, round.assetId, decision.pFinal, decision.oracleStatus, decision.actionCode);
            return;
        }

        // Failsafe Path A: INSUFFICIENT_QUORUM -> Fallback to conservative restricted P_OSM if OSM is readable
        if (round.state == RoundState.INSUFFICIENT_QUORUM) {
            uint256 pOsm = 0;
            bool hasPrice = false;
            try IOSM(round.osmAddress).readPrice() returns (uint256 price, bool has) {
                pOsm = price;
                hasPrice = has;
            } catch {}

            if (hasPrice && pOsm > 0) {
                uint256 haircutPrice = (pOsm * 9000) / 10000; // 10% safety haircut on fallback
                round.pFinal = haircutPrice;
                round.finalStatus = IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY;
                round.actionCode = AEGISDecisionEngine.ActionCode.RESTRICT_LTV;
                round.finalizedAt = uint64(block.timestamp);

                priceRouter.updatePrice(round.assetId, roundId, haircutPrice, round.finalStatus);
                emit RoundFinalized(roundId, round.assetId, haircutPrice, round.finalStatus, round.actionCode);
                return;
            } else {
                // Total breakdown
                round.finalStatus = IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER;
                round.actionCode = AEGISDecisionEngine.ActionCode.TRIGGER_CIRCUIT_BREAKER;
                priceRouter.updatePrice(round.assetId, roundId, 0, round.finalStatus);
                return;
            }
        }

        // Failsafe Path B: OSM_READ_FAILED -> Fallback to P_DEC if dispersion is low and market agrees
        if (round.state == RoundState.OSM_READ_FAILED) {
            uint256 devDecMarket = FixedPointMath.relativeDeviationBps(round.pDec, round.pMarket);
            if (devDecMarket < 200 && round.validatorDispersionBps < 150) {
                round.pFinal = round.pDec;
                round.finalStatus = IAEGISPriceFeed.OracleStatus.SUSPECTED_INCONSISTENCY;
                round.actionCode = AEGISDecisionEngine.ActionCode.RESTRICT_LTV;
                round.finalizedAt = uint64(block.timestamp);

                priceRouter.updatePrice(round.assetId, roundId, round.pDec, round.finalStatus);
                emit RoundFinalized(roundId, round.assetId, round.pDec, round.finalStatus, round.actionCode);
                return;
            } else {
                round.finalStatus = IAEGISPriceFeed.OracleStatus.HALTED_CIRCUIT_BREAKER;
                round.actionCode = AEGISDecisionEngine.ActionCode.TRIGGER_CIRCUIT_BREAKER;
                priceRouter.updatePrice(round.assetId, roundId, 0, round.finalStatus);
                return;
            }
        }

        revert InvalidState(round.state, RoundState.DECISION_READY);
    }

    /// @notice Convenience function for keepers to execute aggregation, market evidence, OSM read, and finalization atomically.
    function finalizeRoundWithAttestation(
        uint256 roundId,
        MarketAttestor.MarketAttestation calldata attestation,
        bytes calldata signature
    ) external nonReentrant {
        VerificationRound storage round = rounds[roundId];
        _checkExpiration(round);

        if (round.state == RoundState.FINALIZED || round.state == RoundState.DISPUTED) {
            revert AlreadyFinalized(roundId);
        }

        // Step 1: Aggregate validator evidence
        if (round.state == RoundState.REVEAL_OPEN || round.state == RoundState.COMMIT_OPEN) {
            if (block.timestamp < round.timing.revealEnd) {
                revert WindowNotOpen("AGGREGATION", block.timestamp, round.timing.revealEnd);
            }
            _aggregateValidatorEvidence(roundId);
        }

        // If quorum failed, finalize immediately via failsafe
        if (rounds[roundId].state == RoundState.INSUFFICIENT_QUORUM) {
            _executeDecisionAndFinalize(roundId);
            return;
        }

        // Step 2: Submit market attestation
        if (rounds[roundId].state == RoundState.AGGREGATED) {
            _submitMarketAttestation(roundId, attestation, signature);
        }

        // Step 3: Read OSM and evaluate evidence
        if (rounds[roundId].state == RoundState.MARKET_EVIDENCE_READY) {
            _readOsmAndEvaluateEvidence(roundId);
        }

        // Step 4: Finalize
        if (rounds[roundId].state == RoundState.DECISION_READY || rounds[roundId].state == RoundState.OSM_READ_FAILED) {
            _executeDecisionAndFinalize(roundId);
        }
    }

    /// @notice Evaluates Three-Dimensional Applicability-Aware Quorum.
    /// @dev Quorum counts DISTINCT organizational operatorId values, NOT raw wallet addresses.
    function _evaluateQuorum(
        uint256 roundId,
        QuorumConfig memory config
    ) internal view returns (
        bool quorumMet,
        uint256 totalReveals,
        uint256 distinctOperators,
        uint256 distinctApplicableLanes,
        bool hasPriceEstimator,
        uint256 activeDiagLanes
    ) {
        ValidatorRevealRecord[] storage reveals = _roundReveals[roundId];
        totalReveals = reveals.length;

        bytes32[] memory seenOperatorIds = new bytes32[](totalReveals);
        bool[] memory seenLanes = new bool[](6); // 1 to 5

        for (uint256 i = 0; i < totalReveals; i++) {
            bytes32 opId = reveals[i].operatorId;
            uint8 lane = reveals[i].laneId;

            bool isNewOp = true;
            for (uint256 j = 0; j < distinctOperators; j++) {
                if (seenOperatorIds[j] == opId) {
                    isNewOp = false;
                    break;
                }
            }
            if (isNewOp && opId != bytes32(0)) {
                seenOperatorIds[distinctOperators] = opId;
                distinctOperators++;
            }

            if (lane >= 1 && lane <= 5) {
                // If OU is NOT_APPLICABLE for this asset, skip Lane 4 from applicable lane count
                if (lane == LANE_4_OU && config.ouNotApplicable) {
                    continue;
                }
                if (!seenLanes[lane]) {
                    seenLanes[lane] = true;
                    distinctApplicableLanes++;

                    if (lane == LANE_1_KALMAN || lane == LANE_2_HUBER) {
                        hasPriceEstimator = true;
                    } else {
                        activeDiagLanes++;
                    }
                }
            }
        }

        quorumMet = (
            totalReveals >= config.minTotalQuorum &&
            distinctOperators >= config.minDistinctOperators &&
            distinctApplicableLanes >= config.minDistinctApplicableLanes &&
            hasPriceEstimator &&
            activeDiagLanes >= 2
        );
    }

    /// @notice Synthesizes diagnostic consensus flags across revealed diagnostic lanes
    function _synthesizeDiagnosticFlags(
        uint256 roundId,
        bool ouNotApplicable
    ) internal view returns (AEGISEvidenceEngine.DiagnosticFlags memory diag) {
        // Lane 1 Gating: if >= 50% of Lane 1 reveals report gated
        AggregatorLib.OperatorPriceSubmission[] storage kalmanReveals = _lanePriceSubmissions[roundId][LANE_1_KALMAN];
        uint256 kalmanGatedCount = 0;
        for (uint256 i = 0; i < kalmanReveals.length; i++) {
            if (kalmanReveals[i].isGated) kalmanGatedCount++;
        }
        bool kalmanGated = (kalmanReveals.length > 0 && kalmanGatedCount * 2 >= kalmanReveals.length);

        // Lane 3 JSD: if >= 50% report divergent
        DiagnosticPayload[] storage jsdPayloads = _laneDiagnosticPayloads[roundId][LANE_3_JSD];
        uint256 jsdCount = 0;
        for (uint256 i = 0; i < jsdPayloads.length; i++) {
            if (jsdPayloads[i].jsdDivergent) jsdCount++;
        }
        bool jsdDivergent = (jsdPayloads.length > 0 && jsdCount * 2 >= jsdPayloads.length);

        // Lane 4 OU: if applicable and >= 50% report jump candidate
        bool ouJump = false;
        if (!ouNotApplicable) {
            DiagnosticPayload[] storage ouPayloads = _laneDiagnosticPayloads[roundId][LANE_4_OU];
            uint256 ouCount = 0;
            for (uint256 i = 0; i < ouPayloads.length; i++) {
                if (ouPayloads[i].ouJumpCandidate) ouCount++;
            }
            ouJump = (ouPayloads.length > 0 && ouCount * 2 >= ouPayloads.length);
        }

        // Lane 5 CUSUM: if >= 50% report drift/trip
        DiagnosticPayload[] storage cusumPayloads = _laneDiagnosticPayloads[roundId][LANE_5_CUSUM];
        uint256 cusumCount = 0;
        for (uint256 i = 0; i < cusumPayloads.length; i++) {
            if (cusumPayloads[i].cusumTripped) cusumCount++;
        }
        bool cusumTripped = (cusumPayloads.length > 0 && cusumCount * 2 >= cusumPayloads.length);

        return AEGISEvidenceEngine.DiagnosticFlags({
            kalmanGated: kalmanGated,
            jsdDivergent: jsdDivergent,
            ouJumpCandidate: ouJump,
            cusumTripped: cusumTripped,
            ouNotApplicable: ouNotApplicable
        });
    }

    /// @notice Transitions round state and emits state change event
    function _transitionState(VerificationRound storage round, RoundState newState) internal {
        RoundState oldState = round.state;
        round.state = newState;
        emit RoundStateChanged(round.roundId, oldState, newState);
    }

    /// @notice Enforces deadline expiration
    function _checkExpiration(VerificationRound storage round) internal {
        if (
            round.state != RoundState.FINALIZED &&
            round.state != RoundState.DISPUTED &&
            round.state != RoundState.EXPIRED &&
            block.timestamp > round.timing.finalizationDeadline
        ) {
            _transitionState(round, RoundState.EXPIRED);
            revert RoundExpired(round.roundId, block.timestamp, round.timing.finalizationDeadline);
        }
    }

    /// @notice Explicitly transitions a round past its deadline into EXPIRED state.
    function expireRound(uint256 roundId) external nonReentrant {
        VerificationRound storage round = rounds[roundId];
        if (round.state == RoundState.UNINITIALIZED) revert RoundDoesNotExist(roundId);
        if (
            round.state == RoundState.FINALIZED ||
            round.state == RoundState.DISPUTED ||
            round.state == RoundState.EXPIRED
        ) {
            revert InvalidState(round.state, RoundState.DECISION_READY);
        }
        if (block.timestamp <= round.timing.finalizationDeadline) {
            revert WindowNotOpen("EXPIRATION", block.timestamp, round.timing.finalizationDeadline);
        }
        _transitionState(round, RoundState.EXPIRED);
    }

    /// @notice Returns count of validator reveals for a round
    function getRoundRevealsCount(uint256 roundId) external view returns (uint256) {
        return _roundReveals[roundId].length;
    }

    /// @notice Returns full round information
    function getRound(uint256 roundId) external view returns (VerificationRound memory) {
        return rounds[roundId];
    }

    /// @notice Returns full reveal records for a round
    function getRoundReveals(uint256 roundId) external view returns (ValidatorRevealRecord[] memory) {
        return _roundReveals[roundId];
    }
}
