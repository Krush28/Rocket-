# KRISHI-X — 5-minute pitch script

**PS 23 · AI Mandi Price Intelligence & Farm-to-Market Supply Chain Platform**

Style: Steve Jobs. Short sentences. One idea per slide. Pause after every number. Never read the slide.
Pace: about 130 words a minute, about 650 words in total. Slide numbers match `index.html` (press **N** in the deck for these notes, **T** for the timer).

| Time | Slides | Beat |
|---|---|---|
| 0:00 – 0:40 | 1–2 | The hook: one farmer, one truck, one decision |
| 0:40 – 1:20 | 3–4 | The problem: three things a farmer cannot see |
| 1:20 – 1:40 | 5 | Introducing KRISHI-X |
| 1:40 – 3:20 | 6–11 | Show, don't tell: the product in six moments |
| 3:20 – 4:05 | 12–13 | How it works, and why you can trust it |
| 4:05 – 4:40 | 14 | Who pays, and how big it gets |
| 4:40 – 5:00 | 15–16 | One more thing, and the close |

---

## 1 · Title (0:00 – 0:10)
> *(Walk to centre. Wait two seconds. Smile.)*
>
> Good morning. We're team KRISHI-X.

## 2 · The hook (0:10 – 0:40)
> Imagine a farmer near Nashik. Let's call him Ramesh.
> He has fifty quintals of onion on a tractor. Five months of work.
> This morning he has to make one decision. **Where do I sell?**
> He goes where the board shows the highest price.
> And that is exactly where he loses money.

## 3 · The problem (0:40 – 1:05)
> Because the price on the board isn't the money in his hand.
> Transport. Hamali. Commission. Waiting. Spoilage.
> Farmers keep only about **a third of what we pay** for onions and tomatoes.
> And India loses about **one and a half lakh crore rupees** of food every year between the farm and the plate.

## 4 · Three things he can't see (1:05 – 1:20)
> Ramesh can't see three things.
> **One**: what he'll actually *keep* at each mandi.
> **Two**: whether the price will go up next week.
> **Three**: a truck, a buyer, or cold storage, when he needs them.
> Three blind spots. We built one app to fix all three.

## 5 · Introducing KRISHI-X (1:20 – 1:40)
> This is KRISHI-X.
> No forms. No menus. No English required.
> He just **talks to it**, in Marathi, Hindi or English.

## 6 · Moment 1: he speaks (1:40 – 1:55)
> Ramesh says: *"I have fifty quintal onion and twenty quintal tomato near Nashik."*
> It understands both crops, both amounts and his village, then reads it back and asks: is this correct?
> Nothing happens without his **yes**.

## 7 · Moment 2: the number (1:55 – 2:20)
> And then, the only number that matters.
> **Sell at Pimpalgaon Baswant today. You take home two lakh, six thousand, seven hundred eighty-eight rupees.**
> Not the board price. What's **left in his hand** after every cost, line by line, like a settlement slip.

## 8 · Moment 3: the map (2:20 – 2:40)
> Here's every mandi on a real road map.
> The second-best mandi is about the same distance away.
> But choosing it would cost him **eighteen thousand, nine hundred rupees**.
> *(Pause.)* That's one decision. Same morning. Same onions.

## 9 · Moment 4: sell or hold (2:40 – 2:55)
> Should he wait? KRISHI-X forecasts the price, and it gives a forecast **only if it beat simple baselines on past data**.
> If it isn't sure, it says *"insufficient data."* We'd rather be honest than confident.
> And it checks his farm's weather: good dry weather, safe to transport.

## 10 · Moment 5: in his language (2:55 – 3:05)
> All of it in Marathi. In Hindi. On a ₹6,000 phone.

## 11 · Moment 6: the whole chain moves (3:05 – 3:20)
> He says *"yes, create the order."*
> A truck request goes out to every transporter nearby, with a booking token.
> FPOs see their members' produce. Warehouses get storage requests.
> **Farmer, FPO, transporter, warehouse, buyer**, one platform.

## 12 · How it works (3:20 – 3:45)
> Under the hood, **twelve AI agents** work together:
> mandi discovery, price intelligence, forecasting, transport, spoilage, storage, sell-or-hold, net realization.
> **Live government prices** from more than **1,600 mandis**.
> An offline map of **5.6 lakh villages** and every pincode.
> A small AI model that runs **locally**, with no cloud bill and no data leaving India.

## 13 · Trust (3:45 – 4:05)
> And three rules we never break.
> **The AI never does the maths.** Every rupee is calculated by deterministic code.
> **We never invent a price.** Estimates are labelled as estimates.
> **Nothing happens without the farmer's yes.**

## 14 · Business (4:05 – 4:40)
> How do we make money? Exactly as the problem statement asks.
> A small **commission** on marketplace sales.
> **Logistics coordination fees** when we fill a truck.
> **Subscriptions** for FPOs and traders.
> And our **price-intelligence API** for processors, lenders and insurers.
> India has more than 7,000 regulated mandis and over 14 crore farm families. Even a sliver of that is huge.

## 15 · One more thing (4:40 – 4:52)
> *(Step forward.)* Oh… one more thing.
> Everything you saw today is **running right now, live**, with real prices from this week. Not a mock-up.

## 16 · Close (4:52 – 5:00)
> Farmers don't need more information.
> They need **one honest answer**.
> **KRISHI-X. Know what you keep, before you sell.**
> Thank you.

---

### Numbers you'll say aloud (and where they come from)
| Claim | Source |
|---|---|
| ₹2,06,788 take-home; ₹18,905 more than the 2nd-best mandi; 50 qtl onion, Nashik → APMC Pimpalgaon Baswant | Live run of KRISHI-X on 2026-11-14 (screenshots in `assets/shots/`) |
| Farmers keep about a third of the consumer rupee (tomato about 33%, onion about 36%) | RBI working paper on vegetable inflation and farmer share, 2024 |
| About ₹1.53 lakh crore of post-harvest losses a year | NABCONS study for the Ministry of Food Processing Industries, 2022 |
| 1,686 mandis with live prices; 5.6 lakh places and 1.55 lakh pincodes offline; 12 agents; 110 automated tests | This repo (`docs/PRD.md`, `backend/tests`) |
| More than 7,000 regulated markets; about 14 crore farm holdings | Ministry of Agriculture (APMC count), Agriculture Census |

### If a judge asks…
- **"Is the forecast real?"** It's SARIMA plus gradient boosting behind a backtest gate. It must beat the baselines by 5%, with a calibrated 80% interval and at least 120 days of history. Otherwise it says "insufficient data".
- **"What if there's no internet?"** Places are looked up offline, the local LLM and Piper voice run on the device or server, and browser speech works as a fallback.
- **"Why not just ChatGPT?"** A chatbot guesses numbers. Ours never lets the model touch money, it cites the source and age of every price, and it asks yes/no before anything with consequences.
- **"What's next?"** Real transporter quotes, phone-OTP login, WhatsApp alerts, a 3-year price history backfill, and a Flutter app on the same `/api/agent`.
