Title: Cloud AI brain (Gemini) with fallbacks, conversation memory, schemes by state / kind / name

## What this adds
- **Cloud brain:** `KRISHIMITRA_LLM=gemini|ollama|auto` plus `GEMINI_API_KEY` (free key from aistudio.google.com/apikey). Cloud first, local Ollama next, rules last. The key goes in a header, never the URL. A failed cloud call pauses the cloud for 60 s so replies stay fast.
- **Wider use of the brain with a cloud model:** sentences of 4+ words go to the planner; exact commands and anything with typed numbers stay on the rules.
- **Conversation memory:** the last turns are passed as context, so "why not the second option" works.
- **Schemes by voice:** `schemes.parse()` reads state, kind (insurance / income / MSP / storage / farm support) and scheme name from plain words in en / hi / mr. Works with no LLM. `/api/schemes` takes `category` and `q`; the schemes page takes `cat` and `q`.
- **Scheme data:** 36 schemes (was 20), 13 states + central. Every new portal URL was checked to respond.
- **UI:** a "Cloud AI" label when a sentence was sent to the cloud model (`ai` field in the agent reply).

Unchanged: Python runs every tool and does all money maths; numbers the model invents are rejected; orders and bookings wait for a yes.

## Tested
- `pytest tests -q`: 105 pass (101 existing + 4 new), on SQLite outside Docker.
- `npx tsc --noEmit` in `apps/web`: clean.
- Live against Gemini (about 2 s a turn): Hindi, Marathi and Hinglish scheme requests, sell-or-hold plus forecast, two-part requests, order confirmation.

## Not tested
- The full Docker stack in a browser, and voice.
- `app/qa/bughunt.py` has not been re-run with the cloud brain.

## Known gaps
- Hinglish (Hindi in Latin letters) is detected as English, so replies come in English.
- "how far is that one" routed to transport instead of a distance answer.
- States without their own schemes show central schemes only.

## Separate issue to discuss
`backend/app/core/present.py` removes the DEMO / simulated labels from user-facing text. Demo buyers and cold stores then look real. This PR does not change that.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
