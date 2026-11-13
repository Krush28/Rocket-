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

## What is real and what is not
- **ALL market data is DEMO DATA** (`demo_data.py`: synthetic seeded series, fictional warehouses/transporters/buyers, approximate unverified coordinates). Forecast accuracy shown is on synthetic data and means nothing for real mandis.
- No live adapter yet. Next step: add `adapters.py` for data.gov.in Agmarknet (needs API key) and write rows in the shape `demo_data.series()` returns.
- Cost defaults (commission, hamali, vehicle rates, financing) are unverified placeholders, editable in the UI.
- Shared-load pool members are `[Simulated]`. No phone numbers are shown anywhere. Storage availability is never claimed.
- Not built (out of reach in the time box): other role portals (FPO/buyer/transporter/warehouse/admin), Flutter app, Postgres/PostGIS, Celery, LightGBM/XGBoost, real STT/TTS beyond the browser's Web Speech API.
- Reference repos in `../reference-repos` are read-only inspiration; four have no licence, so no code was copied from them.
