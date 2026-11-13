# KrishiMitra (KRISHI-X engine)

KrishiMitra (कृषिमित्र) means "farmer's friend". It is a voice-first assistant that ranks where to sell by
**estimated net realization** (revenue minus transport, handling, storage, loss), forecasts prices with an honest gate,
and recommends SELL NOW vs HOLD.

## Run
```
cd krishimitra/backend
..\..\.venv\Scripts\python -m uvicorn app.main:app --port 8000      # then open http://localhost:8000
..\..\.venv\Scripts\python -m pytest tests -q                       # 13 tests
```
New machine: `python -m venv .venv && .venv\Scripts\pip install -r krishimitra/backend/requirements.txt`.
Local LLM (optional, off by default): set `KRISHIMITRA_LLM=ollama`, `OLLAMA_URL`, `OLLAMA_MODEL`. The LLM only extracts slots and phrases
explanations; all numbers come from `costs.py`, `forecast.py`, `logistics.py`.

## Layout
- `backend/app/profile.py` Farmer Profile Agent (en/hi/mr slot filling, confirm before market work)
- `backend/app/agents.py` Mandi Discovery, Price Intelligence, Market Activity, Buyer, Cold Storage, Transport, Shared Load, Price Forecast, Sell vs Hold, Net Realization, Recommendation
- `backend/app/orchestrator.py` explicit pipeline; a failing agent degrades the plan
- `backend/app/forecast.py` baselines + ETS + lag-Ridge + ensemble, rolling-origin backtest, gate (beat baselines by 5% and calibrated 80% interval, else "no reliable forecast")
- `backend/app/costs.py` deterministic money maths; `logistics.py` OR-Tools shared-load; `orders.py` order/tracking state machine (SQLite)
- `frontend/index.html` single-page UI (no build step)

## The action agent
`POST /api/agent` turns a free-form request into tool calls that DO things: open a tab, show an option, compare mandis, read the forecast, explain sell-vs-hold, change a cost and recalculate, start a new lot, create and track an order, request transport or storage, switch language. Rules route EN/HI/MR requests today; set `KRISHIMITRA_LLM=ollama` (plus `OLLAMA_URL`, `OLLAMA_MODEL`) and the local model picks the tool name while the arguments stay rule-parsed and validated. Orders, bookings and sale confirmation always ask yes/no first. Nothing is ever booked with a third party: requests are logged in the app only.

## Live data (data.gov.in / Agmarknet)
1. Get a free key at data.gov.in (My Account) and set `DATA_GOV_API_KEY`.
2. Pull prices: `python -m app.adapters refresh` (or `POST /api/admin/refresh`). Optional backfill from an Agmarknet/CEDA export: `python -m app.adapters import file.csv`.
3. Once any live row exists the app switches to LIVE mode automatically. Mandis with no live rows are excluded (never filled with demo values). Snapshots are stored in `backend/live_prices.db`.
4. The daily feed has no arrivals column and only today's prices, so forecasts show "insufficient data" until about 120 days of history exist (accumulate daily or import a CSV). The resource id `9ef84268-...` is unverified: override with `DATA_GOV_RESOURCE`.
Daily routine without an API key: click **Download** (CSV) on the data.gov.in resource page. The server watches `~/Downloads` (and `~/Downloads/mandiproject`; override with `KRISHIMITRA_WATCH_DIRS`) and auto-imports any new `9ef84268*.csv` within ~30 s. Force a check: `POST /api/admin/scan`. Put `DATA_GOV_API_KEY=...` in `backend/.env` (gitignored) to also auto-refresh every 3 h; the shared public sample key is rate-limited, use your own.
Agmarknet 2.0's own API requires a captcha, so it is not scraped.

## What is real and what is not
- **Until live rows are loaded, ALL market data is DEMO DATA** (`demo_data.py`: synthetic seeded series, fictional warehouses/transporters/buyers, approximate unverified coordinates). Forecast accuracy shown is on synthetic data and means nothing for real mandis.
- The live adapter is written and unit-tested on fixtures, but NOT yet run against the real API (no key). Buyers, warehouses, transporters stay DEMO in live mode.
- Cost defaults (commission, hamali, vehicle rates, financing) are unverified placeholders, editable in the UI.
- Shared-load pool members are `[Simulated]`. No phone numbers are shown anywhere. Storage availability is never claimed.
- Not built (out of reach in the time box): other role portals (FPO/buyer/transporter/warehouse/admin), Flutter app, Postgres/PostGIS, Celery, LightGBM/XGBoost, real STT/TTS beyond the browser's Web Speech API.
