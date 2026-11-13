# KRISHI-X architecture

## First interaction
1. Farmer opens the assistant and speaks or types.
2. Assistant captures crop, quantity, farm location and harvest readiness.
3. Missing details are asked one at a time.
4. Farmer reviews and confirms the structured profile.
5. Only after confirmation may the orchestration layer request market options.

## Planned agent workflow
- Mandi Discovery Agent: discover nearby markets.
- Market Activity Agent: check trading schedules and recent activity; do not infer physical stock.
- Price Intelligence Agent: current/historical prices, forecast and confidence.
- Buyer Discovery Agent: buyer demand and offers.
- Transport Agent: route, capacity, handling/storage and quote status.
- Profit Optimization Agent: compare feasible options by net realization.
- Recommendation Agent: explain recommendation, data freshness and uncertainty.

## Data integrity
Every external value should carry source, observed_at, freshness and verification status. Transport amounts must be labelled `verified_quote` or `estimate`. Synthetic demo data must be labelled `demo`.
