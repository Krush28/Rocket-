# KRISHI-X — repository structure (living)

> Update with [PRD.md](PRD.md) in every commit that adds, moves or removes a file. Request flow and design are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Request flow (one voice turn)
```
browser (apps/web)  ─POST /api/agent {session_id, text, lang?}─▶  api/routes/agent.py
  └▶ agents/action_agent.handle
       ├─ before the plan: conversation/intake.step   (crops → qty → place → ready → store → read-back → yes)
       │                     └ profile_agent.extract  (crop, qty+unit, place via services/geocoding → gazetteer → Nominatim)
       └─ after the plan:  route(text) rules → tool  (LLM pick_tool only if rules say "unknown")
                             └ run_tool → orchestrator.run (12 agents) → core/i18n.localize(plan, lang)
  ◀─ {reply, actions:[plan|tab|order|lang|reset], crops, state, lang}
```

## Files
```text
docker-compose.yml        db (PostGIS 16) · backend (FastAPI :8000, uvicorn --reload) · web (Next 14 :3000, production build)
.env.example              every setting (no secrets in git)
data/raw/                 official data.gov.in CSV snapshots (tracked, small)
data/raw/geonames/        GeoNames dumps (GITIGNORED, heavy; see PRD §6)
docs/PRD.md               living product doc: rules, status, gaps, roadmap, changelog
docs/STRUCTURE.md         this file
docs/ARCHITECTURE.md, ROADMAP.md, superpowers/specs|plans/   design spec and Phase 1 plan

backend/
  app/main.py             FastAPI app, routers, /health, startup warm-up (Piper, LLM)
  app/core/               config.py (env settings) · meta.py (provenance) · ratelimit.py (60/min/IP)
                          i18n.py (EN→hi/mr template translation; place() = Devanagari names; plan["names"])
  app/db/database.py      engine, SessionLocal, Base
  app/models/             core.py (users, farmer profile/inventory, conversation sessions, geocode cache, audit)
                          markets.py (data sources, commodities, mandis, mandi_prices, places, name_translations)
  migrations/versions/    0001 phase-1 schema (+PostGIS geog) · 0002 gazetteer (places, name_translations) · 0003 state_price_history · 0004 forecast_cache
  app/repositories/       market_data.py (LIVE DB vs DEMO, cached reads; clear() after imports)
                          farmers.py (device memory) · sessions.py (conversation state)
  app/conversation/       profile_agent.py (extract slots, yes/no, language detect, units, NAMES)
                          intake.py (multi-crop intake state machine, en/hi/mr phrases)
  app/agents/             agents.py (the 12 agents) · orchestrator.py (runs them, localizes)
                          brain.py (local-LLM tool planner + grounded answers; validates every call) · action_agent.py (voice tools: compare, forecast, price_of, add/remove/edit lots,
                          set_location, assumptions, orders; replies dict R in en/hi/mr; STATE = in-memory cache)
  app/services/           crops.py (every crop: hi/mr names, aliases, shelf life, seasonality) · costs.py (ALL money maths) · spoilage.py · confidence.py · logistics.py (OR-Tools)
                          geocoding.py (gazetteer first, Nominatim cached, fuzzy last) · gazetteer.py (GeoNames load/find/dev_name/romanize)
                          adapters/agmarknet_datagov.py (CSV/API import) · adapters/mandi_api.py (keyless Mandi API, background job) · orders.py (demo order state machine, SQLite)
                          llm.py (Ollama, optional) · tts.py (Piper) · speech.py (faster-whisper) · demo_data.py (DEMO only) · geo.py
  app/ml/forecast.py      baselines, ETS, lag-Ridge + backtest gate
  app/api/routes/         agent · chat (/api/chat, /api/plan) · market (meta, forecast, series) · orders · admin (import/refresh, X-Admin-Token) · voice
  scripts/                geocode_mandis.py · load_gazetteer.py
  tests/                  pytest, temp SQLite per test (conftest.py). test_voice_fixes.py = QA regressions + gazetteer

apps/web/                 Next.js + Tailwind + Recharts
  app/page.tsx            controller: device id, language, agent() calls, applies actions, hands-free mic loop
  components/             Landing (voice-first start) · AgentBar (command bar) · Voice (mic, lang switch, send form, ResetButton)
                          Results (settlement slip; mandi names via plan.names) · PriceChart
  lib/                    api.ts (types + fetchers) · i18n.ts (UI dictionary en/hi/mr, cropName, unitName) · speech.ts
apps/mobile/              Flutter app placeholder (README only)
```

## Conventions
- Every agent output is `{"data", "meta"}` with provenance (`core/meta.py`).
- Mandi key = `"<market>, <district>, <state>"`, never translated (`SKIP_KEYS`). Display names go through `plan.names` / `i18n.place`.
- New farmer-facing text: add en/hi/mr in the same place (`action_agent.R`, `intake.T`, `profile_agent.*`, `core/i18n.TEMPLATES`, `apps/web/lib/i18n.ts`).
- Windows host: the backend runs only in Docker (App Control blocks pandas DLLs). On Git Bash use `MSYS_NO_PATHCONV=1` for container paths.
