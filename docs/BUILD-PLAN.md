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
- [ ] `services/adapters/mandi_api.py`: client (throttled), import latest prices per state×crop into `mandi_prices` (source "mandi-api"), state-average history into `state_price_history`; geocode new mandis with the offline gazetteer.
- [ ] `repositories/market_data.series`: hybrid series (real + synthetic backfill to 3 years, flagged); `history_source` in meta.
- [ ] `ml/forecast.py`: add SARIMA (statsmodels SARIMAX) + LightGBM (fallback sklearn HistGradientBoosting) to the backtest gate.
- [ ] Any crop: Hindi/Marathi names + shelf-life/perishability table for ~60 common crops (category defaults for the rest).
### P2 Smart agent (local LLM, Ollama qwen3:4b)
- [ ] Agentic loop `agents/brain.py`: Ollama `/api/chat` with tools (JSON schemas) → execute deterministic tools → feed results back → final answer in farmer's language. Rules stay as instant fast path for exact commands; LLM handles everything else (free speech intake, multi-step questions, explanations).
- [ ] LLM slot extraction for intake (crop/qty/unit/place/ready/storage from any sentence).
### P3 End-to-end operations
- [ ] Postgres tables: `orders` (move from SQLite), `transport_jobs` (token), `warehouses`, `storage_bookings`, `notifications`, `users` (role, phone, name, state).
- [ ] Demo login (phone + role, no password; labelled demo) and portals: `/transporter`, `/warehouse`, `/fpo`, `/admin`; farmer app stays `/`.
- [ ] Flow: order → transport job → accept/pickup/deliver → sale confirmed → done screen; hold → storage booking → confirm → sell from storage.
- [ ] Notifications bell (poll) for every actor.
### P4 Farmer extras
- [ ] Schemes DB (central + 5 states, official links, "verify on official site", last reviewed) + `/schemes` screen + agent tool `show_schemes`.
- [ ] Retail price tool (labelled retail context; demo markup over mandi modal unless a live source is added).
- [ ] FPO head: member lots aggregate + pooled order.
### P5 Background + polish
- [ ] Daily import job (in-process scheduler), README/PRD, push.

## Status log
- 2026-11-13: plan written; Mandi API probed (works, short history).
