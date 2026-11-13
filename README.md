# Rocket: KrishiMitra (KRISHI-X engine)

Voice-first assistant that ranks where a farmer should sell by **estimated net earnings** (after transport, handling, storage, loss), with an honest forecast gate and a sell-now-vs-hold verdict.

```
krishimitra/   app: FastAPI backend, agents, tests, single-page frontend  (start here: krishimitra/README.md)
data/raw/      real daily mandi prices, data.gov.in (Agmarknet), 13 Nov 2026, 16,038 rows
design/        Design-canvas source for the UI redesign (settlement-slip direction)
docs/          early design notes and the list of reference repos
```

Run: see `krishimitra/README.md`. On startup the server auto-imports `data/raw/*.csv`, so a fresh clone starts in LIVE mode with that day's real prices.

Honest status: mandi prices are real (one day of history, so hold forecasts stay locked); warehouses, transporters, buyers and pooled farmers are DEMO; costs are editable placeholders; voice is untested with a real microphone.
