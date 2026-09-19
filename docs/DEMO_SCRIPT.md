# MVP Demo Script

## Scenario A — abnormal OSM value

1. Start with a normal market and show `P_OSM`.
2. Click `Sudden Market Drop`.
3. Start the one-hour verification window.
4. Show validator submissions arriving from independent logical nodes.
5. Show P_DEC converge through robust aggregation.
6. At T1 reveal P_MARKET.
7. Show deviation calculations.
8. Show `P_OSM` flagged as suspicious/inconsistent.
9. Show the configured decision policy.
10. Show baseline collateral vs AEGIS collateral.

## Scenario B — healthy agreement
Repeat with all values close together. The system should show that no override is necessary.

## Judge-facing claim
The demo proves the **mechanism**, not a production guarantee: a delayed oracle value can be evaluated against independently produced evidence during the delay window before protocol use.
