# Build roadmap

Design: [docs/superpowers/specs/2026-11-13-krishi-x-design.md](superpowers/specs/2026-11-13-krishi-x-design.md)

## Phase 1: foundation (done, 2026-11-13)
- [x] Rocket engine ported into the layered backend (12 agents, orchestrator, costs, forecasting gate, OR-Tools, orders)
- [x] PostgreSQL + PostGIS in Docker, Alembic migration 0001
- [x] Real all-India price CSV imported (16,038 rows, 1,686 mandis, 242 commodities, 13 Nov 2026)
- [x] Mandi + farmer-place geocoding (Nominatim, cached, approximate)
- [x] Voice/text intake (en/hi/mr, auto-detect), DB-persisted sessions, confirm gate, profile + inventory saved
- [x] API: chat, plan, market, orders, admin (token), rate limit
- [x] Next.js assistant + settlement-slip results, mobile-first
- [x] Dockerised stack, docs

## Next
- [ ] Phase 2: LLM-backed multilingual extraction and explanations (agent reasons still English in hi/mr), more languages, TTS polish, mic tests on devices
- [ ] Phase 3: 3-year history backfill from resource 35985678 (needs own DATA_GOV_API_KEY), daily ingestion job, retail source, data validation
- [ ] Phase 4: SARIMA / XGBoost / LightGBM in the backtest gate, model registry tables
- [ ] Phase 5: Sell-vs-hold + net realization on DB history; crop shelf-life table beyond onion/tomato/potato
- [ ] Phase 6: real cold-storage registry, availability, enquiries
- [ ] Phase 7: transporter registry, quotes, real shared-load matching
- [ ] Phase 8: auth + RBAC, buyer marketplace, FPO/transporter/warehouse/admin portals
- [ ] Phase 9: orders/notifications in Postgres, Celery/Redis jobs, accounting
- [ ] Phase 10: hardening, CI/CD, deployment
- [ ] Flutter mobile client
