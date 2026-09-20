# AEGIS — Judge & Reviewer Fast Walkthrough (2-Minute Demo Guide)

This guide is designed for hackathon judges, auditors, and protocol architects seeking a concise, verifiable breakdown of the AEGIS oracle verification engine.

---

## 1. Ten Core Architectural Questions

### 1. What is wrong with a fixed oracle delay (e.g. 1-hour OSM)?
A fixed delay creates a dangerous blind latency window. During sudden volatility or a flash crash, the delayed oracle remains stale at historical prices for up to 1 hour, enabling toxic arbitrage, underwater debt minting, and delayed liquidations.

### 2. What does AEGIS add?
AEGIS repurposes the existing 1-hour delay window into an active, multi-lane cryptographic and statistical verification process. It monitors real-time market behavior **in parallel** with the existing delay, preventing stale or manipulated prices from entering protocol accounting.

### 3. How does the verification window work?
- **$T_0$ (Start of OSM delay):** A new verification round opens concurrently.
- **$T_0 \to T_1$ (Verification window):** Decentralized validators compute statistical methodology estimates, submit salted Keccak-256 commitments, and reveal their payloads.
- **$T_1$ (End of OSM delay):** An independent signed market attestation ($P_{MARKET}$) is ingested, and the keeper atomically finalizes the round with **zero added latency**.

### 4. Why are validators not simply trusted?
No individual validator or statistical methodology is treated as an unquestionable truth source.
- Validators must pass **Applicability-Aware 3D Quorum** ($\ge 3$ distinct organizational `operatorId`s, $\ge 3$ distinct methodology lanes).
- Single-entity Sybils across multiple wallets are collapsed to 1 vote.
- Submissions within each lane are filtered by **robust median** and dispersion heuristics before cross-lane synthesis.

### 5. How does $P_{DEC}$ differ from $P_{OSM}$?
- $P_{OSM}$ is a point-in-time delayed spot price from the upstream oracle.
- $P_{DEC}$ is a synthesized, robust decentralized consensus value formed by a **Two-Tier Aggregation Hierarchy** (within-lane median $\to$ cross-lane inverse-variance blend of Kalman Filter and Huber M-Estimator lanes).

### 6. Why is $P_{MARKET}$ not treated as ground truth?
$P_{MARKET}$ is classified as an external **Market Observer** signed via EIP-712. It can be manipulated, stale, or dislocated. The On-Chain Evidence Engine triangulates all three values ($P_{OSM}, P_{DEC}, P_{MARKET}$) rather than blindly trusting the market observer.

### 7. What happens during a flash crash?
If live market prices plunge from \$100 to \$93 while $P_{OSM}$ remains stale at \$100:
- The Evidence Engine detects abnormal deviation ($d(OSM, DEC) > 400$ BPS).
- The Decision Engine transitions oracle status to `EVIDENCE_OF_ABNORMAL_DEVIATION` and selects the conservative lower price (\$93).
- The downstream protocol enters `RESTRICTED` mode, applying a 50% LTV cap (down from 80%) to protect solvency.

### 8. What happens when a validator is poisoned?
If a rogue validator injects an extreme outlier (\$500.00 quote):
- Tier 1 within-lane aggregation computes the median of submissions in that lane.
- The outlier is completely suppressed.
- $P_{DEC}$ remains accurate at \$100.00, consensus remains `HEALTHY_CONSENSUS`, and the protocol operates normally.

### 9. What happens when the market observer disagrees?
If $P_{OSM}$ and $P_{DEC}$ agree at \$100, but $P_{MARKET}$ reports \$70 (a 30% dislocation):
- The Evidence Engine detects triangular inconsistency.
- Because the market observer is not an absolute authority, the Decision Engine triggers a circuit breaker (`HALTED_CIRCUIT_BREAKER` or protective haircut).
- Protocol borrowing and debt creation are frozen.

### 10. How does this ultimately affect protocol risk?
AEGIS replaces binary trust (either trusting a delayed feed or trusting an instant feed) with **adaptive risk states**:
- `NORMAL` (80% LTV): Full borrowing and normal market operations.
- `RESTRICTED` (50% LTV + Valuation Haircut): Constrains debt ceiling and collateral valuation during abnormal divergence.
- `HALTED` (Circuit Breaker): Suspends minting and borrows to prevent protocol insolvency.

---

## 2. Fast Local Demonstration (2 Commands)

### Step 1: Execute Canonical Normal Consensus
```bash
python -m packages.client.scenario_runner --scenario normal
```
*Expected Output:*
```text
Round ID:              1
P_OSM:                 $100.0000
P_DEC:                 $100.0031
P_MARKET:              $100.0500
P_FINAL:               $100.0031
Oracle Status:         HEALTHY_CONSENSUS
Protocol State:        NORMAL (80% LTV)
```

### Step 2: Execute Hostile Flash Crash / Dislocation
```bash
python -m packages.client.scenario_runner --scenario flash_crash
```
*Expected Output:*
```text
Round ID:              1
P_OSM:                 $100.0000 (Stale OSM)
P_DEC:                 $92.9936  (Real-Time Consensus)
P_MARKET:              $93.5000  (Live Market)
P_FINAL:               $92.9936  (Conservative Haircut)
Oracle Status:         EVIDENCE_OF_ABNORMAL_DEVIATION
Protocol State:        RESTRICTED (50% LTV, Borrows Haircut)
```

---

## 3. Full Five-Scenario Suite Verification

To verify all 5 canonical scenarios sequentially:
```bash
python -m packages.client.scenario_runner --all
```

To run the full Foundry on-chain integration and adversarial test matrix:
```bash
cd contracts
forge test -vvv
```
*(82 / 82 tests passing across 13 suites)*
