# AEGIS — MVP Build Sequence

## Phase 0 — Read and lock
- Read all agent rules.
- Read PRD, TRD, facts/assumptions, frontend brief, threat model, and workflow.
- Create a task board from the phases below.
- Do not implement until the architecture report is produced.

## Phase 1 — Vertical skeleton
Goal: a judge can open the browser and see a real AEGIS flow with mocked inputs.

Build:
1. Next.js shell.
2. Light institutional UI.
3. Scenario model.
4. API skeleton.
5. Shared schema.
6. Mock `P_OSM` provider.
7. Four placeholder validator strategies.
8. Deterministic `P_DEC` aggregation.
9. Mock/live-switchable `P_MARKET` adapter.
10. Evidence calculation.
11. Decision result.

## Phase 2 — Real validator methodologies
When the research team supplies methods:
- evaluate each method independently;
- define inputs/outputs;
- add source citation;
- backtest;
- register as strategy plugin;
- compare forecast error / calibration / robustness;
- never insert a method solely because it sounds sophisticated.

## Phase 3 — Decentralization mechanics
Prototype:
- validator identity;
- signed observations;
- commit/reveal if justified;
- quorum;
- deterministic aggregation;
- provenance hashes.

Do not call the MVP “fully decentralized” unless the actual implementation supports independent participants.

## Phase 4 — Solidity
Implement compact verification/decision contracts in Foundry + Anvil. Keep heavy math off-chain.

## Phase 5 — Historical replay
Build a replay engine where known historical sequences can be fed into the system to evaluate:
- delayed baseline;
- `P_DEC` quality;
- detection quality;
- collateral valuation effect.

## Phase 6 — Attack lab
Provide deterministic scenarios with a visible before/after comparison.

## Phase 7 — Demo hardening
- one-click scenario reset;
- no broken live dependencies;
- fallback fixtures;
- data-status labels;
- source drawer;
- clear baseline-vs-AEGIS accounting.
