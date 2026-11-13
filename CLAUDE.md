# Project instructions for any coding agent

Read `docs/HANDOFF.md` FIRST: it explains the vision, what is built, what is fake, decisions, gotchas and next steps.

Non-negotiables (details in the handoff):
- Never fabricate prices, buyers, warehouses, transporters or phone numbers. Label anything synthetic DEMO / [Simulated]. Costs are ESTIMATES.
- All money maths is deterministic Python. An LLM may only choose a tool or phrase text.
- Orders/bookings/confirmations always ask the farmer yes/no first.
- Never commit `backend/.env`, `*.db`, `.venv`. Do not scrape past captchas.
- Ask the owner before pushing to GitHub (repo Krush28/Rocket-, branch `krishimitra`). Keep answers short and scannable.
- Update `docs/HANDOFF.md` (Status + Next steps) whenever you finish something.
