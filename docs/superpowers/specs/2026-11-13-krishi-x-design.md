# KRISHI-X: platform design

Date: 2026-11-13. Status: draft for approval.

## Intent and why
Farmers sell on the displayed mandi price, but what they actually take home is that price minus transport, commission, hamali, storage and spoilage. KRISHI-X answers five questions for one lot of produce: current nearby prices, best net earnings across mandis and buyers, likely price direction, sell now or hold, and which warehouse/transporter is economical. It ranks every option by **expected net realization**, never by displayed modal price. Voice-first, multilingual (en/hi/mr first), for farmers with limited tech literacy, plus FPO, buyer, transporter, cold-storage and admin roles.

## Goals
- A real, maintainable product, built one phase at a time (spec phases 1-10), each phase working and tested before the next.
- Honest data: every value carries source, timestamps, freshness, verification status. Demo data labelled `DEMO DATA`. Transport costs labelled `VERIFIED QUOTE` or `ESTIMATE`.
- Honest forecasts: shown only when they beat baselines in time-ordered backtests; otherwise an explicit insufficient-data result.
- All money maths in deterministic Python; the LLM only extracts slots and phrases explanations.

## Non-goals
Crop disease, generic advisory, loans, Aadhaar (never collected), payments.

## Anti-goals (failure even if it works)
- Fabricated live prices, buyer offers, phone numbers or warehouse capacity.
- Forecasts presented as guarantees, or accuracy claimed without evaluation.
- Recommending a mandi because its modal price is highest.

## Approaches considered
- **A. Port the Rocket engine (github.com/Krush28/Rocket-, `krishimitra/`) into KRISHI-X's layered structure. Chosen by the user.** Rocket already has working agents, forecasting with a baseline gate, cost maths, OR-Tools shared load, a data.gov.in adapter, orders and 13 tests. KRISHI-X has the target folder layout, a Next.js app and DB-persisted sessions.
- B. Use Rocket as the base, discard the KRISHI-X starter. Rejected: the required structure, Next.js and portals would be retrofitted later anyway.
- C. Run Rocket as a separate service. Rejected: two backends and two databases to maintain.

## Decided
- Approach A.
- Database: PostgreSQL + PostGIS via Docker (docker-compose), Alembic migrations.
- Stack per the spec: FastAPI/Pydantic/SQLAlchemy/Alembic, Next.js/React/TS/Tailwind/Recharts, Redis/Celery later, Flutter later.
- Build one phase at a time.

## Scope: all of India
All states, all mandis and commodities in the government feed. The current snapshot (`data/raw/9ef84268-..._2026-11-13.csv` in Rocket) has 16,038 rows for one day: 29 states, 504 districts, 1,675 markets, 242 commodities, with min/max/modal price, variety and grade. It has no arrivals and no coordinates.

## Data sources verified on 2026-11-13
- `9ef84268-d588-465a-a308-a864a43d0070` "Current Daily Price ... (Mandi)": today only, works with the public sample key.
- `35985678-0d79-46b4-9ed6-6f13308a1d24` "Variety-wise Daily Market Prices": **83 million rows of history from 2010**, filterable by date/state/commodity (about 16k rows per day). The public sample key returns only 10 rows per call, so a backfill needs the user's own free data.gov.in key. Plan: backfill the last 3 years (enough for yearly seasonality plus backtests; roughly 18M rows, a few GB in Postgres), then append daily.
- Mandi coordinates: geocoded once from market + district + state with OpenStreetMap Nominatim (1 request/s, about 30 minutes for 1,675 markets), cached in `mandis`, marked `approximate`. Farmer locations are geocoded the same way (provider behind an interface, results cached).
- No arrivals data in either resource, so arrival-based features wait for another source.

## Constraints found
- Docker 29.9 + Compose are installed: PostgreSQL/PostGIS runs in Docker. SQLite stays only as a fast option for unit tests.
- Python 3.14: all needed wheels exist (ortools 9.15, statsmodels 0.15, pandas 3.1, lightgbm, xgboost). Rocket was written against pandas 2; its tests are the check.
- Agmarknet 2.0 needs a captcha, so it is not scraped. e-NAM needs permitted access.
- Rocket's buyers, warehouses, transporters are fictional DEMO data and stay labelled so until real providers or user registrations exist.

## Phase 1 design (this approval covers building it)
Goal: one repo, one backend, the voice intake working end to end against the database, and the agent architecture in place.

1. **Port Rocket into `backend/app/`** keeping Rocket's logic and tests intact:
   - `conversation/profile_agent.py` <- `profile.py` (replaces KRISHI-X `conversation/manager.py`; adds en/hi/mr, correction flow, read-back, confirm gate). Session state persisted via the existing DB session table instead of memory.
   - `agents/` <- `agents.py`, `agents/orchestrator.py` <- `orchestrator.py`.
   - `ml/forecast.py` <- `forecast.py`; `services/costs.py`, `services/logistics.py`, `services/geo.py`, `services/llm.py`, `services/orders.py`; `services/adapters/agmarknet_datagov.py` <- `adapters.py`; `core/meta.py` <- `meta.py`; `services/demo_data.py` <- `demo_data.py` (stays labelled DEMO).
   - Rocket's 13 tests move to `backend/tests/` and must pass; KRISHI-X `test_chat.py` is updated to the new agent's behaviour.
2. **Database.** SQLAlchemy models + first Alembic migration for the Phase 1 tables: `users` (role enum: farmer, fpo, buyer, transporter, warehouse, admin), `farmer_profiles`, `farmer_inventory` (qty_kg + original qty/unit), `commodities`, `crop_varieties`, `mandis` (lat/lon), `mandi_prices`, `data_sources`, `audit_logs`, plus the existing conversation sessions table. The 13 Nov CSV is imported as real data (`verification_status=official`, source data.gov.in) so current prices shown are real; mandis without coordinates yet are listed by state/district but excluded from distance ranking. Common provenance columns (source_id, observed_at, updated_at, verification_status) as a mixin. On PostgreSQL the migration adds a PostGIS `geography(Point)` column and GiST index on `mandis`; on SQLite it is skipped and distance stays haversine x road factor (Rocket's method). Remaining spec tables arrive with the phase that uses them. Startup `create_all` is replaced by `alembic upgrade head`.
3. **API.** `/api/chat` (profile agent; on confirmation saves profile + inventory row), `/api/voice/transcribe` (existing, optional faster-whisper), `/api/plan` (orchestrator, only for a confirmed profile, else 409), `/api/forecast`, `/api/series`, `/api/orders`, `/health`. Pydantic schemas in `schemas/`.
4. **Web app.** Next.js opens straight into the assistant: big mic button (browser Web Speech API for STT where available, else record + backend transcribe), text box, language switch (en/hi/mr), replies spoken via `speechSynthesis`, live profile card, confirm/correct buttons. After confirmation it calls `/api/plan` and shows a first results view ported from Rocket's `index.html` (ranked net-realization options with deductions, sell vs hold, freshness and DEMO labels). Tailwind added; Recharts for the price/forecast chart. Visual direction follows Rocket's "settlement-slip" redesign (`design/krishimitra-redesign/`: desktop result, phone assistant, phone result).
5. **Infrastructure.** `docker-compose.yml` (postgis/postgis, backend, web), `backend/Dockerfile`, `apps/web/Dockerfile`, `.env.example` updated (`DATABASE_URL`, `DATA_GOV_API_KEY`, `KRISHIX_LLM`, `CORS_ORIGINS`), README run steps for both Docker and SQLite.

Done when: pytest passes; `docker compose up` brings up PostGIS, backend and web; `alembic upgrade head` runs on Postgres; `next build` succeeds; in the browser a farmer can speak or type "1000 kg tomatoes near Ponda, Goa", answer follow-ups, correct a detail, confirm, and see ranked options where real prices are labelled with source and date and anything synthetic (buyers, warehouses, transporters, forecasts on demo series) is labelled DEMO DATA. Forecasts on real data honestly show insufficient history until the Phase 3 backfill.

## Later phases (outline; each detailed at its start)
2 LLM-backed multilingual extraction (behind `services/llm.py`, rule-based fallback), TTS polish. 3 Mandi + retail ingestion, history tables, validation. 4 Forecast pipeline: add SARIMA, XGBoost, LightGBM to Rocket's backtest/gate, model registry tables. 5 Sell vs Hold + Net Realization against DB data. 6 Cold storage tables, enquiries. 7 Transport quotes, OR-Tools shared loads. 8 Buyer marketplace and role portals with auth + RBAC. 9 Notifications, tracking, accounting, Celery jobs. 10 Hardening, CI, deployment.

## Left to the builder
How finely to split `agents/` into files, exact styling within a green/earth palette, test fixture layout.

## Calls I made (check these)
- SQLite only for fast unit tests; Postgres in Docker for everything else.
- Backfill depth 3 years (Phase 3); needs the user's own data.gov.in key.
- Nominatim for geocoding (free, no key); results marked approximate.
- Only the Phase 1 tables in the first migration; the rest come with their phase.
- Browser Web Speech API first for STT/TTS, backend Whisper as fallback.
- Authentication and RBAC deferred to Phase 8; Phase 1 uses an anonymous session id.
- Rocket's hard-coded demo place list is replaced by geocoding, so any Indian village or town resolves.
- Mandi geocoding runs in Phase 1 (needed for distance ranking), the 3-year price backfill in Phase 3.
