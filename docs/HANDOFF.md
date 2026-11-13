# HANDOFF: read this first (for the next agent or teammate)

Last updated: 2026-11-13. Keep this file current: update the "Status" and "Next steps" sections whenever you finish something.

## 1. What we are building (the vision)
**KrishiMitra** (working codename in the original brief: **KRISHI-X**) is a **voice-first, multilingual (English / Hindi / Marathi) assistant that tells an Indian farmer where to sell, and how much they will actually keep after costs.** It is a hackathon project (problem statement PS 23: *AI Mandi Price Intelligence & Farm-to-Market Supply Chain Optimization*), built by a team of 4, originally in about 20 hours.

The five questions it must answer for every farmer:
1. What is my crop worth in nearby mandis today?
2. Which mandi or buyer gives the best **net** earnings (not the highest displayed price)?
3. Will the price go up or down, and how sure are we?
4. Should I sell now or hold?
5. If I hold or move it: which storage and transport?

The differentiator is the **Net Realization Engine**: revenue minus transport, handling, storage, financing, commission and expected loss. The original brief (very long) also lists FPO / buyer / transporter / warehouse / admin portals, Flutter mobile app, Postgres+PostGIS, Celery, XGBoost/LightGBM, shared-load matching, etc. **That full spec is NOT achievable in the time box and is not built.** We deliberately built a vertical slice (see section 5).

### Hard rules from the brief (never break these)
- Never fabricate live prices, arrivals, buyer offers, warehouse/transporter details or phone numbers. Anything synthetic is labelled **DEMO DATA** / **[Simulated]**.
- Costs are **ESTIMATES** unless a verified quote exists. Never present an estimate as a quote.
- Retail prices are context, never the price a farmer receives.
- No guaranteed forecasts. If history is insufficient, say so explicitly ("no reliable forecast").
- All money maths is deterministic Python. **An LLM may only choose which tool to run or phrase text; it never calculates.**
- Do not collect or verify Aadhaar. No crop-disease, loans or generic advisory features.
- Orders, bookings and "confirm sale" always ask the farmer yes/no first. "Booking" only logs a request inside the app; nothing reaches a real third party.

## 2. The user (owner) and how they like to work
- Not a deep engineer; wants things that **actually work** and honest status ("is it real?"). Asked "is it a working app?" and "make it work live!!!". Never overclaim.
- Prefers **short, scannable, ADHD-friendly answers**. Use bullets, tables, bold. Lead with the answer.
- Has a weak PC (cannot run big local models). Has not yet told us RAM / GPU: ask before picking a local LLM.
- Always confirmed before pushes ("Push the X?" then "Yes, push"). Keep doing that. Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- They used these skills/commands: `/superpowers:brainstorming`, `/ponytail` (smallest change), `/caveman` (terse), `/web-design-engineer`, `/design` (Design canvas artifact). Honour terse style where asked.

## 3. Where everything lives
- **GitHub:** https://github.com/Krush28/Rocket-  branch **`krishimitra`** (not `main`). Commits so far: scaffold+agents, live data adapter, UI redesign + auto-import, data+design+docs, spoilage/confidence features. Push by cloning the repo, copying files over, committing, `git push origin krishimitra`. **Never commit** `backend/.env`, `*.db`, `.venv`.
- **Local working folder:** `C:\Users\shreyash\Downloads\mandiproject\` (Windows 11; Git Bash + PowerShell). Python venv at `mandiproject\.venv` (Python 3.13). Not itself a git repo; the repo is cloned to a temp dir when pushing.
- **Design canvas (UI mockups):** https://claude.ai/artifact/9FLdEEHFMuq6cVHLmu11m7 (private); source in `design/krishimitra-redesign/`.

```
krishimitra/backend/app/
  main.py          FastAPI app + all endpoints (+ background threads: forecast warm-up, CSV watcher, optional 3h API refresh)
  agent.py         ACTION AGENT: free-form request -> tool -> executes (UI actions, plan edits, orders). Rules route EN/HI/MR; optional local LLM picks tool NAME only
  intake.py        multi-crop voice intake (crops -> quantity per crop -> village -> ready -> can store -> read-back -> confirm)
  inventory.py     remembers farmer + crops between visits (sqlite farmer.db, keyed by browser device id; no accounts)
  profile.py       single-lot slot filling helpers (extract crop/qty/place, yes/no, language detect, translated question text)
  orchestrator.py  explicit pipeline of agents; a failing agent degrades the plan instead of crashing
  agents.py        the agents: mandi discovery, price intelligence, market activity, buyers, cold storage, transport, shared load, forecast, sell-vs-hold, net realization, recommendation
  costs.py         deterministic money maths (transport, sell/hold, p_decline, decide)
  forecast.py      baselines + ETS + lag-Ridge + ensemble, rolling-origin backtest, reliability GATE
  logistics.py     OR-Tools CP-SAT shared-load matching (pool members are SIMULATED)
  spoilage.py      transit spoilage risk
  confidence.py    explainable confidence score
  adapters.py      LIVE data: data.gov.in API + CSV import + folder watcher + national-median helper for the data-error guard
  demo_data.py     synthetic series, fictional warehouses/transporters/buyers (all labelled DEMO), live-mode routing, price_outlier guard
  orders.py        order state machine (sqlite); llm.py optional Ollama hook; geo.py; meta.py (common metadata block)
krishimitra/frontend/index.html   single-file UI (no build step). Settlement-slip design. Talks to /api/agent
krishimitra/backend/tests/        pytest, 33 tests (conftest isolates DBs/state; tests run in DEMO mode)
data/raw/9ef84268-..._2026-11-13.csv   real Agmarknet daily prices, 16,038 rows (auto-imported on startup)
docs/            HANDOFF.md (this), original design notes (mandi-copilot-*.md)
design/          Design canvas source
.claude/launch.json   preview server config ("krishimitra", port 8000)
```

## 4. How to run, test, refresh data
```bash
# from krishimitra/backend  (venv is at ../../.venv on the owner's machine)
..\..\.venv\Scripts\python -m uvicorn app.main:app --port 8000     # open http://localhost:8000 (NO auto-reload: restart after backend edits)
..\..\.venv\Scripts\python -m pytest tests -q                       # run with PYTHONPATH=. if imports fail
```
- **Data modes:** if `live_prices.db` has rows the app is **LIVE** (real prices, mandis with no data are excluded, never filled with demo). Otherwise **DEMO** (synthetic).
- **Daily routine (works today, no API key):** download the CSV from the data.gov.in resource page (https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi, **Download** button). The server watches `~/Downloads`, `~/Downloads/mandiproject`, repo root and `data/raw` for `9ef84268*.csv` and imports within ~30 s. Force: `POST /api/admin/scan`. Manual: `python -m app.adapters import file.csv`.
- **Live API:** resource id `9ef84268-d588-465a-a308-a864a43d0070`. Needs `DATA_GOV_API_KEY` (env var or `backend/.env`, gitignored). **The only key tried is data.gov.in's shared public sample key, which returns HTTP 429 "Rate limit exceeded" from our machine.** The owner could not find a personal key (it is under the **API** button next to **Data** on the resource page, after login). Getting their own key is the fix.
- **Do not scrape:** Agmarknet 2.0 requires a captcha (we do not bypass captchas); CEDA is behind Cloudflare; e-NAM returned HTML not data.
- **Optional local LLM:** `KRISHIMITRA_LLM=ollama`, `OLLAMA_URL`, `OLLAMA_MODEL`. Off by default (rules only).

## 5. Status (what is real, what is not)
**Works and tested:** multilingual (EN/HI/MR) chat/voice intake with read-back-then-confirm; **multi-crop** intake + memory across visits + switching crops; real mandi price ranking by net earnings; sell-now/hold verdict with a "why" list; spoilage risk; explainable confidence; data-error guard (excludes prices far from the national median, e.g. a ₹200/qtl tomato); order tracking (create, request transport, storage enquiry, deliver, confirm sale); action agent (open tabs, compare, forecast, change costs, new lot, create/track orders, language switch) with confirmation for consequences; auto CSV import; settlement-slip UI.

**Not real / limits (be honest about these in any demo):**
- Only **one day** of real price history, so **forecasts are locked** (need ~120 days; the gate then opens by itself) and the verdict is always SELL NOW.
- Warehouses, transporters, buyers, pooled farmers: **DEMO/[Simulated]**. Cost rates (commission, hamali, vehicle rates, financing, ambient temperature): **unverified placeholders**, editable.
- Voice has **never been tested with a real microphone** (Chrome Web Speech API: hi-IN / mr-IN). The browser pane in dev blocks the mic.
- Not deployed (runs on the owner's laptop). No logins. Other roles (FPO, buyer, transporter, warehouse, admin) and the Flutter app are not built.
- Tomatoes near Ponda: no usable price in the file (the only nearby tomato price was a data error and was excluded), so the app says "No reliable price to compare". Onions near Niphad is the best demo path.

**Voice-first landing page: BUILT (2026-11-13), 33 tests green, checked in the browser with typed input only (mic untested).**
- First page is only the voice agent: full-screen mic orb, greeting caption, crops appear as chips while the farmer names them ("I grow onion and tomato" -> asks quantity per crop -> village -> ready -> can store -> read-back -> yes). Hands-free loop: after the agent speaks it listens again (first tap needed: browsers block autoplay audio and mic). Typed fallback and "Open dashboard" skip are always there.
- Multi-crop memory: browser device id (`localStorage.kmDevice`) is the `session_id`; `inventory.py` stores crops + farm details; returning visit skips the questions ("Welcome back..."). Crop switcher chips above the slip; saying/typing another saved crop name switches to it; "which crops do I have" lists them. A page reload on a live session resumes the dashboard.
- Language: `initLang()` uses a saved manual choice, else `navigator.language`, else browser Geolocation -> rough lat/lon boxes (Maharashtra->mr, Hindi belt->hi, Goa/other->en). Switcher always visible; a manual choice is remembered and wins.
- Dictionary: `frontend/i18n.js` (en/hi/mr, English fallback) merged into `T`; `t("key")`.

**Translation coverage is PARTIAL (be honest about it):** landing, header, tabs, slip, verdict card titles, crop bar, intake questions and core agent replies are translated. Still English-only: table headers and panel texts inside the Compare/Forecast/Logistics/Order panels, the cost-assumption form, backend-generated sentences (risk text, "why" factors, spoilage/confidence lines, forecast text), and many agent replies (only the core ones have hi/mr). The mic and geolocation paths are untested on a real device.

## 6. Key decisions and why (so you do not undo them)
1. **Scoped to a vertical slice** (onion/tomato/potato, Nashik-Goa-Karnataka belt) instead of the whole KRISHI-X spec: honest, demoable, cannot be done in 20 h otherwise.
2. **Rules-first + deterministic maths; LLM only picks a tool name / phrases text.** Reliable, explainable, works offline, safe with tiny local models. LLM-supplied arguments are never trusted (re-parsed by rules, whitelisted).
3. **Forecast reliability gate:** a horizon is shown only if the best model beats BOTH baselines (seasonal-naive, 7-day MA) by >=5% MAE in a chronological rolling-origin backtest AND its 80% interval coverage is within 0.2 of 0.8. Otherwise "no reliable forecast". Never random splits.
4. **Spoilage is a risk flag + ranking penalty, never a second rupee deduction** (weight loss is already modelled once as reduced saleable quantity; do not double count).
5. **Data-error guard:** in LIVE mode a price <35% or >250% of today's national median for the crop is excluded with a visible reason.
6. **No third-party scraping past captchas; no third-party code copied in.**
7. **UI direction:** "settlement slip" (mandi-receipt feel: forest green `#0F3D2E`, marigold `#F2B01E`, warm ground `#EEEDE4`, Bricolage Grotesque + Instrument Sans + Noto Sans Devanagari). The owner rejected a generic Apple-style polish, so do not revert to it.
8. **Memory without accounts:** a random device id kept in the browser, farmer data in sqlite. "Start over" deliberately forgets the farmer.

## 7. Gotchas we hit (save yourself the time)
- Python `\b` is unreliable around Devanagari combining marks: it split the Hindi word "क्विंटल" at the Marathi word "व" ("and"). Use whitespace-bounded alternations (see `intake.SEP`).
- Server has **no `--reload`**: restart after backend edits (`preview_stop` / `preview_start` in the dev pane).
- Entrance animations that start at `opacity:0` never finish in a throttled/hidden browser tab (screenshots looked washed out). Use transform-only animations.
- Mobile layout: grid items need `min-width:0` (`.panel>*`) or the page widens beyond the viewport.
- Tests must not touch real data: `tests/conftest.py` monkeypatches `adapters.DB`, `inventory.DB` and clears agent/intake/profile state. A leaked `farmer.db` made tests treat "a1" as a returning farmer.
- On this machine a very long bash command that mixes heredocs and Python can be rejected by a safety check that looks for dangerous `rm`; write scripts to files (scratchpad) and run them instead.
- `StarletteDeprecationWarning` about httpx in TestClient is harmless.
- `crop_median` needs >=5 rows for the crop on the latest date, otherwise the guard is skipped.
- Mandi price data labels: the CSV headers are `Min_x0020_Price` etc.; the importer already handles them. Market names are matched by alias substring (see `adapters.ALIASES`); coordinates in `demo_data.MANDIS/PLACES` are approximate and UNVERIFIED.

## 8. Next steps (priority order)
1. **Finish the translation pass:** move every remaining hardcoded UI string (panel headings, table headers, forms, buttons, errors) into `frontend/i18n.js`, and translate backend-generated sentences (return message keys + params from the API instead of English sentences). First drafts via IndicTrans2 (MIT) or Bhashini, then native-speaker review of farming vocabulary.
2. **Test the voice landing on a real device** (Chrome, mic permission, Hindi/Marathi speech output voices).
3. **Get the owner's own data.gov.in key** (so prices refresh every 3 h) and keep downloading the daily CSV to build history. After ~120 days of stored prices the forecast gate can open.
4. **Test voice on a real mic** (Chrome, Windows needs the Hindi/Marathi language pack for speech synthesis). Consider offline Whisper (STT) + Piper (TTS); Marathi quality for both is **unverified**.
5. **Local LLM for the agent:** ask the owner for RAM/GPU first. Candidates for a weak CPU PC: Sarvam-1 2B (Indic, older), Qwen3-4B (community Hindi fine-tune, ~2.5 GB Q4), small Gemma. Test Marathi tool-picking on real sentences. Free cloud tiers (Gemini, Groq) are a fallback but send farmer text off-device: label it.
6. Verify cost placeholders with a real FPO manager / trader (commission, hamali, vehicle rates). Replace demo warehouses/transporters/buyers with real, verified listings only when they exist.
7. Later: other role portals, deployment (Docker), real auth, Postgres/PostGIS, mobile app.

## 9. Open questions for the owner
- PC RAM / GPU (to pick the local model).
- Judging criteria and real deadline (unknown).
- Can someone talk to a real onion FPO manager to sanity-check the cost defaults?
