# Mandi Copilot (working name): design

Date: 2026-11-13. Hackathon PS 23, 23-hour build. Status: approved by the team on 2026-11-13, including the changes below.

## Intent and why
An onion FPO manager (or progressive farmer) in the Nashik belt has a lot of onions and must decide where to sell, whether to hold, and whether a buyer's offer is fair. Today they rely on word of mouth, a phone call to the arhtiya, or raw mandi price lists. The product answers three questions for one lot:
1. Where do I net the most after transport, commission and shrinkage?
2. Should I sell now or hold for N days, given carrying costs and a forecast?
3. Is this offer fair?

A voice front end (Marathi, Hindi, English) lets the user ask in their own language. Simple threshold alerts tell them when a price crosses a level.

Why it should exist: displayed mandi prices are not the price a farmer realises, and cross-mandi arbitrage often fails on quality risk and distance (IMPRI on eNAM, hypothesis-grade). FPOs struggle with price information and storage economics (MicroSave). Existing players mostly buy and resell (DeHaat, Ninjacart) or crowd load matching (TrucksUp).

## Goals
- One working end-to-end flow on real Agmarknet data for onion in the Nashik belt.
- Honest uncertainty. Forecasts are shown only when they beat a naive baseline in time-based backtests.
- Every assumption (transport rate, commission, shrinkage, holding cost) is visible and editable, and labelled as an assumption.
- Voice works for at least Hindi and Marathi input, with typed fallback.

## Non-goals
- No real marketplace or real load matching, no payments, no WhatsApp sending. A clearly labelled simulated pooling view is in scope (see "Changes approved after external review").
- No multi-crop support beyond onion for the demo (the data layer stays crop-agnostic).
- No user accounts beyond a simple session or device id.

## Anti-goals (a failure even if it technically works)
- A pretty dashboard with fake numbers.
- Presenting forecasts as guaranteed prices, or claiming real adoption, savings or accuracy we haven't measured.
- Forcing an LLM into calculations that rules do better.

## Approaches considered
- **A. Rules-first calculator, forecaster behind a baseline gate, LLM only for language and voice (chosen).** Reliable, explainable, and degrades gracefully when data is thin.
- B. Forecast-led product. Rejected: Agmarknet series have gaps and delays, so the core value would depend on the weakest part.
- C. Marketplace or load-matching led. Rejected: cold start, crowded space, can't be honestly demonstrated in 23 hours.

## Calls I made (change any of them)
- **Stack:** React/Vite PWA frontend, Python FastAPI backend, SQLite locally (Postgres on Supabase free tier only if needed), Leaflet with OpenStreetMap tiles. Next.js adds nothing here.
- **Forecasting:** Precompute forecasts offline into cached JSON, so the demo never depends on live inference. The classical pipeline comes first (damped-trend ETS with empirical residual quantiles); Mandi-Chronos is an optional upgrade only (see the revisions section). Baselines are seasonal naive and a 7-day moving average. The gate requires beating both baselines on MAE and passing a quantile calibration check; the margin (5%) is my guess to be tuned on real data.
- **Validation:** Rolling-origin, time-ordered backtest at 7 and 14 day horizons. Report MAE and quantile coverage.
- **Voice:** Browser Web Speech API for input and output, with Gemini free tier mapping the utterance to one of four tool calls (create_lot, rank_mandis, hold_or_sell, check_offer). Marathi and Hindi voices vary by device, so typed input is always available.
- **Data:** Snapshot the data.gov.in Agmarknet resource (35985678-0d79-46b4-9ed6-6f13308a1d24) into the database with an ingest script. The demo reads the snapshot, and the UI shows data freshness and missing days. Whether the API includes arrival quantities is unverified.
- **Distances:** Haversine distance times a road factor, using mandi coordinates geocoded once and hand-checked. Public OSRM routing is optional.
- **Cost defaults:** Transport rate per quintal-km, commission, hamali and shrinkage are placeholders labelled "assumption (edit me)".

## MUST build
1. **Lot entry:** crop, quantity, variety/grade, location, storage availability and holding cost per quintal per week. Form or voice.
2. **Net-in-hand ranking** across 4 to 8 mandis: price, minus transport (per-trip vehicle cost), commission and hamali, plus any optional risk allowance. Shows data age per mandi. Wording is always "estimated net realization".
3. **Sell-or-hold:** expected net at 0, 7 and 14 days from forecast quantiles minus carrying cost and shrinkage. Outputs a recommendation with a range. If the gate fails, it says "no reliable forecast" and shows recent trend facts only.
4. **Offer check:** enter a buyer's quote and compare it with a reference price net of the same costs. Verdict is low, fair or high with a band.
5. **Voice assistant** (Marathi, Hindi, English) routing to the four tools above, replying in the user's language.
6. **Alert rules:** "tell me when Lasalgaon modal price goes above X", evaluated on each data refresh and shown in-app.

## SHOULD build
- Map of mandis with net-in-hand colouring.
- Backtest page showing model vs baseline, so judges can see the gate working.
- Simple outcome log, to start collecting real feedback.

## DO NOT build
A real marketplace, real load matching, WhatsApp sending, payments, authentication beyond a session id, multi-crop UI.

## Demo scenario
An FPO manager near Niphad has 200 quintals of onion on Nov 13, the day Lasalgaon auctions resume after the Diwali pause. The demo shows ranking, hold-or-sell and an offer check on real snapshot data. Savings are shown as "model-estimated versus selling at the nearest mandi today", never as a claim about real farmers. Anything simulated is labelled.

## Calls added after the builder check (mine, not yours)
- **Reference price for the offer check and day-0 hold baseline:** the 3-day median modal price at the nearest mandi for the same variety, net of the same costs. The "fair" band is the interquartile range of that mandi's last 30 days of modal prices. The offer check does not depend on the forecaster gate, so it works even when the gate fails.
- **Distance and quality (revised):** the automatic distance haircut is removed, because I added it on weak evidence. A separate optional "risk allowance" (default 0%) is shown apart from the core ranking. The user picks commodity, variety and grade from those present in the data, since Agmarknet labels are inconsistent, and the app warns that the modal price is not a guaranteed price for their lot.
- **Forecaster and leakage (corrected):** My earlier claim was wrong. Per the model card, May 2026 is when the data was pulled; Mandi-Chronos was fine-tuned on series dated before 2025-06-01. Backtests therefore use dates on or after 2025-06-01, about 17 months if our data reaches back that far. The licence is CC BY-NC-SA 4.0 (non-commercial) and the download is gated, so the classical pipeline must work first and Chronos stays optional. The model card reports WQL against zero-shot Chronos-2 but no interval coverage figures, so we run our own calibration check.
- **Data access fallback:** the first task is to confirm the API works and to pull a snapshot. If it is unreachable, we use a manual CSV export from the Agmarknet portal. If arrivals are missing, the product is price-only.
- **Alerts:** the demo has a "simulate data refresh" button, and alerts are checked on app open. No push notifications.
- **Voice languages:** Hindi and English are the primary demo languages, Marathi is best-effort, until the judging audience is known.
- **Cost defaults:** placeholders, plus one cited Maharashtra APMC commission rate if we can find it quickly.

## Changes approved after external review (2026-11-13)
- **Simulated pooling (new MUST, time-boxed to 1-2 hours):** Inside the transport-cost assumptions, a toggle compares solo against pooled shipping. Pooled cost per quintal = truck_total_cost / min(truck_capacity_qtl, user_lot_qtl + pooled_qtl). Solo cost per quintal = tempo_total_cost / user_lot_qtl. Truck capacity, truck cost and tempo cost are editable assumptions. The pooled quintals come from a few synthetic seed rows, each labelled `[Simulated]`, with a one-card "Pool Match" view. Nothing here claims real coordination. The saving shown is whatever the arithmetic produces; no hardcoded percentage.
- **Data source order (revised):** probe three sources in hour 1: the data.gov.in resources 35985678-0d79-46b4-9ed6-6f13308a1d24 (variety-wise, per the model card) and 9ef84268-d588-465a-a308-a864a43d0070 (current daily, per the second reviewer; unverified), and the CEDA portal. Use the source with daily-fresh data for live prices and the source with the deepest history for the backtest, since CEDA's monthly updates may lag. Manual Agmarknet CSV export is the last fallback.
- **Voice demo safety:** sample prompt chips in Marathi, Hindi and English under the mic button, routed by a deterministic offline parser so the demo works without Gemini or Wi-Fi. Free-form speech still goes through Gemini. The demo laptop must run standard Chrome, since Web Speech recognition fails silently on other browsers.
- **Cost defaults:** commission, hamali and shrinkage are marked `[Unverified placeholder - edit me]`, with a seller pays or buyer pays toggle for commission. They come from an outside review and are not sourced.
- **Geography:** mandi coordinates come from a one-time Nominatim geocoding pass with spot checks. They are never typed from memory.

## Revisions after the second review (2026-11-13, approved)
- **Transport:** per-trip cost by vehicle (tempo, truck) with capacity, instead of a linear per-quintal-km rate. Cost per quintal = trips × (base + per-km × km) / lot quantity, with an optional user-entered quote override. Vehicle costs are placeholders.
- **Cost labels:** every assumption carries a source tag: verified, user-entered or unverified. The UI says "estimated net realization", never "profit".
- **Forecast gate adds calibration:** besides beating both baselines on MAE, the q0.3 quantile's empirical coverage must be within 0.1 of 0.3. Hold recommendations need both. Forecasts only for the demo mandis.
- **Lot model:** commodity, variety and grade, with the origin chosen from a verified list of Nashik-belt places. Free-text villages are postponed.
- **Primary user:** an FPO manager. Pitch and UI language follow that.
- **Priority tiers:** Core = modules 1 to 4 (rank, offer check, hold-or-sell, simulated pooling) plus voice chips. Stretch, done only after the core works and cut first if behind: alerts, Gemini free-form voice routing, mandi map, and a "member lots add up to a total" input.

## Left to the builder
Mandi shortlist and coordinates, exact UI layout, alert evaluation timing, and the specific carrying-cost defaults.

## Open items that only the team can answer
- Team skills (frontend, Python, ML) and how many people.
- Judging criteria, and the real deadline.
- Whether a data.gov.in API key works and the API is reachable from your machines.
- Whether anyone can speak to a real onion FPO manager or trader in Nashik before the demo.
