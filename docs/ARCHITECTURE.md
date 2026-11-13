# KRISHI-X architecture

## Request flow
1. **Web** (`apps/web`) opens on the assistant. Speech: browser Web Speech API, else MediaRecorder upload to `/api/voice/transcribe`. Replies are read aloud with `speechSynthesis`.
2. **`POST /api/chat`** runs the **Farmer Profile Agent** (`conversation/profile_agent.py`): one question at a time, only missing slots, corrections, read-back. State is saved in `conversation_sessions`. Crops come from the commodity catalogue (`repositories/market_data.crop_catalogue`). Places are geocoded (`services/geocoding.py`, cached).
3. Only when the farmer confirms: the profile and inventory are saved (`farmer_profiles`, `farmer_inventory`), then the **orchestrator** runs.
4. **Orchestrator** (`agents/orchestrator.py`): an explicit typed pipeline. A failing agent degrades the plan and never crashes it, and Mandi Discovery / Price Intelligence failures stop downstream work.

| Agent | Reads | Output |
|---|---|---|
| Mandi Discovery | market_data.mandis_with_prices (geocoded, has prices) | ≤7 mandis within 450 km, distance ESTIMATE |
| Price Intelligence | market_data.series | latest/avg/trend per mandi + meta (official/demo) |
| Market Activity | series arrivals | unavailable in LIVE (source has none) |
| Buyer Discovery | demo buyers | hidden in LIVE |
| Cold Storage | demo warehouses ≤200 km | availability always UNCONFIRMED |
| Transport | costs.transport + demo rate card | ESTIMATE |
| Shared Load | OR-Tools on simulated pool | not ranked in LIVE |
| Price Forecast | ml/forecast (gate: beat baselines by 5 %, calibrated 80 % interval, ≥120 days) | per-horizon ok / no_reliable_forecast / insufficient_data |
| Sell vs Hold | costs.hold_option + forecast + crop shelf life | SELL NOW / HOLD / INSUFFICIENT INFORMATION |
| Net Realization | costs.sell_option | ranked options (score = net − risk penalty) |
| Recommendation | all of the above | best option, decision, answers to the 5 farmer questions |

Every agent returns `{"data", "meta"}` with `meta = core.meta.meta(source, verification, observed_at, last_updated, freshness_days, confidence, error)`.

## Data
- `market_data` is the single read path: **LIVE** when `mandi_prices` has any row (never padded with demo values), otherwise **DEMO** (Rocket's seeded synthetic series).
- Ingestion: `services/adapters/agmarknet_datagov.py` (CSV import + API fetch), idempotent upsert on (mandi, commodity, variety, grade, date), and `verification_status=official`.
- PostGIS: `mandis.geog geography(Point,4326)` with a GiST index, filled by the geocode job. Ranking currently uses a Python haversine × road factor over ≤1,700 mandis (marked shortcut).

## Security
- No secrets in code (env via `.env`), CORS from `CORS_ORIGINS`, pydantic validation with length limits, rate limit on `/api/*`.
- The admin API needs `X-Admin-Token`; CSV import is restricted to `data/raw/*.csv`.
- Auth and RBAC for the role portals arrive in Phase 8.
