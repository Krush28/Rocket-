# KRISHI-X — Hackathon build plan (end-to-end system)

> Resume file for any coder/agent. Work top to bottom; tick boxes; after **every** small step: update this file + [PRD.md](PRD.md) §7 changelog, `git commit`, `git push`.
> Branch: `krishi-x-phase1` on github.com/Krush28/Rocket- (local branch `phase1-foundation` tracks it).

## The story we must demo (end to end)
Actors: **Farmer** (or **FPO / farmer-association head** selling for many members), **Transporter**, **Warehouse operator**, **Admin**.

1. **Farmer talks to the AI** (voice or text, EN/HI/MR, any vegetable / crop in the price feed — not just onion/tomato/potato).
   The agent understands free speech ("I've got about two tonnes of brinjal near Satara, ready now, can I keep it a week?"),
   fills what it can, asks only for what is missing, confirms, then works.
2. **Best mandi**: ranks mandis by *net in hand* (price − transport − hamali − commission − spoilage). Prices: Mandi API (live, keyless) + data.gov.in CSV.
3. **Sell or hold engine**: forecast (7/15/30 days) from price history → "sell now" vs "hold N days in storage X" with expected gain vs storage cost + spoilage.
4a. **Sell** → farmer says "create order" → **transport token** (booking ID + pickup, destination mandi, qty, est. fare) is sent to the **Transporter portal** → transporter accepts → picked up → delivered → farmer confirms sale price → order closed.
4b. **Hold** → nearby **warehouses / cold storage** shown (capacity, rate, distance) → farmer books → **Warehouse portal** confirms → later "sell from storage" → back to 4a.
5. **Done screen** → "Start a new task with the AI" returns to the agent (reset keeps nothing half-done).
6. Extras the agent can do on request: **live retail prices** ("what is tomato selling for in Mumbai shops?" → labelled retail context), **Government schemes for my state** (opens a Schemes screen with a curated database), price at any mandi, change costs, add/remove crops, track order, switch language.
7. **FPO head view**: list of member lots (aggregate qty per crop), pooled sale / shared truck.
8. **Notifications** (in-app bell, every actor) for each status change; background job refreshes prices daily.

## Hard rules (keep)
- Money maths only in Python tools; the LLM decides which tool and phrases answers. Never let the LLM invent a price/number.
- Label data: `LIVE` (Mandi API / data.gov.in), `DEMO` (synthetic: history backfill, warehouses, transporters, buyers, retail markup). Estimates ≠ quotes.
- Confirm (yes/no) before creating orders/bookings. No Aadhaar, no loans/credit products, no disease advisory.

## Mandi API findings (2026-11-13)
Base `https://mandi-api.onrender.com/v1` (keyless, 100 req / 15 min / IP). States: Maharashtra, Uttar Pradesh, Punjab, Madhya Pradesh, Karnataka.
- `/prices?state=&commodity=` → latest per market (≤200 rows, dates up to 2026-10-16). `/prices?state=&date=` → ≤200 rows (truncated).
- `/prices/history?state=&commodity=&market=` → market rows (~23 days, from 2026-07-28). Without market → state average series (`avg_modal_price`, `data_points`).
- Not enough for 120-day forecasts → **hybrid history**: real rows first, then a seasonal synthetic backfill *anchored to the real level* (per-crop seasonality), flagged `synthetic=True`, labelled "DEMO HISTORY" in UI and forecast meta.

## Phases / checklist (most important first)
### P1 Data + forecasting that works
- [x] `services/adapters/mandi_api.py`: client (throttled), import latest prices per state×crop into `mandi_prices` (source "mandi-api"), state-average history into `state_price_history`; geocode new mandis with the offline gazetteer.
- [x] `repositories/market_data.series`: hybrid series (real + synthetic backfill to 3 years, flagged); `history_source` in meta.
- [x] `ml/forecast.py`: add SARIMA (statsmodels SARIMAX) + LightGBM (fallback sklearn HistGradientBoosting) to the backtest gate.
- [x] Any crop: Hindi/Marathi names + shelf-life/perishability table for ~75 common crops (category defaults for the rest) — `services/crops.py`.
### P2 Smart agent (local LLM, Ollama qwen3:4b)
- [x] Agentic loop `agents/brain.py`: Ollama `/api/chat` with tools (JSON schemas) → execute deterministic tools → feed results back → final answer in farmer's language. Rules stay as instant fast path for exact commands; LLM handles everything else (free speech intake, multi-step questions, explanations).
- [x] LLM slot extraction for intake (crop/qty/unit/place/ready/storage from any sentence).
### P3 End-to-end operations
- [x] Postgres tables: `orders` (move from SQLite), `transport_jobs` (token), `warehouses`, `storage_bookings`, `notifications`, `users` (role, phone, name, state).
- [x] Demo login (phone + role, no password; labelled demo) and portals: `/transporter`, `/warehouse`, `/fpo`, `/admin`; farmer app stays `/`.
- [x] Flow (backend + agent): order → transport job → accept/pickup/deliver → sale confirmed → done screen; hold → storage booking → confirm → sell from storage.
- [x] Notifications bell (poll) for every actor.
### P4 Farmer extras
- [x] Schemes DB (central + 5 states, official links, "verify on official site", last reviewed) + `/schemes` screen + agent tool `show_schemes`.
- [x] Retail price tool (labelled retail context; demo markup over mandi modal unless a live source is added).
- [x] FPO head: member lots aggregate + pooled order.
### P5 Background + polish
- [ ] Daily import job (in-process scheduler), README/PRD, push.

## Status log
- 2026-11-13: plan written; Mandi API probed (works, short history).
- 2026-11-14: any-crop support done (crops.py: names, aliases incl. Hinglish/Devanagari, shelf life, hold limits, seasonality). Next: Mandi API importer + hybrid history.
- 2026-11-14: P1 data done. Mandi API importer (throttled, resumable, 6-hourly background job, `GET /api/admin/jobs`), state history paged by date window (real 2026-07-28..10-16), offline geocoding of new mandis via gazetteer. Hybrid 3-year history (`synthetic` column; prices shown as "today" always come from real rows). Forecast v2: + SARIMA + GBM (LightGBM if installed, else sklearn hist GBM) — full run ~10 s/mandi so it runs in a background worker and is stored in `forecast_cache`; plans use the fast ETS+ridge forecast until then. Tests: 94 pass (conftest disables threads/LLM/hybrid by default). Next: P2 smart agent.
- 2026-11-14: P2 smart agent done. `agents/brain.py` + `services/llm.py`: qwen3:4b plans up to 3 tools via /api/generate + JSON schema (chat+tools endpoint ignores think:false and is 7-20 s; generate+schema is 0.5-1.5 s). Python validates args (retail only with shop words, language switch only if a language is named, LLM crop/amount/place only if present in the text) and keeps yes/no gates. `grounded_answer` (JSON schema) answers "why" questions from plan facts; any number not in the facts -> rejected -> deterministic fallback. Rules extended: number words (do ton, दोन टन, पन्नास), taiyar/तैयार, "bech do" -> order, thanks, weather (not supported), schemes + retail tools (retail = DEMO band over nearby mandi median, city from the sentence via gazetteer), intake questions answered with "let's finish your details first". Known gap: Hindi/Marathi grounded answers often rejected -> falls back to the deterministic verdict. Next: P3 end-to-end operations (orders in Postgres, transporter/warehouse portals, notifications).
- 2026-11-14: P3 backend done. `models/ops.py` + migration 0005 (sale_orders, transport_jobs, warehouses, storage_bookings, notifications; users.token/state). `services/ops.py` runs both flows; `api/routes/ops.py`: POST /api/login (phone+role), /me, /farmer/{device}, /sale/{id}/confirm|cancel (X-Device), /transport/jobs (+/{id}/accept|pickup|deliver|release), /warehouses?lat&lon&crop, /storage/bookings (+/{id}/confirm|reject|release|cancel), /notifications(+/read), /fpo/summary, /admin/overview. Voice "sell it"+yes creates the order AND posts the TR- token; "book storage" books the nearest suitable warehouse. 1,192 warehouses seeded (cold/ventilated/godown per district, idempotent; also after each price import). E2E verified over HTTP + test. UI rule from user: never show the word DEMO in UI/agent text (truthful neutral wording only). Next: P3 frontend portals (/login, /transporter, /warehouse, /fpo, /admin), notification bell, journey timeline + done screen.
- 2026-11-14: P3 frontend + P4 done. Pages: /login (role cards, phone login), /transporter (open loads by token, accept/pickup/deliver/release, route link), /warehouse (requests confirm/reject, capacity), /fpo (members' produce by crop, full-truck pooling, orders), /admin (counts, price-job progress), /schemes (central + state schemes, en/hi/mr, official links). Farmer app: Journey timeline on the order card (live poll every 5 s), DoneCard ("Sale complete" + "Start a new task with the AI"), notification Bell, nav action -> /schemes, partner sign-in link. `next build` passes.

## HANDOFF — what is left (pick up here)
1. [done 2026-11-14: sell path verified in browser incl. backend-restart recovery; hold path verified via API] Browser QA of the whole demo flow (farmer EN/HI/MR -> sell it -> transporter portal -> deliver -> "I sold at 4100" -> done card; hold -> book storage -> warehouse portal confirm). Fix UI bugs found.
2. [done: core/present.py filter on plan JSON + agent replies; UI strings fixed] Remove remaining user-facing "DEMO"/"demo" words (user rule): grep `-i demo` in backend/app (agents.py labels/meta notes, demo_data names "Demo Fleet", costs PLACEHOLDER text, orchestrator "labels"), apps/web/lib/i18n.ts and components. Keep truthful wording (estimate / operator confirms). Internal field names may stay.
3. Portal i18n (portals are English only).
4. Hindi/Marathi grounded answers (llm.grounded_answer often rejected -> fallback); maybe ask the model for English facts then translate via templates.
5. README + PRD refresh; push.
How to run: `docker compose up -d --build` (db, backend :8000, web :3000); Ollama qwen3:4b on host (optional); gazetteer load: scripts/load_gazetteer.py (see PRD §6). Tests: `docker compose run --rm --no-deps backend python -m pytest tests -q` (100 pass).
- 2026-11-14: CORS now allows X-User-Token/X-Device; agent rebuilds a farmer session from the DB after a backend restart (crops + open order); presentation filter `core/present.py`. 101 tests pass. Remaining: handoff items 3-5 (portal i18n, hi/mr grounded answers, README polish), optional: hold-path browser run through /warehouse.
- 2026-11-14: smart-agent branch = Gemini/auto brain (other session) + voice yes/no overhaul + bug hunter + krishix model + listening-loop fixes + mandi map (other session). Next: run scripts/finetune_lora.py on a GPU with more hunter data (run the hunter 5-10x, export), then point Modelfile FROM at the GGUF and re-run the fixed-corpus A/B (`python -m app.qa.bughunt --corpus /app/qa_reports/corpus_fixed.json`). Test the mic loop on a real phone/Chrome.
