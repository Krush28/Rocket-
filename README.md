# KRISHI-X

**Where does a farmer keep the most money after costs?** KRISHI-X is a voice-first, multilingual mandi price intelligence and farm-to-market platform. It ranks every selling option by **expected net realization** (sale revenue minus transport, handling, storage and expected loss), not by the highest displayed price, and says honestly when it does not know.

Built on the Rocket / KrishiMitra engine (github.com/Krush28/Rocket-), ported into this layered monorepo.

## Run it (Docker, recommended)

```bash
cp .env.example .env          # optional: set ADMIN_TOKEN, DATA_GOV_API_KEY
docker compose up -d --build  # db (PostGIS) + backend :8000 + web :3000
```

- Web app: http://localhost:3000 (opens straight into the assistant)
- API docs: http://localhost:8000/docs · health: http://localhost:8000/health

The backend applies migrations (`alembic upgrade head`) on start.

### Load real prices (all India)

```bash
docker compose run --rm backend python -m app.services.adapters.agmarknet_datagov import /data/raw/9ef84268-d588-465a-a308-a864a43d0070_2026-11-13.csv
docker compose run --rm backend python scripts/geocode_mandis.py   # ~1 req/s, resumable; mandis appear in rankings once geocoded
```

New daily CSVs from data.gov.in (resource `9ef84268-…`, "Download" button) go in `data/raw/` and import the same way, or via `POST /api/admin/import {"path": "<file>.csv"}` with header `X-Admin-Token`.

On Git Bash for Windows, prefix container paths with `MSYS_NO_PATHCONV=1`.

### Tests

```bash
docker compose run --rm --no-deps backend python -m pytest tests -q
cd apps/web && npm run build
```

### Local web dev
`cd apps/web && npm install && npm run dev` (talks to the Dockerised backend on :8000).

> On this Windows machine the host Python venv cannot load pandas (Windows Application Control blocks its DLLs), so the backend runs and is tested in Docker.

## Voice agent (ported from Rocket)

- `POST /api/agent` is the whole farmer experience. **Multi-crop intake:** "I grow onion and tomato" asks the quantity for each, then the village, readiness and storage, reads it back, and runs nothing before "yes". **Actions:** "where should I sell", "show the forecast", "should I hold", "how sure are you", "book transport", "set hamali to 15", "create the order" (asks yes/no first), "track my order", "switch to Hindi", "start over".
- **Memory:** the browser keeps a random device id. Returning farmers get "welcome back" with their crops, and saying a crop name switches to it.
- **Speed:** rules answer first (every turn takes about 5–120 ms on real data). The local LLM is asked only when the rules do not understand, and only its tool name is trusted.
- **Languages:** EN / हिं / मरा. Agent replies, plan sentences and the whole UI follow the chosen language. Mandi and place names stay as the government data spells them.
- **Voice:** the browser's speech recognition and voice come first. Offline fallbacks run in the backend: Piper TTS (`/api/voice/speak`; hi_IN-priyamvada, mr_IN-google, en_US-amy) and faster-whisper STT (`/api/voice/transcribe`). Models download once into the `models` volume.
- **Local LLM (optional):** install [Ollama](https://ollama.com), run `ollama pull qwen3:4b`, and the backend uses it automatically via `host.docker.internal:11434`. If it is not running, the agent falls back to rules instantly.

## What is real and what is not

| Data | Status |
|---|---|
| Mandi wholesale prices (min/max/modal) | **Real**, official data.gov.in / Agmarknet, labelled with source and date. Only 13 Nov 2026 is loaded so far. |
| Mandi coordinates | Real places, **approximate** (OpenStreetMap geocoding of market + district + state). |
| Price forecasts | Need ~120 days of history per mandi. Until then: explicit "insufficient data", and holding is not recommended. |
| Arrivals | Not in this source; shown as unavailable. |
| Retail prices | No verified source yet: nothing shown (never presented as a farmer price). |
| Buyers, warehouses, transporters, shared-load pool | **DEMO DATA** (fictional, no phone numbers). Buyers hidden in LIVE mode; the simulated pool is never ranked next to real prices. |
| Costs (transport, hamali, commission) | **ESTIMATES** (editable placeholders), never shown as verified quotes. |

When the database has no price rows the app runs entirely on Rocket's labelled synthetic series (`DEMO DATA`).

## Repository layout

```text
apps/web/            Next.js + Tailwind + Recharts: voice assistant → settlement-slip results
apps/mobile/         Flutter app (later phase)
backend/app/
  api/routes/        chat, plan, market (meta/forecast/series), orders, admin, voice
  agents/            12 agents + explicit orchestrator (structured outputs with provenance meta)
  conversation/      Farmer Profile Agent (en/hi/mr, read-back, confirm gate)
  ml/                forecasting: baselines, ETS, lag-Ridge, backtest gate
  repositories/      market_data (LIVE DB vs DEMO), conversation sessions
  services/          costs (all money maths), logistics (OR-Tools), geocoding, adapters/, orders, speech, llm
  models/ db/ core/  SQLAlchemy models, engine, settings, rate limit, meta
backend/migrations/  Alembic (0001: Phase 1 schema + PostGIS geography on mandis)
data/raw/            official CSV snapshots
docs/                design spec, plans, architecture, roadmap
```

## Rules the code enforces
- Market work starts only after the farmer confirms the read-back.
- `Net = revenue − transport − handling − storage − financing − commission (if seller pays) − risk allowance`; spoilage reduces saleable quantity and is not subtracted twice.
- No Aadhaar, no fabricated prices, offers, phone numbers or capacity; estimates are labelled.
- Rate limit 60 req/min per client on `/api/*`; admin endpoints need `ADMIN_TOKEN`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/ROADMAP.md](docs/ROADMAP.md) and the [design spec](docs/superpowers/specs/2026-11-13-krishi-x-design.md).
