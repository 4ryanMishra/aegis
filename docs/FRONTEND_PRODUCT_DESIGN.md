# AEGIS — Frontend Product & Visual Design Brief

## Direction
Build a **light institutional-finance risk terminal**, not a generic AI dashboard.

Multipli's current public brand uses a highly polished product/finance aesthetic and its public site emphasizes tokenized RWA infrastructure and institutional-grade positioning. AEGIS should borrow the *discipline* of that presentation — strong typography, hierarchy, restrained motion, financial data presentation — while intentionally using a light interface for the hackathon prototype.

## Hard constraints
- Light mode only for MVP.
- No neon cyberpunk styling.
- No purple-gradient “AI” hero sections.
- No glassmorphism cards everywhere.
- No floating chatbot.
- No fake 3D crypto coins.
- No excessive rounded cards.
- No gamification, badges, flashcards, streaks, “AI magic” copy, or decorative Lottie clutter.
- No animated number explosions.
- No fake Bloomberg branding.
- No copy-pasting Multipli's UI; take inspiration, do not imitate assets/layout one-to-one.

## Visual language
- White / off-white page background.
- Near-black typography.
- One restrained accent for actionable/highlight states.
- Hairline borders and subtle separators.
- Small radii; avoid pill-shaped everything.
- Financial tabular numerals.
- Dense information where useful, with generous whitespace between sections.
- Charts should look like analytical charts, not marketing illustrations.

## Main experience
App shell:
- compact wordmark: `AEGIS`
- subtitle: `Oracle Verification Engine`
- environment/status indicator: `SIMULATION` / `TESTNET`
- scenario selector
- run/reset controls

Primary workspace:

### 1. Oracle state strip
Show:
`P_OSM` | `P_DEC` | `P_MARKET` | `FINAL`

This must be the first thing the eye sees.

### 2. Verification timeline
A horizontal 10 PM → 11 PM timeline showing:
- OSM value arrival;
- validator observations;
- market-source observations;
- finalization.

### 3. Validator evidence table
Columns:
- Validator
- Method
- Source set
- Estimate
- Interval/confidence
- Timestamp
- Status

### 4. Evidence comparison
A compact analytical chart comparing `P_OSM`, validator distribution / `P_DEC`, and `P_MARKET`.

### 5. Decision panel
Explain in plain finance language:
- baseline valuation;
- AEGIS valuation;
- deviation;
- collateral value at the configured factor;
- resulting difference;
- reason codes.

### 6. Provenance drawer
Every number should be inspectable:
- source;
- timestamp;
- methodology ID;
- validator ID;
- aggregation method;
- simulated/live status.

## Interaction style
Motion is functional only:
- timeline progression;
- row insertion when validator data arrives;
- chart update;
- state transition.

Never animate to make the UI look “AI-generated.”

## Copy style
Prefer:
- `Delayed oracle value`
- `Independent reference`
- `Terminal market observation`
- `Deviation`
- `Validator quorum`
- `Evidence status`
- `Collateral valuation`

Avoid:
- `AI MAGIC`
- `Oracle Superbrain`
- `Quantum prediction`
- `Trust score: 99.9%` without a defined metric.

## Reference requests for later refinement
Useful references to supply to the frontend agent:
1. 2–3 screenshots of light-mode institutional finance dashboards.
2. 1–2 screenshots of a clean trading/market analytics interface.
3. 1 screenshot of a polished risk/compliance terminal.
4. Optional: Pinterest/Figma links that show typography/layout only.

Do not send 20 references. Three to six strong references are enough.
