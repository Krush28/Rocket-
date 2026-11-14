# KRISHI-X — business model & scale-up plan

> One line: **free for the farmer, paid by the supply chain that KRISHI-X coordinates.**
> Every rupee we help a farmer keep moves through a truck, a store and a buyer. Each of them pays a little for being matched, filled and paid on time.

Numbers marked **(assumption)** are planning hypotheses to test in the pilot, not measured results. Market figures are approximate and should be quoted with their source.

---

## 1. Who we serve and what each one gets

| Customer (from PS 23) | Their pain | What KRISHI-X gives them | Pays? |
|---|---|---|---|
| **Farmer** | Sells at the highest *board* price, not the highest *take-home* | Voice answer in mr/hi/en: best mandi by net in hand, sell or hold, truck, storage | **Free** (always) |
| **FPO** (Farmer Producer Organisation) | Can't see members' produce; trucks go half-empty | Member dashboard, pooled loads, sales pipeline, price alerts | Subscription |
| **Transporter / logistics fleet** | Empty return trips, no steady loads | Booking tokens for loads near them, routes, shared loads | Fee per booked load |
| **Cold-storage / warehouse** | Unused capacity, no demand signal | Storage requests from farmers who should *hold* | Fee per booking |
| **Mandi trader / wholesale buyer** | Uncertain supply, last-minute sourcing | Visibility of upcoming produce by crop, quantity, place | Commission on matched sale |
| **Food processor / exporter** | Procurement price risk | Price-intelligence feed + direct FPO supply | API / data subscription |
| **Lender / insurer** (later) | Can't value a farmer's crop | Price history + forecasts by mandi and crop | Data API |

## 2. Revenue streams (the four in PS 23)

| Stream | How it's charged | Indicative price **(assumption)** | Why they'll pay |
|---|---|---|---|
| **1. Marketplace commission** | % of the sale value of orders matched through KRISHI-X, charged to the **buyer** | 0.5–1% | Cheaper and more reliable sourcing than calling 10 commission agents |
| **2. Logistics coordination fee** | Per booked truck (or % of freight), charged to the **transporter** | ₹100–200 per load, or 5–8% of freight | Fewer empty kms; loads come to them |
| **3. FPO & trader subscriptions** | Monthly SaaS | FPO ₹2,000–5,000/month; trader ₹1,000–3,000/month | Member management, pooled loads, alerts, reports |
| **4. Price-intelligence API** | Monthly data plan by volume | ₹25,000–2,00,000/month | Clean, geocoded mandi prices + backtested forecasts with confidence |
| *Later: storage booking fee* | Per booking, charged to the **warehouse** | 3–5% of storage rent | Fills idle capacity |
| *Later: embedded finance referrals* | Referral fee from lenders/insurers | per sanctioned loan or policy | Better risk data on the farmer's crop |

**Rule:** the farmer never pays, and every fee is shown to them. Trust comes before monetisation.

## 3. Unit economics: one example load (from the live demo)

50 quintal onion, Nashik → APMC Pimpalgaon Baswant, sale ≈ ₹2,08,950.

| | Amount |
|---|---|
| Extra money the farmer keeps vs the 2nd-best mandi | **₹18,905** (measured in the app) |
| Buyer commission at 0.75% **(assumption)** | ₹1,567 |
| Transporter fee per load **(assumption)** | ₹150 |
| **KRISHI-X revenue for this load** | **≈ ₹1,700** |
| Cost to serve the AI answer | ≈ ₹0: the LLM, voice and maps run locally or on free, open services (data.gov.in, OpenStreetMap, OSRM, Open-Meteo) |

The farmer gains ~11× what we earn on that load. That gap is what makes the model fair and defensible.

## 4. How we scale: 4 phases

| Phase | Where / what | Go-to-market | Target **(assumption)** |
|---|---|---|---|
| **0 · Pilot** (0–6 months) | Nashik onion & tomato belt (Lasalgaon, Pimpalgaon, Sinnar) | 3–5 FPOs, 1 transporter group, 1 cold-store; field staff at mandis; demo days at KVKs | 5,000 farmers; measure ₹ gained per farmer, repeat use, truck fill rate |
| **1 · Maharashtra** (6–18 months) | Onion, tomato, grapes, pomegranate, soybean, cotton | FPO federations (state FPO networks); agri-input dealers as referral points; WhatsApp + missed-call voice line | 100 FPOs, 1 lakh farmers |
| **2 · Five states** (18–36 months) | MP, Karnataka, Gujarat, UP, Rajasthan | Add Kannada, Gujarati, Punjabi; state partners; e-NAM / ONDC listing | 1,000 FPOs, 10 lakh farmers |
| **3 · National + data platform** | All states; B2B price API | Processors, exporters, banks, insurers buy the data feed | Price API as a second engine of revenue |

**Why the product scales cheaply**
- **Geography is data, not code:** the system already covers 1,686 mandis across India and 5.6 lakh villages offline. A new state needs price data and local names, not a rebuild.
- **Language is a dictionary:** every farmer-facing sentence exists in en/hi/mr. A new language is a new column, reviewed by native speakers.
- **Any crop:** 75+ crops with local names today; category rules handle the rest.
- **Near-zero marginal cost per query:** our fine-tuned local model (`krishix`) and offline voice mean no per-call cloud AI bill.

## 5. Distribution: how farmers actually get it

1. **Through FPOs first.** One FPO head onboards hundreds of members, and the FPO subscription pays for it. It is the cheapest channel per farmer.
2. **At the mandi gate.** QR posters and field staff on peak arrival days ("check what you'll keep before you unload").
3. **Agri-input dealers and KVKs** as trusted referral points.
4. **Phones without the app:** WhatsApp voice notes and a missed-call IVR line run on the same `/api/agent` brain.
5. **Word of mouth:** the "you kept ₹18,905 more" moment is shareable by design.

## 6. Moats: why we stay ahead

- **Data network effect:** every matched order adds real transaction prices, transport quotes, arrival volumes and storage capacity that public data doesn't have. Better data gives better answers, which brings more farmers.
- **Two-sided liquidity:** once a cluster has farmers *and* transporters *and* buyers, a newcomer has to rebuild all three.
- **Trust rules as brand:** the AI never does the maths, never invents a price, and nothing happens without "yes". These are hard to copy for chatbot-first competitors.
- **Cost structure:** local AI and open data keep our cost per farmer close to zero.

## 7. Technology scale-up (from `docs/PRD.md` roadmap)

| Need at scale | Plan |
|---|---|
| Millions of sessions, many servers | Move agent state and orders to Postgres (today partly in memory/SQLite); shared rate limiting |
| Fast nearby-mandi search | PostGIS radius queries (already indexed) instead of in-process distance scans |
| Better forecasts | 3-year price history backfill + daily import; SARIMA/LightGBM behind the existing backtest gate; model registry |
| Real logistics | Transporter onboarding, verified quotes (replacing estimates), OR-Tools shared-load matching on real loads |
| Identity & payments | Phone-OTP login, roles; UPI payment confirmation for sale settlement |
| Reach | WhatsApp/SMS notifications; Android app on the same API |
| Reliability | CI (tests + build), monitoring, background job queue |

## 8. Illustrative 3-year revenue **(all assumptions)**

Assumptions: each active farmer routes ≈ ₹40,000 of sales/year through KRISHI-X; 0.75% buyer commission; ₹150 per booked truck; FPO plan ₹3,000/month.

| | Year 1 (pilot) | Year 2 (Maharashtra) | Year 3 (5 states) |
|---|---|---|---|
| Active farmers | 5,000 | 1,00,000 | 10,00,000 |
| FPOs | 5 | 100 | 1,000 |
| Matched sales (GMV) | ₹20 cr | ₹400 cr | ₹4,000 cr |
| Commission (0.75%) | ₹15 L | ₹3 cr | ₹30 cr |
| Logistics fees | ₹4.5 L (3k loads) | ₹75 L (50k loads) | ₹7.5 cr (5 L loads) |
| FPO subscriptions | ₹1.8 L | ₹36 L | ₹3.6 cr |
| Price API | — | ₹60 L (10 clients) | ₹6 cr (50 clients) |
| **Total** | **≈ ₹21 L** | **≈ ₹4.7 cr** | **≈ ₹47 cr** |

## 9. Metrics we track

North star: **₹ extra kept per farmer per season.** Also: weekly active farmers · matched GMV · take rate · truck fill rate and empty-km saved · repeat sellers · forecast accuracy vs baselines · cost per farmer acquired (by channel).

## 10. Risks and how we handle them

| Risk | Mitigation |
|---|---|
| Commission agents (adatiyas) resist | Bring them on as buyers and partners; we add volume, not just remove margin |
| APMC rules differ by state | Start with the platform role (information + logistics); transactions follow each state's rules |
| Bad or stale public price data | Validation rules; show source + age on every number; "insufficient data" instead of guessing |
| Farmers' trust in a new app | FPO-led onboarding, voice in their language, yes/no confirmation, free forever |
| Low smartphone use | WhatsApp voice and missed-call IVR on the same brain |
| Price swings make a forecast wrong | Forecasts only after a backtest; intervals, not promises; sell-or-hold advice shows its reasons |

## Ask (for judges / incubators)
Pilot partners: **3–5 FPOs in Nashik district**, one transporter group, one cold-storage operator, and a data.gov.in API key for the full 3-year price history.
