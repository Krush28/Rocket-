# KRISHI-X Phase 1 (foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One repo and one backend: Rocket's engine ported into KRISHI-X's layout, PostgreSQL/PostGIS with Alembic, the real 13 Nov all-India price CSV imported, mandis geocoded, a DB-persisted voice/text intake with confirmation, and a Next.js assistant that shows ranked net-realization options.

**Architecture:** FastAPI app in `backend/app` with layers `api/ core/ conversation/ agents/ ml/ services/ models/ repositories/`. Agents keep Rocket's contract (`fn(state) -> {"data", "meta"}`) but read mandis and prices through `repositories/market_data.py`, which serves real DB rows when any exist and Rocket's labelled demo series otherwise. Next.js talks to the API over JSON.

**Tech Stack:** Python 3.14, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, GeoAlchemy2, psycopg 3, pandas, statsmodels, scikit-learn, OR-Tools, httpx; Next.js 14, React 18, TypeScript, Tailwind, Recharts; Docker Compose with `postgis/postgis:16-3.4`.

**Spec:** `docs/superpowers/specs/2026-11-13-krishi-x-design.md`

**Rocket source:** `git clone --branch krishimitra https://github.com/Krush28/Rocket-.git` into a scratch dir (call it `$ROCKET`). Code lives in `$ROCKET/krishimitra/backend/app`, the CSV in `$ROCKET/data/raw/9ef84268-d588-465a-a308-a864a43d0070_2026-11-13.csv`, the UI designs in `$ROCKET/design/krishimitra-redesign/`.

## Global Constraints
- Never fabricate live prices, arrivals, buyer offers, phone numbers or warehouse capacity. Synthetic values carry the label `DEMO DATA`.
- Transport costs are labelled `VERIFIED QUOTE` or `ESTIMATE`. Retail prices are consumer context, never shown as farmer selling prices.
- Every agent output carries `core.meta.meta(...)` (source, verification, observed_at, last_updated, freshness_days, confidence, error).
- Money maths only in `services/costs.py`; the LLM never computes numbers.
- Market work (`/api/plan`, orchestrator) starts only after the farmer confirms the profile.
- Quantities are stored as `qty_kg` plus `original_qty` and `original_unit`.
- No Aadhaar fields anywhere. No secrets in code; config comes from env (`DATABASE_URL`, `DATA_GOV_API_KEY`, `KRISHIX_LLM`, `OLLAMA_URL`, `OLLAMA_MODEL`, `CORS_ORIGINS`, `GEOCODER_URL`).
- Nominatim calls: at most 1 request/s, `User-Agent: KRISHI-X/0.1`, `countrycodes=in`. Results are cached and marked `approximate`.
- Forecasts on fewer than 120 days of history return Rocket's insufficient-data result.

## Review Focus
1. **Unresolvable place or geocoder down** ("near xyzabc", network off): the assistant re-asks for the location; it never answers with a 500. Test in Task 6.
2. **A crop with no prices near the farm** (crop exists in the catalogue, but no mandi within 450 km has a row): `/api/chat` confirmation returns a plan whose recommendation is `INSUFFICIENT INFORMATION` with a reason, not a crash. Test in Task 5.
3. **Re-importing the same CSV, or rows with `NA` or zero prices:** the import is idempotent and bad rows are skipped and counted. Test in Task 3.
4. **A crop without shelf-life parameters** (for example `Brinjal`): hold options are skipped with reason "no shelf-life data", and sell-now options are still ranked. Test in Task 5.
5. **A browser without Web Speech API** (Firefox): the mic falls back to MediaRecorder upload to `/api/voice/transcribe`, and typing always works. Checked in Task 8.

---

### Task 1: git init and port Rocket into the KRISHI-X layout

**Files:**
- Create: `.gitignore` (merge Rocket's entries: `.venv`, `__pycache__`, `*.db`, `.pytest_cache`, `.env`, `node_modules`, `.next`)
- Create from Rocket, imports rewritten: `backend/app/core/meta.py` (<- meta.py), `backend/app/services/{costs,logistics,geo,llm,orders,demo_data}.py`, `backend/app/services/adapters/agmarknet_datagov.py` (<- adapters.py), `backend/app/ml/forecast.py`, `backend/app/agents/agents.py`, `backend/app/agents/orchestrator.py`, `backend/app/conversation/profile_agent.py` (<- profile.py)
- Create: `backend/tests/test_core.py`, `backend/tests/conftest.py` (from Rocket, imports rewritten)
- Delete: `backend/app/conversation/manager.py`, `backend/tests/test_chat.py` (replaced by Task 7 tests), `backend/krishi_x.db`
- Modify: `backend/requirements.txt` = existing lines + `pandas numpy statsmodels scikit-learn ortools alembic geoalchemy2`

**Interfaces:**
- Produces: Rocket's public functions, unchanged in name and signature: `orchestrator.run(profile, assumption_override=None) -> dict`, `profile_agent.chat(sid, text, lang=None) -> dict`, `forecast.forecast(crop, mandi) -> dict`, `costs.*`, `logistics.match(...)`, `orders.create/get/list_all/event`.

- [ ] **Step 1:** `git init` at the repo root, add `.gitignore`, commit the existing starter as-is: `git commit -m "chore: import existing KRISHI-X starter"`.
- [ ] **Step 2:** Copy the Rocket modules to the paths above. Rewrite relative imports (`from . import agents as A` becomes `from app.agents import agents as A`, and so on). Delete Rocket's `main.py` (its routes move in Task 7).
- [ ] **Step 3:** Install: `.venv/Scripts/python -m pip install -r requirements.txt`. Expected: success.
- [ ] **Step 4:** Run `python -m pytest tests/test_core.py -q`. Expected: 17 passed. Fix pandas 3 incompatibilities in the ported code only (no test edits unless a test imports a moved path).
- [ ] **Step 5:** Commit `feat: port Rocket engine into KRISHI-X layout`.

### Task 2: Config, models, Alembic, Postgres in Docker

**Files:**
- Create: `backend/app/core/config.py`: `settings` built from env with `database_url` (default `postgresql+psycopg://krishix:krishix@localhost:5432/krishix`), `cors_origins`, `data_gov_api_key`, `geocoder_url` (default `https://nominatim.openstreetmap.org/search`)
- Modify: `backend/app/db/database.py`: use `settings.database_url`; remove `init_db`/`create_all`
- Create: `backend/app/models/{__init__,base,users,catalog,markets,conversation,audit}.py`
- Create: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/0001_phase1.py`
- Create: `docker-compose.yml` with service `db` (`postgis/postgis:16-3.4`, user/password/db `krishix`, port 5432, named volume `pgdata`). The backend and web services come in Task 9.
- Test: `backend/tests/test_migrations.py`

**Interfaces:**
- Produces (SQLAlchemy 2 typed models, all with `id` int PK, `created_at` and `updated_at`):
  - `ProvenanceMixin`: `source_id -> data_sources.id` (nullable), `observed_at`, `verification_status` (str: `official|verified|unverified|estimate|demo`).
  - `User(role: Enum[farmer,fpo,buyer,transporter,warehouse,admin], phone: str|None unique, display_name, preferred_language)`.
  - `FarmerProfile(user_id -> users nullable, session_id unique, name, preferred_language, location_name, lat, lon, can_store, sell_pref)`.
  - `FarmerInventory(farmer_profile_id, commodity_id, variety, grade, qty_kg, original_qty, original_unit, harvest_date, ready, status default "available")`.
  - `Commodity(name unique, key unique lowercase)`, `CropVariety(commodity_id, name, unique(commodity_id, name))`.
  - `Mandi(name, district, state, lat, lon, geo_status: str default "pending" in pending|approximate|not_found, unique(name, district, state))`, index on (state, district).
  - `MandiPrice(+Provenance; mandi_id, commodity_id, variety, grade, price_date: date, min_price, max_price, modal_price, unit default "Rs/quintal", unique(mandi_id, commodity_id, variety, grade, price_date))`, index on (commodity_id, price_date).
  - `DataSource(name unique, kind, url, licence_note)`, `AuditLog(actor, action, entity, entity_id, detail JSON, at)`, `ConversationSession(session_id PK, state JSON, confirmed bool, updated_at)`, `GeocodeCache(query unique, lat, lon, display_name, status, provider)`.
- Migration `0001`: creates all of the above. When `op.get_bind().dialect.name == "postgresql"` it also runs `CREATE EXTENSION IF NOT EXISTS postgis`, adds `mandis.geog geography(Point,4326)` and a GiST index `ix_mandis_geog`.

- [ ] **Step 1: Write the failing test** `test_upgrade_and_downgrade_on_sqlite(tmp_path)`: runs `alembic upgrade head` then `downgrade base` against `sqlite:///{tmp_path}/t.db` via `alembic.command`; asserts table names include `mandis`, `mandi_prices`, `farmer_inventory`, `conversation_sessions`, `geocode_cache` after the upgrade and are gone after the downgrade.
- [ ] **Step 2:** Run it. Expected: FAIL (no alembic config).
- [ ] **Step 3:** Implement the models, `migrations/env.py` (reads `settings.database_url`, honours `-x url=` and the `config.attributes["url"]` override) and `0001_phase1.py`.
- [ ] **Step 4:** Run it. Expected: PASS.
- [ ] **Step 5:** `docker compose up -d db`, then `alembic upgrade head`. Expected: no errors; `docker compose exec db psql -U krishix -c "\d mandis"` shows column `geog`.
- [ ] **Step 6:** Commit `feat: models, alembic 0001, postgis compose`.

### Task 3: Import the data.gov.in CSV into the database

**Files:**
- Create: `backend/app/services/ingest/datagov_csv.py`
- Modify: `backend/app/services/adapters/agmarknet_datagov.py`: `upsert()` writes through `datagov_csv.upsert_rows(session, rows)` instead of its own SQLite file; `live_mode()` becomes `select exists(mandi_prices)`
- Copy: the CSV to `data/raw/9ef84268-d588-465a-a308-a864a43d0070_2026-11-13.csv`
- Test: `backend/tests/test_ingest.py`; `tests/conftest.py` gains a `db` fixture (fresh SQLite file, alembic upgrade, yields `Session`, and monkeypatches `app.db.database.SessionLocal`)

**Interfaces:**
- Consumes: Rocket's `parse_record(r) -> dict|None` (keys `market,state,district,commodity,variety,grade,date,min_price,max_price,modal_price`).
- Produces: `import_csv(session, path: str) -> dict` returning `{"rows_read", "rows_upserted", "rows_skipped", "mandis_created", "commodities_created"}`; `upsert_rows(session, rows: list[dict], source_name="data.gov.in 9ef84268") -> int`. Rows get `verification_status="official"` and `observed_at` = file mtime. CLI: `python -m app.services.ingest.datagov_csv <path>`.

- [ ] **Step 1: Write the failing tests:** a 4-row fixture CSV (2 good rows, 1 with `NA` modal, 1 with modal `0`) using the real header `State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_x0020_Price,Max_x0020_Price,Modal_x0020_Price`.
  - `test_import_counts_and_skips`: `rows_upserted == 2`, `rows_skipped == 2`.
  - `test_reimport_is_idempotent`: importing twice leaves 2 `MandiPrice` rows.
  - `test_commodity_key_lowercase`: `Commodity.key == "tomato"` for "Tomato".
- [ ] **Step 2:** Run. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement. Use pandas `read_csv` + Rocket's `parse_record`, and a dialect-agnostic upsert (select existing, then insert or update) in batches of 1,000. `Commodity.key` = lowercased name with any `(...)` suffix stripped.
- [ ] **Step 4:** Run `pytest tests/test_ingest.py tests/test_core.py -q`. Expected: all pass. Update Rocket's three live-adapter tests to use the `db` fixture where they touched the old SQLite path.
- [ ] **Step 5:** Run against Postgres: `python -m app.services.ingest.datagov_csv ../data/raw/9ef84268-...csv`. Expected: about 16,000 upserted, 1,675 mandis, 242 commodities.
- [ ] **Step 6:** Commit `feat: import data.gov.in price CSV into postgres`.

### Task 4: Geocoding service and mandi geocoding job

**Files:**
- Create: `backend/app/services/geocoding.py`, `backend/scripts/geocode_mandis.py` (script lives in `backend/scripts` so it can import `app`)
- Test: `backend/tests/test_geocoding.py`

**Interfaces:**
- Produces: `geocode(session, query: str, *, client: httpx.Client | None = None) -> dict | None` returning `{"name", "lat", "lon", "status": "approximate"}` or `None`. It looks in `GeocodeCache` first; on a miss it calls Nominatim (`q=query, format=jsonv2, countrycodes=in, limit=1`), sleeping to keep 1 req/s, and caches hits and `not_found` alike. Network errors return `None` and are not cached.
- `geocode_mandis(session, limit: int | None = None) -> dict`: for each `Mandi` with `geo_status == "pending"`, tries `"{name}, {district}, {state}"`, then `"{district}, {state}"` (that fallback still counts as `approximate`), and sets `lat`/`lon`/`geo_status` (plus `geog` on Postgres). Returns counts.

- [ ] **Step 1: Write the failing tests** with an `httpx.MockTransport`:
  - `test_cache_hit_skips_network`: the second call makes 0 requests.
  - `test_network_error_returns_none_uncached`
  - `test_mandi_falls_back_to_district`: the first query returns `[]`, the second returns a point; asserts `geo_status == "approximate"`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Strip `APMC`, `(F&V)` and similar suffixes from mandi names before querying.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Run `python scripts/geocode_mandis.py` in the background against Postgres (about 30–60 min). Report the counts when done. Later tasks don't block on it; mandis still `pending` are excluded from distance ranking.
- [ ] **Step 6:** Commit `feat: nominatim geocoding with cache; mandi geocode job`.

### Task 5: Market-data repository; agents read from it

**Files:**
- Create: `backend/app/repositories/market_data.py`
- Modify: `backend/app/agents/agents.py` (`mandi_discovery`, `price_intelligence`, `market_activity`, `price_forecast`, `sell_vs_hold`), `backend/app/ml/forecast.py` (`forecast(crop, mandi_key)` reads `market_data.series`)
- Test: `backend/tests/test_market_data.py`

**Interfaces:**
- Produces:
  - `live() -> bool` (any `MandiPrice` row).
  - `mandis_with_prices(crop: str) -> list[dict]`: each dict is `{"key": str, "name", "district", "state", "lat", "lon"}`, only geocoded mandis. In live mode `key = str(mandi.id)`; in demo mode `key` = Rocket's mandi name from `demo_data.MANDIS`.
  - `series(crop: str, mandi_key: str) -> pd.DataFrame` with Rocket's columns `date, modal, min, max` (+`arrivals_t` only in demo).
  - `last_updated(crop, mandi_key) -> datetime`, `source_label(crop, mandi_key) -> str` (`"data.gov.in (Agmarknet) daily price, official"` or the DEMO label).
  - `crop_params(crop: str) -> dict | None`: Rocket's `demo_data.CROPS[crop]` or `None`.
  - `crop_catalogue() -> dict[str, list[str]]`: key -> aliases (Rocket aliases merged with `Commodity` keys from the DB).
- In live mode it never falls back to demo prices (Rocket rule). Demo mode is used only when the DB has no `MandiPrice` rows.
- Agents: `mandi_discovery` keeps its 450 km radius and top 7 rule over `mandis_with_prices` (haversine, shortcut: Python scan of at most 1,675 mandis, move to PostGIS `ST_DWithin` once the row count makes it slow). `sell_vs_hold`: when `crop_params` is `None`, `holds = []` and the decision reason is "no shelf-life data for this crop; hold not evaluated".

- [ ] **Step 1: Write the failing tests** (`db` fixture, rows inserted directly):
  - `test_live_mode_excludes_ungeocoded_and_never_demo`: 2 mandis with tomato prices, 1 pending; `mandis_with_prices("tomato")` returns 1, and `series` for an unknown key is empty.
  - `test_orchestrator_live_ranks_real_mandi`: the profile is near the geocoded mandi; options contain that mandi, and `prices` meta verification is `official`.
  - `test_unknown_shelf_life_skips_hold`: crop `brinjal` with prices; `sell_vs_hold.holds == []`, the reason mentions shelf-life, and the sell-now option exists.
  - `test_no_mandi_in_radius_insufficient`: farm 1,000 km away; the orchestrator result has recommendation action `INSUFFICIENT INFORMATION` (or a failed Mandi Discovery trace with that reason) and no exception.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the repository and the agent changes.
- [ ] **Step 4:** Run the full suite. Expected: all pass (Rocket tests still run in demo mode with an empty DB).
- [ ] **Step 5:** Commit `feat: market-data repository; agents read live DB prices`.

### Task 6: Profile agent: catalogue crops, geocoded places, persisted sessions

**Files:**
- Modify: `backend/app/conversation/profile_agent.py`
- Create: `backend/app/repositories/sessions.py`
- Test: `backend/tests/test_profile_agent.py`

**Interfaces:**
- Consumes: `market_data.crop_catalogue()`, `geocoding.geocode(session, query)`.
- Produces: `chat(sid, text, lang=None, *, db=None) -> dict` with the same return shape as Rocket's. Sessions are loaded and saved via `sessions.load(db, sid) -> dict|None` and `sessions.save(db, sid, state: dict, confirmed: bool)`, falling back to the in-memory dict when `db` is None (keeps Rocket tests valid). Tuples in history are stored as lists.
- `on_confirm(db, profile: dict) -> int`: creates a `FarmerProfile` + `FarmerInventory` and returns the inventory id. It is called by the route, not by `chat`.
- Location: Rocket's `PLACES` match first. Else, when `awaiting == "location"` or the text matches `\bnear\s+(.+)`, the place text goes to `geocode`; a hit sets `location={"name","lat","lon","status":"approximate"}`, a miss re-asks. The re-ask copy drops the "demo list" hint.

- [ ] **Step 1: Write the failing tests:**
  - `test_geocoded_place_any_india`: monkeypatch `geocode` to return Ludhiana; "500 kg wheat near Ludhiana" fills location.
  - `test_geocoder_down_reasks`: `geocode` returns None; the reply contains the location question and `state == "collecting"`.
  - `test_catalogue_crop_from_db`: commodity `Brinjal` in the DB; "I have 10 quintal brinjal" gives `crop == "brinjal"` and `qty_kg == 1000`.
  - `test_session_persists_across_calls`: two `chat` calls with a fresh in-memory dict between them; the slots survive via the DB.
  - `test_hindi_quintal`: "10 क्विंटल प्याज" gives `qty_kg == 1000`, `lang == "hi"`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite. Expected: all pass.
- [ ] **Step 5:** Commit `feat: profile agent with catalogue crops, geocoding, db sessions`.

### Task 7: API routes

**Files:**
- Modify: `backend/app/main.py` (CORS from settings, routers, `/health`, rate limit)
- Create: `backend/app/api/routes/{chat,plan,market,orders,admin}.py`; keep `voice.py`
- Modify: `backend/app/schemas/chat.py` and add `schemas/plan.py`
- Test: `backend/tests/test_api.py`

**Interfaces (all under `/api`):**
- `POST /chat {session_id?: str, text: str, lang?: "en"|"hi"|"mr"}` returns Rocket's chat dict + `session_id` + `inventory_id` (once confirmed) + `plan` (orchestrator result, only when `done`).
- `POST /plan {session_id}` returns the orchestrator result for that confirmed session; 409 `{"detail": "profile not confirmed"}` otherwise, 404 for an unknown session.
- `GET /forecast?crop=&mandi_key=` and `GET /series?crop=&mandi_key=&days=180`: 404 when the crop or mandi is unknown.
- `GET /orders`, `POST /orders {option, profile}`, `POST /orders/{id}/event {event, data?}` (Rocket semantics).
- `POST /admin/import {path}` calls `import_csv` (path must be under `data/raw/`, else 400). `GET /health` returns `{"status": "ok", "db": bool, "data_mode": "LIVE"|"DEMO DATA", "last_price_date"}`.
- `POST /voice/transcribe` is unchanged.
- Rate limit: in-process sliding window, 60 req/min per client IP on `/api/*`, 429 beyond. Shortcut: per-process memory; move to Redis when running more than one worker.

- [ ] **Step 1: Write the failing tests** (`TestClient` + `db` fixture):
  - `test_chat_flow_to_confirmed_plan`: messages "1000 kg tomato", "near Ponda" (monkeypatched geocode), "yes", "no", "yes" give a final response with `done == True`, `inventory_id` an int and `plan["options"]` a list.
  - `test_plan_409_before_confirm`
  - `test_admin_import_rejects_outside_data_raw`
  - `test_rate_limit_429`
  - `test_health_reports_mode`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite. Expected: all pass.
- [ ] **Step 5:** Run `uvicorn app.main:app --port 8000` against Postgres and `curl` the chat flow once. Expected: a plan with real prices from 13 Nov 2026.
- [ ] **Step 6:** Commit `feat: phase 1 API`.

### Task 8: Web app: voice-first assistant and results

**Files:**
- Modify: `apps/web/package.json` (add `tailwindcss postcss autoprefixer recharts`), `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`
- Create: `apps/web/tailwind.config.ts`, `apps/web/postcss.config.mjs`, `apps/web/app/globals.css`, `apps/web/lib/api.ts`, `apps/web/lib/speech.ts`, `apps/web/components/{Assistant,ProfileCard,Results,OptionSlip,PriceChart,DataBadge}.tsx`

**Interfaces:**
- Consumes: Task 7's `/api/chat`, `/api/series`, `/api/voice/transcribe`.
- `lib/speech.ts`: `listen(lang): Promise<string>` (Web Speech API `SpeechRecognition` with `lang` mapped en→`en-IN`, hi→`hi-IN`, mr→`mr-IN`; if unsupported, records with MediaRecorder for up to 15 s and posts to `/api/voice/transcribe`), and `speak(text, lang)` (`speechSynthesis`, no-op if unsupported).
- Visual direction: read `$ROCKET/design/krishimitra-redesign/{Main,Phone-Assistant,Phone-Result}.dc.html` and port its "settlement-slip" look (layout, palette, type scale) into Tailwind. Mobile-first, touch targets at least 48 px, body text at least 18 px, mic button at least 96 px, visible focus rings, `aria-live="polite"` on the assistant reply.
- `Results` shows: the best option as a settlement slip (gross revenue, each deduction line, net), the other options ranked, sell-vs-hold rows, a source/date badge per price (`DataBadge` turns amber with "DEMO DATA" when `meta.verification == "demo"`), `ESTIMATE` labels on transport, retail labelled "consumer price, not your selling price", and a forecast that says "Not enough price history yet" when insufficient.

- [ ] **Step 1:** Implement the components and `page.tsx` (opens directly into `Assistant`; after `done` it renders `Results` from `plan`).
- [ ] **Step 2:** `npm install && npm run build`. Expected: build succeeds with no type errors.
- [ ] **Step 3:** Start the backend and `npm run dev`; in the browser pane run the Task 7 chat flow by typing, and check: the profile card fills, the read-back appears, "no" lets you correct, "yes" shows results with 13 Nov source badges, and the layout at 375 px width has no horizontal scroll. Also check the mic button with Web Speech unavailable: the fallback path starts recording.
- [ ] **Step 4:** Commit `feat: voice-first assistant and results UI`.

### Task 9: Docker for the whole stack, env, docs

**Files:**
- Create: `backend/Dockerfile` (python:3.12-slim [3.14 slim images may lag], installs requirements, runs `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`), `apps/web/Dockerfile` (node:22-alpine, build + `next start`)
- Modify: `docker-compose.yml` (add `backend` with depends_on db healthy, `web`), `.env.example`, `README.md` (Docker run, local run, CSV import, geocode job, what is real vs demo), `docs/ROADMAP.md` (tick Phase 1), `docs/ARCHITECTURE.md` (layer map, agent pipeline, data flow)

- [ ] **Step 1:** Write the files.
- [ ] **Step 2:** `docker compose up -d --build`, then `docker compose exec backend python -m app.services.ingest.datagov_csv /data/raw/...csv` (mount `./data` at `/data`). Expected: `GET http://localhost:8000/health` returns `{"status":"ok","db":true,"data_mode":"LIVE",...}` and http://localhost:3000 loads the assistant.
- [ ] **Step 3:** Full `pytest -q`. Expected: all pass.
- [ ] **Step 4:** Commit `chore: dockerised stack, env and docs for phase 1`.
