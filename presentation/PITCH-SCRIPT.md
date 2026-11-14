# KRISHI-X — pitch script (7 slides · 5 min incl. live demo · 3 min Q&A)

**PS 23 · AI Mandi Price Intelligence & Farm-to-Market Supply Chain Platform**

Rules from the organisers: **max 7 slides**, **5 minutes for PPT + prototype**, then **3 minutes of Q&A**.
Style: Steve Jobs. Short sentences. Pause after every number. Never read the slide.
In the HTML deck press **N** for these notes and **T** for the timer. In PowerPoint use Presenter View (Alt+F5).

| Time | Slide | Who / what |
|---|---|---|
| 0:00 – 0:30 | 1 · Hook | One farmer, one decision |
| 0:30 – 1:05 | 2 · Problem | Board price vs money in hand · three blind spots |
| 1:05 – 1:35 | 3 · Solution | “He just talks to it” · ₹2,06,788 · +₹18,905 |
| **1:35 – 3:35** | **4 · Live demo** | **Prototype in the browser, 2 minutes** |
| 3:35 – 4:15 | 5 · Under the hood | 12 agents · live data · 3 trust rules |
| 4:15 – 4:45 | 6 · Business | Free for the farmer, paid by the chain |
| 4:45 – 5:00 | 7 · Close | One honest answer · thank you |

Tip: split it between two people. **Speaker A** does slides 1–3 and 5–7; **Speaker B** drives the demo on slide 4, with the app already open in a second tab.

---

## 1 · Hook (0:00 – 0:30)
> Good morning. We're team KRISHI-X.
> Imagine a farmer near Nashik. Let's call him Ramesh.
> Fifty quintals of onion on a tractor. Five months of work.
> And this morning, one decision. *(click)* **Where do I sell?**
> He goes where the board shows the highest price, and that's exactly where he loses money.

## 2 · Problem (0:30 – 1:05)
> Because the board price isn't the money in his hand.
> Transport. Hamali. Commission. Waiting. Spoilage.
> Farmers keep only about **a third** of what we pay for onions and tomatoes.
> India loses about **one and a half lakh crore rupees** of produce a year between farm and plate.
> *(click ×3)* Ramesh can't see three things: **what he'll keep**, **where the price is going**, and **a truck, a buyer or storage** when he needs one.

## 3 · Solution (1:05 – 1:35)
> Meet **KRISHI-X**. No forms. No menus. No English needed.
> He just **talks to it**, in Marathi, Hindi or English.
> *"Fifty quintal onion, twenty quintal tomato near Nashik."*
> One answer: **sell at Pimpalgaon Baswant today. You keep two lakh, six thousand, seven hundred eighty-eight rupees**, after every cost.
> The second-best mandi is the same distance away. It would have cost him **eighteen thousand nine hundred rupees**.
> Let me show you. It's live.

## 4 · Live demo (1:35 – 3:35) — Speaker B drives
Prepare before you go on stage: open `http://localhost:3000` in a **fresh/incognito window** (new session), zoom so the text is readable from the back, and keep the transporter portal open in a second tab (log in at `/login` as a transporter).

| # | Do / say in the app | Say to the judges (one line) | ~sec |
|---|---|---|---|
| 1 | Type or say **“I have 50 quintal onion and 20 quintal tomato near Nashik”** | “Two crops, two amounts, a village, from one sentence.” | 15 |
| 2 | It asks *ready now?* → **yes**; *can you store?* → **no**; read-back → **yes** | “It reads back. Nothing happens without his yes.” | 20 |
| 3 | Results load: point at the big number and the settlement slip | “Not the board price: what's left in his hand, line by line.” | 20 |
| 4 | Scroll: **map** (road route) → **weather** card; ask **“will the price go up?”** | “Real road distance. His farm's weather. Forecasts only when they pass a backtest.” | 30 |
| 5 | Tap **मरा** (Marathi) | “The same answer, in his language.” | 10 |
| 6 | Say **“create the order”** → **yes**; switch to the transporter tab and refresh | “And the chain moves: a truck request with a booking token, live.” | 25 |

Back to the slides at **3:35**.
**If anything fails** (Wi-Fi, mic): say *“Here's what you'd see”*, go back to slide 3 (it's all real screenshots), and continue. Type instead of speaking if the room is noisy.
**Avoid:** saying “book transport” after the order is created (it replies with a technical message: known rough edge).

## 5 · Under the hood (3:35 – 4:15)
> Under the hood: **twelve AI agents** working together: mandi discovery, prices, forecasting, transport, spoilage, storage, sell-or-hold.
> **Live government prices** from 1,686 mandis. An offline map of **5.6 lakh villages**.
> Our own small AI model runs **locally**: no cloud bill, no data leaving India.
> *(click ×3)* And three rules we never break. **The AI never does the maths.** **We never invent a price.** **Nothing happens without the farmer's yes.**

## 6 · Business (4:15 – 4:45)
> One platform for the whole chain: farmer, FPO, transporter, cold storage, buyer.
> **Free for the farmer. Paid by the chain**: a small **commission** on matched sales, **logistics fees** per booked truck, **subscriptions** for FPOs and traders, and a **price-intelligence API** for processors, lenders and insurers.
> More than 7,000 regulated mandis. 14 crore farm holdings. Even a sliver is huge.

## 7 · Close (4:45 – 5:00)
> Farmers don't need more information.
> They need **one honest answer**.
> **KRISHI-X. Know what you keep, before you sell.**
> Thank you. We'd love your questions.

---

## Q&A (3 minutes): keep each answer to 20–30 seconds
Have `diagrams.html` open in a tab: farmer journey (UML), architecture, agent workflow, order lifecycle.

- **“Is the forecast real?”** SARIMA plus gradient boosting behind a backtest gate: it must beat simple baselines by 5% with a calibrated 80% interval and at least 120 days of history. Otherwise it says “insufficient data”.
- **“Where does the price data come from?”** data.gov.in / Agmarknet (official), plus the keyless Mandi API on a 6-hourly import. Every number shows its source and age.
- **“Why not just ChatGPT?”** A chatbot guesses numbers. Ours never lets the model touch money, and asks yes/no before anything with consequences.
- **“What about poor internet?”** Village lookup is offline (5.6 lakh places), the LLM and voice run locally, and browser speech is the fallback.
- **“How is transport cost calculated?”** Road distance × the transporter rate card, labelled ESTIMATE until a transporter gives a verified quote.
- **“How do you reach farmers?”** Through FPOs: one FPO head onboards hundreds of members; FPO subscriptions fund it.
- **“How do you make money / scale?”** Free for farmers; buyers pay ~0.75% on matched sales, transporters ~₹150 per load, FPOs a subscription, processors and lenders for the price API. Pilot in Nashik with 3–5 FPOs → Maharashtra → 5 states. One demo load earns us ≈₹1,700 while the farmer keeps ₹18,905 more. Details: `BUSINESS-MODEL.md`.
- **“What's next?”** Real transporter quotes, phone-OTP login, WhatsApp alerts, a 3-year price history backfill, and an Android app on the same API.
- **Show the architecture:** open `diagrams.html#arch` (or `#agents` for the agent workflow).

### Numbers you'll say aloud (and where they come from)
| Claim | Source |
|---|---|
| ₹2,06,788 take-home; ₹18,905 more than the 2nd-best mandi; 50 qtl onion, Nashik → APMC Pimpalgaon Baswant | Live run of KRISHI-X, 14 Nov 2026 (`assets/shots/`) |
| Farmers keep about a third of the consumer rupee (tomato ≈33%, onion ≈36%) | RBI working paper on farmer share in vegetable prices, 2024 |
| ≈ ₹1.53 lakh crore post-harvest losses a year | NABCONS study for the Ministry of Food Processing Industries, 2022 |
| 1,686 mandis; 5.6 L places + 1.55 L pincodes offline; 12 agents | This repo (`docs/PRD.md`) |
| 7,000+ regulated markets; ≈14 crore farm holdings | Ministry of Agriculture (APMC count), Agriculture Census |
