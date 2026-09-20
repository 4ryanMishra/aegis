# AEGIS — Judge & Reviewer Fast Walkthrough (2-Minute Demo Guide)

> **Multipli / VIT Vellore Hackathon 2026 Track: "Rethinking Blockchain Oracles"**

AEGIS is an **On-Chain Oracle Cross-Checking & Risk-Resolution Layer**. Instead of trusting an unverified delayed Oracle Security Module (OSM) or training speculative off-chain prediction models, AEGIS compares the upstream Multipli OSM against 6 established on-chain oracle networks (**Chainlink, Pyth, Chronicle, RedStone, Supra, and API3**), runs deterministic on-chain price-band agreement clustering ($\le 0.5\%$), and enforces conservative risk resolution to protect protocol solvency.

---

## 1. Ten Core Architectural Questions

### 1. What is the core problem with Multipli's delayed OSM?
Multipli's Oracle Security Module (OSM) introduces a mandatory delay window (e.g. 60 minutes) to prevent single-block flash-loan price manipulation. However, during flash crashes, high volatility, or upstream oracle stalls, the delayed OSM remains stale at historical elevated prices. An attacker can deposit suddenly devalued collateral at the stale high valuation and borrow unbacked stablecoins (e.g. RWAUSD), leaving the protocol with catastrophic bad debt.

### 2. Is AEGIS just another oracle?
**No.** AEGIS does **NOT** build another predictive oracle and does **NOT** train speculative off-chain machine learning models. AEGIS is a **cross-checking, risk-resolution layer** that sits between oracle feeds and downstream lending/vault protocols.

### 3. What oracle networks does AEGIS cross-check?
AEGIS ingests real-time, on-chain price observations from 6 established oracle networks:
1. **Chainlink** (Decentralized Oracle Networks)
2. **Pyth Network** (High-frequency pull oracle with confidence intervals)
3. **Chronicle Protocol** (MakerDAO battle-tested Scribe oracles)
4. **RedStone** (Modular gas-optimized data packages)
5. **Supra Oracles** (Dora consensus multi-feed)
6. **API3** (First-party airnode dAPIs)
Plus the target **Multipli OSM** feed.

### 4. How does AEGIS compute Consensus on-chain?
AEGIS implements **Deterministic Price-Band Agreement Clustering**:
- Each feed is tested against every other feed for agreement within a tight threshold ($\le 0.5\%$ spread).
- AEGIS identifies the largest cluster of agreeing independent oracles.
- The **Consensus Price ($P_{\text{CONSENSUS}}$)** is the exact median of this largest agreement cluster.
- In normal conditions, all 6 external oracles form an agreement cluster (spread $\approx 0.05\%$).

### 5. How does AEGIS detect Multipli divergence?
AEGIS computes the exact relative deviation between the delayed Multipli OSM and the independent oracle consensus:
$$\text{multipliDeviation} = \frac{|P_{\text{OSM}} - P_{\text{CONSENSUS}}|}{P_{\text{CONSENSUS}}}$$
- $\le 0.50\%$: **Aligned** (Multipli is consistent with DeFi market consensus).
- $> 0.50\%$: **Divergent** (Multipli is lagging, stale, or experiencing feed dislocation).

### 6. What happens during a sudden flash crash?
When the market drops (e.g., Gold drops $4,380 \to \$4,050$) while Multipli OSM remains stale at $4,380.00:
- External oracles immediately report \$4,050.
- AEGIS detects an $8.13\%$ deviation ($\gg 0.5\%$).
- AEGIS sets Oracle Status to `RESTRICTED` (Divergent).
- AEGIS applies the **Conservative Valuation Rule**:
  $$P_{\text{FINAL}} = \min(P_{\text{OSM}}, P_{\text{CONSENSUS}}) = \$4,050.85$$
- Downstream collateral borrowing LTV is restricted from 80% to 50%.
- Maximum borrow capacity on 10 oz Gold drops from \$35,040 to \$20,254, saving the protocol from **\$14,786 in bad debt**.

### 7. What happens when an external oracle is poisoned or corrupted?
If a rogue oracle injects a false quote (e.g. RedStone reports \$5,200 while others report \$4,380):
- The rogue quote falls outside the 0.5% agreement band of the other 5 oracles.
- The agreement cluster forms among the 5 honest oracles (83.3% agreement ratio).
- The rogue oracle is isolated into an outlier cluster (size 1) and rejected.
- $P_{\text{CONSENSUS}}$ remains \$4,380.00, Multipli deviation is 0.00%, and protocol operation continues with 0 disruption.

### 8. What happens during severe market dislocation or oracle fragmentation?
If oracles fragment and fail to achieve consensus ($\ge 3$ oracles agreeing):
- AEGIS triggers a circuit breaker (`HALTED_CIRCUIT_BREAKER`).
- Downstream lending protocols freeze borrows and collateral withdrawals until valid consensus is restored.

### 9. What are the downstream protocol risk states?
AEGIS directly governs collateral valuation and borrow parameters for protocols like Multipli RWAUSD vaults:
- **`NORMAL` (80% LTV):** Full borrowing capacity, collateral valued at $P_{\text{OSM}}$.
- **`RESTRICTED` (50% LTV + Conservative Haircut):** Multipli is stale/lagging; collateral valued at $\min(P_{\text{OSM}}, P_{\text{CONSENSUS}})$, borrow capacity strictly capped.
- **`DISPUTED` (60% LTV):** Minor consensus ambiguity; conservative pricing applied.
- **`HALTED` (0% LTV / Reverts):** Circuit breaker active; borrows and liquidations paused.

### 10. How is this verified on-chain?
- Complete EVM implementation in Solidity (`^0.8.24`): `OracleRegistry.sol`, `ConsensusEngine.sol`, `RiskDecisionEngine.sol`, `AEGISPriceRouter.sol`.
- 88/88 passing tests in Foundry across 14 test suites (`forge test`).
- Gas-efficient: Price query $\approx 13.6\text{k}$ gas; Consensus resolution $\approx 85\text{k}$ gas.

---

## 2. Fast Local Demonstration (One-Click)

### Launch Complete Demo Environment
```powershell
.\run-demo.ps1
```
This automatically starts the Python backend, launches the Next.js institutional risk control room at [http://localhost:3000](http://localhost:3000), and opens your browser.

---

## 3. Fast CLI Demonstration

### Step 1: Normal Multi-Oracle Agreement (Multipli Aligned)
```bash
python -m packages.client.scenario_runner --scenario normal
```
*Output:*
```text
Round ID:              1
Asset:                 XAUt (Tether Gold)
Multipli OSM:          $4,380.0000
Consensus Median:      $4,380.0000 (6/6 Oracles Agree, Spread: 0.046%)
Multipli Status:       ALIGNED (Dev: 0.00%)
AEGIS Valuation:       $4,380.0000
Oracle Status:         NORMAL
Protocol Action:       NORMAL (80% LTV | Max Borrow: $35,040.00)
```

### Step 2: Flash Drop (Multipli Stale — Conservative Risk Resolution)
```bash
python -m packages.client.scenario_runner --scenario flash_drop
```
*Output:*
```text
Round ID:              1
Asset:                 XAUt (Tether Gold)
Multipli OSM:          $4,380.0000 (STALE DELAYED FEED)
Consensus Median:      $4,050.8500 (5/6 Oracles Drop, Spread: 0.121%)
Multipli Status:       DIVERGENT (Dev: 8.13% >> 0.50% Threshold)
AEGIS Valuation:       $4,050.8500 (ENFORCED: min(P_OSM, P_CONSENSUS))
Oracle Status:         RESTRICTED
Protocol Action:       RESTRICTED (50% LTV | Max Borrow: $20,254.25)
Bad Debt Prevented:    $14,785.75
```

### Step 3: Verify All 5 Scenarios
```bash
python -m packages.client.scenario_runner --all
```

---

## 4. Full Verification Suite
```powershell
.\verify.ps1
```
- **Python Tests**: 54/54 PASS
- **Scenario Suite**: 5/5 PASS
- **Next.js Production Build**: PASS (0 errors)
- **Solidity Smart Contracts**: 88/88 PASS across 14 suites
