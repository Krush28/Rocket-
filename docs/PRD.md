# KRISHI-X — Product Requirements Document (living)

> **Hackathon end-to-end build in progress: see [BUILD-PLAN.md](BUILD-PLAN.md) (checklist, resume point).**
> **Living document.** Update this file (and [STRUCTURE.md](STRUCTURE.md)) in the same commit as every feature or fix.
> Last updated: 2026-11-13 · branch `phase1-foundation` · tests: 91 passing.

## 1. Problem and goal
Indian farmers sell where the *displayed* price is highest, not where they *keep* the most after transport, handling, commission, storage and spoilage. KRISHI-X is a **voice-first, multilingual (EN / हिं / मरा) assistant** that ranks every selling option by **expected net realization** and says honestly when it does not know. Scope: all of India.

**Primary user:** a farmer on a phone, speaking Hindi, Marathi or English, often with patchy network.
**Later users (Phase 8):** FPOs, buyers, transporters, warehouse operators, admin.

## 2. Non-negotiable rules (the code must keep these)
1. Never fabricate live prices, arrivals, buyer offers, phone numbers or warehouse capacity. Synthetic data is labelled **DEMO DATA**.
2. Transport costs are labelled **VERIFIED QUOTE** or **ESTIMATE**. Never present an estimate as a quote.
3. Retail prices are context only, never a farmer price.
4. No guaranteed forecasts. Return "insufficient data" when the backtest gate is not met.
5. All money maths is deterministic Python (`services/costs.py`, `agents/agents.py`). The LLM only picks a tool name or phrases text.
6. No Aadhaar collection. No crop-disease detection, loans or generic agri advisory.
7. No API keys in code; use env vars (`.env.example`).
8. Orders, bookings and any action with consequences ask **yes / no** first.
9. Place and mandi names in Hindi/Marathi come only from verified sources (GeoNames Devanagari, a state table). Unknown names keep the government spelling; machine transliteration is not shown (qwen3:4b was tested and spelled names wrong).

## 3. What exists today (Phase 1: done)

| Area | Status | Where |
|---|---|---|
| Real wholesale prices, all India (data.gov.in / Agmarknet) | ✅ one day (2026-11-13), 1,686 mandis | `services/adapters/agmarknet_datagov.py`, `data/raw/*.csv` |
| Mandi geocoding (Nominatim, cached) | ✅ 1,651 / 1,686 | `services/geocoding.py`, `scripts/geocode_mandis.py` |
| **Offline gazetteer** (GeoNames: 560k places + 155k pincodes) | ✅ about 1 ms per lookup; villages, "village, district", pincodes, Devanagari, Marathi oblique forms (पुण्याजवळ) | `services/gazetteer.py`, migration `0002`, `scripts/load_gazetteer.py` |
| 12-agent plan (discovery, prices, forecast gate, sell/hold, net realization, logistics, spoilage, confidence, recommendation) | ✅ | `agents/agents.py`, `agents/orchestrator.py` |
| Voice agent `/api/agent`: multi-crop intake, read-back, yes gate | ✅ | `conversation/intake.py`, `conversation/profile_agent.py` |
| Post-plan editing by voice: add a crop (named, with amount, or "add more crops"), remove a crop, change amount, change farm place | ✅ (QA 2026-11-13) | `agents/action_agent.py` (`add_crop`, `remove_lot`, `set_qty`, `set_location`) |
| **Reset / cancel:** "start over" button on both screens (confirm first) and by voice; "cancel / never mind / छोड़ो / राहू द्या" drops only a half-done step (pending yes/no, half-added crop, unfinished intake); reload drops pending questions; an intake untouched for 30 min starts fresh | ✅ | `action_agent._handle`, `intake.STALE_S`, `profile_agent.is_cancel`, `components/Voice.tsx` `ResetButton` |
| Price questions: named mandi or town, other crop, Devanagari names | ✅ | `action_agent._price_of` |
| Orders: create, transport, storage enquiry, track (yes/no gated) | ✅ demo state machine (SQLite) | `services/orders.py` |
| Hindi/Marathi: UI, agent replies, plan sentences, mandi / district / state names | ✅ (names partial; see rule 9) | `core/i18n.py`, `apps/web/lib/i18n.ts`, `plan.names` |
| Voice in/out: browser STT/TTS, offline Piper TTS, faster-whisper STT | ✅ | `services/tts.py`, `services/speech.py`, `api/routes/voice.py` |
| Local LLM fallback (Ollama qwen3:4b), used only when rules do not understand | ✅ optional | `services/llm.py` |
| Farmer memory (device id), "welcome back" | ✅ | `repositories/farmers.py` |
| Web: voice-first landing, results "settlement slip", command bar | ✅ | `apps/web` |

**Measured speed:** an agent turn takes 5–120 ms, a plan 14–93 ms, a gazetteer lookup about 1 ms, a warm LLM fallback 0.2–0.4 s, and Piper speech about 0.2–0.35 s.

## 4. Open issues / known gaps in Phase 1
- `action_agent.STATE` keeps plans and pending yes/no in memory per process. It is lost on restart and breaks with more than one worker. Move it to Postgres (M).
- Orders live in a separate SQLite file (`krishimitra.db`). Move them to Postgres (M).
- Only one day of prices, so forecasts always say "insufficient data". A history backfill (resource `35985678`) needs the user's data.gov.in key.
- Demo data is still used for buyers (hidden in LIVE), warehouses, transporter rate card, shared-load pool, arrivals and market schedule (`services/demo_data.py`).
- Distance ranking is a Python haversine scan; PostGIS `ST_DWithin` is available on `mandis.geog`.
- Rate limiting is in-process.
- Shelf life is only known for onion, tomato and potato (`services/spoilage.py`).
- Mandi-name Devanagari coverage is partial (for example "Chandwad" has no GeoNames Devanagari). Needs a curated, native-reviewed `name_translations` list (table exists, empty).
- A typo'd place ("Nashk") works only through online Nominatim. Offline fuzzy matching covers Devanagari input only.
- "transport cost 50 per quintal" is not an editable assumption yet (it shows the logistics estimate instead).
- The microphone has not been tested on real Android phones.

## 5. Roadmap (next phases, in suggested order)

| # | Work | Phase | Size |
|---|---|---|---|
| 1 | Persist agent state and orders in Postgres | 1-hardening | M |
| 2 | 3-year price-history backfill (35985678), daily scheduled import, validation rules, ingestion log | 3 | L |
| 3 | PostGIS radius queries for mandi discovery | 1-hardening | S |
| 4 | Forecast models (SARIMA, LightGBM/XGBoost) in the backtest gate + model registry + backtest report | 4 | M–L |
| 5 | Shelf-life table for more crops; hold logic on real history | 5 | M |
| 6 | LLM slot extraction and explanations in hi/mr behind the rules; an evaluation set of real farmer utterances | 2 | M |
| 7 | Auth (phone OTP), roles, registries for buyers / warehouses / transporters (replaces demo data) | 8 | L |
| 8 | Storage enquiries, transporter quotes (VERIFIED QUOTE), real shared-load matching | 6–7 | L |
| 9 | Background jobs, WhatsApp/SMS notifications, accounting | 9 | L |
| 10 | CI (GitHub Actions: pytest + `next build`), deployment, shared rate limit | 10 | M |
| 11 | Flutter app (`apps/mobile`) reusing `/api/agent` | — | L |

## 6. Working on this repo as an independent agent (lightweight)
You do **not** need the heavy assets to build most features:

| Heavy asset | Size | Needed for | Without it |
|---|---|---|---|
| GeoNames gazetteer (`data/raw/geonames/`, gitignored) | ~30 MB zip / ~1.2M rows | fast offline place lookup, Devanagari names | geocoding falls back to Nominatim online; names stay English |
| Piper voices (`models` volume) | ~200 MB | offline TTS | the browser voice is used; `/api/voice/speak` returns 503 |
| faster-whisper `small` | ~500 MB | offline STT | browser speech recognition is used |
| Ollama `qwen3:4b` | 2.5 GB | LLM fallback for odd phrasings | rules only (`KRISHIMITRA_LLM` unset) |

**Minimum loop:** `docker compose up -d db backend`, then `docker compose run --rm --no-deps backend python -m pytest tests -q`. Tests use a temp SQLite DB (DEMO mode) and never touch heavy assets or the network. To load the gazetteer, download from the links in `backend/scripts/load_gazetteer.py`.

**Definition of done for any feature:**
1. pytest is green.
2. `apps/web` builds (`docker compose up -d --build web` runs `next build` with type checking).
3. Every new farmer-facing sentence exists in en/hi/mr.
4. The rules in §2 still hold.
5. This PRD (§3/§4/§5/§7) and STRUCTURE.md are updated in the same commit.

## 7. Changelog
- **2026-11-14 (h)** — Pitch kit in `presentation/`: 5-minute script with sources (`PITCH-SCRIPT.md`), an offline slide deck in the pastel-dream theme with screenshots of the live app and credited farmer photos (`index.html`), and diagrams for the farmer journey (UML sequence), architecture, agent workflow and order lifecycle (`diagrams.html`). No app code changed.
- **2026-11-14 (g)** — Any crop by any name: local/Hinglish names (chawal, dhaan, kaju, akhrot, papita...), variety names (paddy basmati), typo tolerance (papya, tamatr), crop families ask which one (dry fruits, dal, millets), local-LLM mapping with a second verification call; unknown crops get an honest reply. Orders follow the crop the farmer names (switches, or asks the amount then the order yes/no). Forecast message fixed for long histories.
- **2026-11-14 (f)** — Voice: natural yes/no in full sentences (punctuation-proof, Hinglish/Marathi idioms, "yes but first..." answers then re-asks, LLM reads unclear replies with the question as context); read-back "yes, we are ready" confirms. Listening loop fixed (mic waits for real end of speech, ignores its own echo, answer buttons, rephrases after two misses). Voice bug-hunter agent `app/qa/bughunt.py` (LLM-generated farmer speech, judges outcomes, diagnoses, can learn yes/no phrases; fixed-corpus A/B). Specialised local model `krishix` (ollama/Modelfile.krishix): 92.6% vs 91.1% for base qwen3:4b on the same 203-line corpus; default OLLAMA_MODEL. Fine-tune pipeline ready: `app/qa/export_finetune.py` (171 verified examples) + `scripts/finetune_lora.py` (Colab/CUDA, not run yet).
- **2026-11-14 (f)** — Mandi map on the farmer results page (`components/MandiMap.tsx`): free OpenStreetMap tiles + Leaflet (CDN) + public OSRM road routes, no API keys. Farm pin, ranked mandi pins labelled with net in hand and distance, best mandi highlighted with its real road route, road km and drive time; tap a mandi to fly to its route; nearby storage pins; en/hi/mr. Web type-check target raised to ES2017.
- **2026-11-14 (e)** — Portals: login by role, transporter (booking tokens), warehouse operator, FPO head, admin; government schemes screen (central + state, en/hi/mr); farmer order journey, sale-complete screen, notification bell. Handoff list in BUILD-PLAN.md.
- **2026-11-14 (d)** — End-to-end operations backend: sale order + transport booking token to transporters, accept/pickup/deliver, sale confirmation; storage booking to warehouse operators; notifications for every side; FPO and admin dashboards API; storage network across 29 states. Tests: 100 pass.
- **2026-11-14 (c)** — Smart agent: local LLM plans multi-step tool calls from free speech (EN/HI/MR/Hinglish), extracts several intake facts from one sentence, answers "why" questions from plan facts with a number check; new tools: retail price context (DEMO), government schemes navigation, thanks, weather (declined). Tests: 99 pass.
- **2026-11-14 (b)** — Live prices from the keyless Mandi API (5 states, 25 crops, 6-hourly job); hybrid 3-year history labelled DEMO HISTORY so forecasts and hold/sell work; forecast v2 with SARIMA + gradient boosting computed in the background (`forecast_cache`). Migrations 0003 (state_price_history), 0004 (forecast_cache).
- **2026-11-14** — Any crop: `services/crops.py` (75 crops with hi/mr names and spoken aliases; category shelf life / hold limits for the rest); spoilage and hold now work for every crop.
- **2026-11-13 (c)** — Started the one-shot end-to-end build: plan in `docs/BUILD-PLAN.md`; Mandi API (keyless) probed.
- **2026-11-13 (b)** — Reset option: a visible "start over" button (en/hi/mr, with a confirm), voice "cancel" that drops unfinished steps without losing finished crops, unfinished intake expiring after 30 minutes, and reload clearing pending questions. 5 new tests.
- **2026-11-13**
  - Voice QA pass (13 scenario scripts) found about 15 bugs; all fixed with regression tests (`tests/test_voice_fixes.py`). Fixes:
    - adding a crop after confirmation
    - "I also have…", removing a crop, changing the amount or place
    - net / forecast / track routing in Hinglish and Hindi
    - Marathi yes/no words (ho, nako, na, y)
    - unit carry-over ("50 quintal onion and 20 potato")
    - a bare number now asks for its unit
    - Marathi stays Marathi for Devanagari input
    - transport booking without an order
    - Hindi plan restored on resume
  - Offline GeoNames gazetteer + pincodes.
  - Devanagari mandi, district and state names.
  - Living PRD + STRUCTURE added.
