# Mandi Copilot Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Nashik-onion decision copilot for FPO managers (estimated net realization ranking, offer check, sell-or-hold, simulated pooling, voice chips) on real Agmarknet data within 23 hours.

**Architecture:** Deterministic Python rules engine behind FastAPI, reading a SQLite snapshot of Agmarknet prices. Forecasts are precomputed offline into cached JSON and shown only if they pass a baseline and calibration gate. A React/Vite PWA calls the API; an LLM, if used at all, only routes speech to four tool calls.

**Tech Stack:** Python 3.11, FastAPI, pandas, statsmodels, pytest, SQLite; React + Vite + TypeScript; optional Mandi-Chronos; Gemini free tier (stretch only).

**Spec:** `/home/claude/mandi-copilot-design.md` (approved 2026-11-13, including both revisions sections). Repo root below is `mandi-copilot/`.

## Global Constraints

- Python 3.11+, FastAPI, SQLite; React + Vite PWA; free-tier services only.
- Forecast evaluation uses only dates on or after 2025-06-01, because Mandi-Chronos was fine-tuned on series dated before that (model card). Weekly rolling origins.
- A forecast is shown only if the model's MAE beats both baselines (seasonal naive, 7-day moving average) by at least 5% at that horizon AND the q0.3 empirical coverage is within 0.1 of 0.3; otherwise show "no reliable forecast" and trend facts only.
- The classical pipeline must work before any Chronos work. Mandi-Chronos is optional: CC BY-NC-SA 4.0 (non-commercial) and a gated download.
- All arithmetic is deterministic Python. An LLM may only map speech to one of four tool calls: `create_lot`, `rank_mandis`, `hold_or_sell`, `check_offer`.
- Every cost assumption carries a source tag `verified | user | unverified`; unverified ones show `[Unverified placeholder - edit me]`. The UI says "estimated net realization", never "profit", and warns that the modal price is not a guaranteed price for a lot.
- Simulated rows carry the label `[Simulated]`. No hardcoded savings percentage anywhere.
- Mandi coordinates come only from the geocoding script's output after hand-checking.
- Demo runs on standard Chrome. Voice chips work offline through the deterministic parser.
- Hour-1 data probe covers three sources: data.gov.in `35985678-0d79-46b4-9ed6-6f13308a1d24`, data.gov.in `9ef84268-d588-465a-a308-a864a43d0070` (unverified), and CEDA. Use the daily-fresh source for live prices and the deepest history for the backtest; manual Agmarknet CSV is the last fallback.

## Review Focus

1. A mandi with no recent price for the chosen commodity, variety and grade, or a price older than 7 days: excluded with a reason and a visible age, never a crash or a silent stale rank (Task 5).
2. Non-positive lot quantity, a lot larger than one vehicle, or pooled quantity exceeding capacity: validation error, extra trips, or a capped explained result (Tasks 1, 4, 9).
3. Voice input with Devanagari numerals ("२००"), an unknown intent, or garbage text: "could not understand", chips stay visible, no unvalidated call runs (Task 10).
4. An offer of zero, negative, or absurdly high (10x the reference): reject non-positive values; verdict "high" for the rest (Task 6).
5. A series with too little history, long gaps, or a stale last observation, or a forecast that fails calibration: forecast disabled, not computed from sparse data (Tasks 7, 8).

## Schedule (hours from kickoff; roles are placeholders until you tell me the team's skills)

| Hours | Work | Role |
|---|---|---|
| H0-2 | Task 1; Task 2 data probe; ask a real FPO manager or trader two questions | all |
| H2-6 | Tasks 3, 4, 5, 6 | backend |
| H2-10 | Tasks 7, 8 (forecast pipeline, highest risk; classical first) | ML/data |
| H5-12 | Task 12 against the Task 11 contract (mock until live) | frontend |
| H6-11 | Tasks 9, 10, 11 | backend |
| H11-16 | Task 13; then stretch tasks only if the core works | all |
| H17-18 | End-to-end tests; **feature freeze at H18** | all |
| H18-21 | Task 14 (deploy, hardening, bug fixes) | all |
| H21-23 | Rehearsal, 3-minute script, judge Q&A | all |

If the data probe fails, spend no time on Chronos: get the core on a verified snapshot first.

---

### Task 1: Scaffold, models, config, database

**Files:**
- Create: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/models.py`, `backend/app/config.py`, `backend/app/db.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces:
  - `models.Lot(qty_qtl: float, commodity: str, variety: str, grade: str, origin: str, storage_available: bool, holding_cost_per_qtl_week: float)`; `qty_qtl` must be > 0.
  - `models.Vehicle(name: str, capacity_qtl: float, base_cost: float, per_km_cost: float)`.
  - `models.CostAssumptions(vehicles: list[Vehicle], commission_pct: float, commission_payer: Literal["seller","buyer"], hamali_per_qtl: float, shrinkage_pct_per_week: float, risk_allowance_pct: float, road_factor: float, sources: dict[str, Literal["verified","user","unverified"]])`.
  - `config.DEFAULT_ASSUMPTIONS: CostAssumptions`: vehicles `tempo` (capacity 40, base 400, per-km 14) and `truck` (capacity 100, base 500, per-km 25); commission 4.0 with payer "buyer"; hamali 15.0; shrinkage 2.0; risk allowance 0.0; road factor 1.3; every source tag "unverified". `config.PLACEHOLDER_NOTE = "[Unverified placeholder - edit me]"`.
  - `db.init_db(path: str) -> sqlite3.Connection`, creating `prices(market, district, commodity, variety, grade, date, min_price, max_price, modal_price, arrivals_t NULL, PRIMARY KEY(market, commodity, variety, grade, date))`.

- [ ] **Step 1: Write failing tests:** `test_lot_rejects_non_positive_qty` (`pytest.raises(ValidationError)` for 0 and -5); `test_default_assumptions_flagged` (note string equals the spec value, every source tag is "unverified", the two vehicles exist with the values above); `test_init_db_creates_prices_table`.
- [ ] **Step 2: Run** `pytest backend/tests/test_models.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** with pydantic v2 and stdlib `sqlite3`. Run `git init`; `.gitignore` for `.venv`, `*.db`, `node_modules`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: scaffold models, config, db`.

---

### Task 2: Data-source probe and price loaders

**Files:**
- Create: `scripts/probe_sources.py`, `backend/app/ingest/__init__.py`, `backend/app/ingest/csv_loader.py`, `backend/app/ingest/datagov.py`
- Test: `backend/tests/test_ingest.py`, `backend/tests/fixtures/prices_sample.csv`

**Interfaces:**
- Consumes: `db.init_db`.
- Produces:
  - `csv_loader.COLUMN_MAP: dict[str, str]` mapping source headers to `prices` columns (fixture headers are placeholders until the probe shows the real ones).
  - `csv_loader.load_prices_csv(path: Path, conn: sqlite3.Connection) -> int` returning rows upserted.
  - `datagov.fetch_datagov(api_key: str, resource_id: str, state: str, since: date, page_size: int = 500) -> list[dict]`, paginating by offset until exhausted.

- [ ] **Step 1: Write failing tests.** Fixture CSV has an "Other" variety, a row with empty arrivals, and one duplicate row. `test_load_is_idempotent` loads twice and asserts an unchanged row count; `test_missing_arrivals_stored_as_null`.
- [ ] **Step 2: Run** `pytest backend/tests/test_ingest.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the probe first. For each of the three sources it prints row count, earliest and latest date, the latest date for Maharashtra onion, and whether an arrivals column exists. Run it with network access and a data.gov.in key; **record the results, they decide the sources** (Global Constraints). Then implement the loader (upsert on the primary key) and the paginated fetch.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: price ingest and source probe`.

---

### Task 3: Mandi geography

**Files:**
- Create: `scripts/geocode_mandis.py`, `backend/data/mandis.json`, `backend/app/geo.py`
- Test: `backend/tests/test_geo.py`

**Interfaces:**
- Produces:
  - `geo.haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float`
  - `geo.road_km(a, b, road_factor: float) -> float` (haversine times factor; an estimate, labelled as such in the UI)
  - `geo.load_mandis(path: str, require_verified: bool = True) -> dict[str, Mandi]` with `Mandi(name, lat, lon, verified: bool)`.

- [ ] **Step 1: Write failing tests:** `test_haversine_one_degree_equator` ((0,0) to (0,1) ≈ 111.19 km within 0.2); `test_road_km_applies_factor`; `test_unverified_mandi_rejected`.
- [ ] **Step 2: Run** `pytest backend/tests/test_geo.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `geo.py`. The geocoding script uses Nominatim at one request per second and writes `verified: false`. Run it for the Nashik-belt places that appear in the loaded data (mandis and the origin list), hand-check each on a map, then set `verified` to true.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: geo helpers and geocoded places`.

---

### Task 4: Transport and net realization

**Files:**
- Create: `backend/app/costs.py`
- Test: `backend/tests/test_costs.py`

**Interfaces:**
- Consumes: `CostAssumptions`, `Vehicle`.
- Produces:
  - `costs.choose_vehicle(lot_qtl: float, vehicles: list[Vehicle]) -> Vehicle`: the smallest vehicle that fits the lot in one trip, otherwise the largest.
  - `costs.trips_needed(lot_qtl: float, v: Vehicle) -> int` (ceiling of lot over capacity).
  - `costs.net_in_hand(price_per_qtl: float, road_km: float, lot_qtl: float, a: CostAssumptions, transport_quote: float | None = None) -> NetBreakdown` with per-quintal fields `gross, transport, commission, hamali, risk, net`. Transport per quintal = `trips × (base_cost + per_km_cost × km) / lot_qtl`, or `transport_quote / lot_qtl` when a quote is given. Commission = pct% of gross only when payer is "seller". Risk = `risk_allowance_pct`% of gross. Net = gross minus the four deductions.

- [ ] **Step 1: Write failing tests** (defaults, price 1500, 100 km, payer "seller"): lot 100 on a truck gives transport 30.0, commission 60.0, hamali 15.0, risk 0.0, net 1395.0; payer "buyer" gives net 1455.0; lot 40 chooses the tempo and gives transport 45.0, net 1380.0; `choose_vehicle(30, ...)` is the tempo, `choose_vehicle(80, ...)` the truck; `trips_needed(250, truck) == 3`; a quote of 5000 for 100 quintals gives transport 50.0; risk allowance 2% gives risk 30.0.
- [ ] **Step 2: Run** `pytest backend/tests/test_costs.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** as pure functions.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: per-trip transport and net realization`.

---

### Task 5: Mandi ranking

**Files:**
- Create: `backend/app/rank.py`
- Test: `backend/tests/test_rank.py`

**Interfaces:**
- Consumes: `net_in_hand`, `geo.road_km`, `Lot`, prices.
- Produces: `rank.rank_mandis(lot: Lot, conn, mandis: dict[str, Mandi], a: CostAssumptions, as_of: date, max_age_days: int = 7) -> RankResult` with `RankResult(ranked: list[RankedMandi], excluded: list[Excluded])`. `RankedMandi(mandi, price_date, age_days, gross, road_km, net_per_qtl, net_total)` sorted by `net_total` descending. `Excluded(mandi, reason)`.

- [ ] **Step 1: Write failing tests** on a seeded in-memory DB: `test_ranks_by_net_not_gross` (a farther mandi with a higher gross ranks below a nearer one once costs apply); `test_stale_mandi_excluded_with_reason` (`"stale: 9 days"`); `test_mandi_without_match_excluded` (`"no price for commodity/variety/grade"`); `test_total_equals_per_qtl_times_qty`.
- [ ] **Step 2: Run** `pytest backend/tests/test_rank.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** using each mandi's latest modal price matching the lot's commodity, variety and grade on or before `as_of`.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: mandi ranking with exclusions`.

---

### Task 6: Offer check

**Files:**
- Create: `backend/app/offer.py`
- Test: `backend/tests/test_offer.py`

**Interfaces:**
- Consumes: `net_in_hand`, prices.
- Produces: `offer.check_offer(offer_per_qtl: float, basis: Literal["farm_gate","delivered"], lot: Lot, mandi: str, as_of: date, conn, mandis, a: CostAssumptions) -> OfferVerdict` with `verdict: Literal["low","fair","high"]`, `offer_net`, `reference_net`, `band_low_net`, `band_high_net`. Reference gross = median modal of the last 3 days at the mandi for the lot's commodity, variety and grade; band = 25th to 75th percentile of the last 30 days of modal prices, each through `net_in_hand`. A farm-gate offer counts as already net; a delivered offer goes through `net_in_hand`.

- [ ] **Step 1: Write failing tests:** below the band's net gives "low", inside "fair", above "high"; `offer_per_qtl` of 0 or negative raises `ValueError`; 10 times the reference gives "high"; the module imports nothing from `forecast`.
- [ ] **Step 2: Run** `pytest backend/tests/test_offer.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** with pandas quantiles.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: offer check`.

---

### Task 7: Baselines, backtest, gate and calibration

**Files:**
- Create: `backend/app/forecast/__init__.py`, `backend/app/forecast/baselines.py`, `backend/app/forecast/backtest.py`
- Test: `backend/tests/test_backtest.py`

**Interfaces:**
- Produces:
  - `baselines.seasonal_naive(history: pd.Series, horizon: int, season: int = 7) -> float`
  - `baselines.moving_average(history: pd.Series, horizon: int, window: int = 7) -> float`
  - `backtest.series_supported(history: pd.Series, origin: pd.Timestamp) -> bool`: at least 120 observations in the prior 365 days and a last observation at most 7 days before `origin`. Thresholds are tunable after the probe shows real data.
  - `backtest.rolling_origin_mae(series, predict: Callable[[pd.Series, int], float], horizon: int, eval_start: str = "2025-06-01", step_days: int = 7) -> float`; history is strictly before each origin; unsupported origins are skipped.
  - `backtest.coverage(observed: list[float], predicted_q: list[float]) -> float`: the fraction of observations at or below the predicted quantile.
  - `backtest.calibration_ok(cov: float, q: float, tol: float = 0.1) -> bool`.
  - `backtest.gate_passes(model_mae: float, baseline_maes: list[float], margin: float = 0.05) -> bool`.

- [ ] **Step 1: Write failing tests:** `test_no_leakage` (a `predict` stub raises if given any value dated on or after the origin); `gate_passes(10, [10, 12])` is false and `gate_passes(8, [10, 12])` is true; `test_sparse_series_unsupported`; `calibration_ok(0.3, 0.3)` true and `calibration_ok(0.6, 0.3)` false; `coverage([1,2,3,4], [2,2,2,2]) == 0.5`.
- [ ] **Step 2: Run** `pytest backend/tests/test_backtest.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the functions.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: baselines, backtest, gate, calibration`.

---

### Task 8: Forecast precompute and hold-or-sell

**Files:**
- Create: `scripts/precompute_forecasts.py`, `backend/app/forecast/store.py`, `backend/app/hold.py`, `backend/data/forecasts.json` (generated)
- Test: `backend/tests/test_hold.py`

**Interfaces:**
- Consumes: Task 7, `net_in_hand`.
- Produces:
  - `store.load_forecasts(path: str) -> dict[str, SeriesForecast]`; `SeriesForecast(gate_ok: dict[int, bool], calibration_ok: dict[int, bool], quantiles: dict[int, dict[str, float]], backtest: dict)`; horizons 7 and 14; quantile keys "q0.1" to "q0.9".
  - `hold.hold_or_sell(lot: Lot, price_now: float, forecast: SeriesForecast | None, road_km: float, a: CostAssumptions) -> HoldDecision` with `action: Literal["SELL_NOW","HOLD","NO_RELIABLE_FORECAST"]`, `horizon_days: int | None`, `net_by_horizon: dict[int, float]`, `reason: str`. Net per quintal at horizon h days = `net_in_hand(price_h, road_km, lot.qty_qtl, a).net × (1 − shrinkage_pct_per_week × h/7 / 100) − holding_cost_per_qtl_week × h/7`. HOLD only if both `gate_ok[h]` and `calibration_ok[h]` hold and the net from quantile q0.3 exceeds net now (about a 70% chance of gain; my threshold).

- [ ] **Step 1: Write failing tests:** no forecast, a failed gate, or a failed calibration gives `NO_RELIABLE_FORECAST`; a rising synthetic forecast with a cheap holding cost gives HOLD at 14; the same forecast with a very high holding cost gives SELL_NOW; shrinkage is applied (with flat quantile prices, net at 14 is below net now); `storage_available False` gives SELL_NOW with that reason.
- [ ] **Step 2: Run** `pytest backend/tests/test_hold.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `store` and `hold`. Then `precompute_forecasts.py`, classical first: damped-trend ETS (statsmodels) with empirical residual quantiles from earlier origins, for the demo mandis only, weekly origins from 2025-06-01. Compute MAE against both baselines, q0.3 coverage, `gate_ok` and `calibration_ok`, and write `forecasts.json`. A `--model chronos` flag swaps in Mandi-Chronos only if the licence, access and install all work; do not spend time on it before the core is demo-ready. Commit the generated JSON so the demo never runs inference.
- [ ] **Step 4: Run** the unit tests. Expected: PASS. Open `forecasts.json` and note honestly which series pass; if none do, say so on the backtest page.
- [ ] **Step 5: Commit** `feat: forecast precompute and hold-or-sell`.

---

### Task 9: Simulated pooling (time-boxed to 1-2 hours)

**Files:**
- Create: `backend/app/pool.py`, `backend/data/pool_seed.json`
- Test: `backend/tests/test_pool.py`

**Interfaces:**
- Produces:
  - `pool.pool_cost_per_qtl(truck_total_cost: float, truck_capacity_qtl: float, lot_qtl: float, pooled_qtl: float) -> float` = `truck_total_cost / min(truck_capacity_qtl, lot_qtl + pooled_qtl)`.
  - `pool.solo_cost_per_qtl(tempo_total_cost: float, lot_qtl: float) -> float` = `tempo_total_cost / lot_qtl`.
  - `pool.load_seed_pool(path: str) -> list[SimulatedLoad]`; every item has `label == "[Simulated]"`.

- [ ] **Step 1: Write failing tests:** `pool_cost_per_qtl(12000, 100, 40, 60) == 120.0`; `solo_cost_per_qtl(6000, 40) == 150.0`; `pool_cost_per_qtl(12000, 100, 80, 60) == 120.0` (capped at capacity); non-positive `lot_qtl` raises `ValueError`; every seed load is labelled `[Simulated]`.
- [ ] **Step 2: Run** `pytest backend/tests/test_pool.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Seed file holds a few synthetic loads; all truck figures are placeholders.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: simulated pooling calculator`.

---

### Task 10: Voice chips (deterministic router)

**Files:**
- Create: `backend/app/voice.py`, `backend/data/chips.json`
- Test: `backend/tests/test_voice.py`

**Interfaces:**
- Produces:
  - `voice.ToolCall(name: Literal["create_lot","rank_mandis","hold_or_sell","check_offer"], args: dict)`
  - `voice.parse_quantity(text: str) -> float | None`, accepting Latin and Devanagari digits.
  - `voice.parse_chip(text: str) -> ToolCall | None`, built from `chips.json` (at least one chip each for Marathi, Hindi, English).
  - `voice.dispatch(call: ToolCall, deps) -> dict`, running the matching rules function.

- [ ] **Step 1: Write failing tests:** `parse_quantity("२००") == 200.0`; each chip parses to its expected `ToolCall`; `parse_chip("blah blah")` is `None`; `dispatch` of `rank_mandis` returns a ranked result on the seeded DB.
- [ ] **Step 2: Run** `pytest backend/tests/test_voice.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** with pydantic validation.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: voice chips router`.

---

### Task 11: API wiring

**Files:**
- Create: `backend/app/main.py`, `scripts/seed_demo_db.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 4-10.
- Produces (the frontend contract):
  - `POST /api/rank` {lot, assumptions?} -> {ranked, excluded, data_as_of}
  - `POST /api/hold` {lot, mandi, assumptions?} -> HoldDecision
  - `POST /api/offer` {lot, mandi, offer_per_qtl, basis, assumptions?} -> OfferVerdict
  - `POST /api/pool` {lot_qtl, truck_total_cost, truck_capacity_qtl, tempo_total_cost} -> {solo, pooled, loads}
  - `POST /api/voice` {text, lang, chip_id?} -> {call, result} or `{error: "could_not_understand"}`
  - `GET /api/backtest`, `GET /api/freshness`

- [ ] **Step 1: Write failing tests** with `TestClient` on a seeded DB: rank returns ranked and excluded lists; `qty_qtl = 0` returns 422; an English chip via `/api/voice` returns a ranked result; garbage returns `could_not_understand`; `/api/freshness` returns an age per mandi.
- [ ] **Step 2: Run** `pytest backend/tests/test_api.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the endpoints and `seed_demo_db.py` (builds the fixture DB for tests and offline demos).
- [ ] **Step 4: Run** `pytest backend -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: API wiring`.

---

### Task 12: Frontend core

**Files:**
- Create: `frontend/` (Vite React TS), `src/api.ts`, `src/components/LotForm.tsx`, `RankingList.tsx`, `HoldCard.tsx`, `OfferCheck.tsx`, `AssumptionsPanel.tsx`, `FreshnessBadge.tsx`
- Test: `frontend/src/format.test.ts`

**Interfaces:**
- Consumes: the Task 11 contract (mock with static JSON until live).
- Produces: `format.rupees(n: number): string` (Indian digit grouping); typed `api.ts` functions named after the endpoints.

- [ ] **Step 1: Write failing test:** `rupees(1395)` returns `"₹1,395.00"`, `rupees(123456)` returns `"₹1,23,456.00"`.
- [ ] **Step 2: Run** `npm --prefix frontend test`. Expected: FAIL.
- [ ] **Step 3: Implement** the formatter and components. Mobile-first with large touch targets. Every price shows its age. AssumptionsPanel shows each value with a verified / user / unverified badge and is editable. A failed gate renders "No reliable forecast" with trend facts only. Copy says "estimated net realization" and warns that modal price is not a guarantee for the lot.
- [ ] **Step 4: Run** the test and `npm --prefix frontend run build`. Expected: PASS and a clean build.
- [ ] **Step 5: Commit** `feat: frontend core`.

---

### Task 13: Frontend voice chips, pooling, backtest page

**Files:**
- Create: `src/components/VoiceButton.tsx`, `ChipRow.tsx`, `PoolToggle.tsx`, `BacktestPage.tsx`
- Test: `frontend/src/voice.test.ts`

**Interfaces:**
- Consumes: Task 11 endpoints; Task 10 chip ids.
- Produces: `voice.isSpeechSupported(win: Window): boolean`.

- [ ] **Step 1: Write failing tests:** `isSpeechSupported` is false without `webkitSpeechRecognition` and true with it; the chip row renders at least three chips (Marathi, Hindi, English).
- [ ] **Step 2: Run** `npm --prefix frontend test`. Expected: FAIL.
- [ ] **Step 3: Implement.** VoiceButton uses `webkitSpeechRecognition` and shows "use Chrome" if unsupported. Chips post `chip_id` to `/api/voice` and work offline. PoolToggle shows solo against pooled cost per quintal, every pooled row labelled `[Simulated]`. BacktestPage shows model against both baselines per series, the evaluation window dates, MAE, q0.3 coverage and the gate result.
- [ ] **Step 4: Run** tests and build. Expected: PASS.
- [ ] **Step 5: Commit** `feat: voice chips, pooling, backtest UI`.

---

### Task 14: Deployment and demo hardening

**Files:**
- Create: `render.yaml` (or the host's equivalent), `docs/demo-script.md`, `docs/judge-qa.md`
- Test: `backend/tests/test_smoke.py`

- [ ] **Step 1: Write a failing smoke test** running the demo scenario against the seeded DB: a 200-quintal onion lot near Niphad, rank, hold-or-sell, offer check, pooling; assert each returns 200 with a non-empty result.
- [ ] **Step 2: Run** `pytest backend/tests/test_smoke.py -v`. Expected: FAIL until the seed holds the scenario.
- [ ] **Step 3: Complete the seed and deploy.** Free-tier backend plus a static frontend. Free backends sleep, so hit it before judging and keep a local run on the demo laptop as the fallback. The 3-minute script follows an FPO manager's decision, labels every simulated item aloud, shows the latest real observation date (a Nov 13 reopening does not guarantee new data is published), and answers the judge questions honestly (data trust, lot quality, real versus estimated transport, why not call a trader, where the AI adds value, revenue, first ten FPOs).
- [ ] **Step 4: Run** the full suite and a manual run-through in standard Chrome, including a chips-only pass with the network off.
- [ ] **Step 5: Commit** `chore: deployment and demo materials`.

---

## Stretch tasks (only after Task 13 works end to end; cut in this order if behind)

- **S1 Alerts:** `alerts.evaluate_alerts(rules: list[AlertRule], latest: dict[tuple[str, str], float]) -> list[Triggered]`, an `alert_rules` table, `/api/alerts*` endpoints, a banner with a "simulate refresh" button. Tests: above and below trigger, equal does not, missing price is skipped.
- **S2 Gemini routing:** `voice.route_with_gemini(text: str, call_model: Callable[[str], str]) -> ToolCall | None`, injected model call, validated JSON against the four tools. Tests: invalid JSON, unknown tool name, and a negative quantity all return `None`.
- **S3 Mandi map:** Leaflet map coloured by net realization.
- **S4 Member lots:** a LotForm table whose quantities sum into the lot total.

## Self-review notes

- **Spec coverage:** all core items and both revisions sections map to tasks; stretch items match the spec's priority tiers.
- **Decisions of mine, flagged:** HOLD uses q0.3; support thresholds (120 observations, 7 days); calibration tolerance 0.1; vehicle presets and cost defaults; ETS as the classical model.
- **Risks:** Task 2's probe may show daily-fresh data without deep history, or the reverse; Task 8 may find that no series pass the gate, in which case the app shows trend facts and the backtest page becomes the honest story.
