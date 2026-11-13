# KRISHI-X

**AI that finds the most profitable route from farm to market.**

KRISHI-X is a voice-first mandi price intelligence and farm-to-market supply-chain platform. This starter establishes the project structure and the first working milestone: a farmer can chat by text, record a voice message, capture crop/quantity/location/readiness details, and review a structured profile before market agents are connected.

## Product boundaries
- Focus: mandi price intelligence, market discovery, buyer matching, transport coordination and net realization.
- No Aadhaar collection or verification.
- No crop disease diagnosis.
- Demo responses are explicitly labelled. Never treat sample prices, buyer offers or transport costs as live data.

## Repository structure

```text
KRISHI-X/
├── apps/
│   ├── web/                 # Next.js farmer web app (voice + text)
│   └── mobile/              # Reserved for Flutter mobile client
├── backend/
│   ├── app/
│   │   ├── api/routes/      # HTTP endpoints
│   │   ├── agents/          # Future market/buyer/transport agents
│   │   ├── conversation/    # Conversation state + profile extraction
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── services/        # Speech and domain services
│   └── tests/
├── data/                    # Sample/demo data only
├── docs/                    # Architecture and API notes
├── scripts/
└── .env.example
```

## Start locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Web app
```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `apps/web/.env.local` if needed.

To use PostgreSQL, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/krishi_x` in the backend environment.

## Current milestone
- Text chat with simple slot extraction for crop, quantity, location and readiness.
- Browser microphone recording and upload endpoint.
- Optional Faster-Whisper transcription (install `faster-whisper` separately; model download occurs on first use).
- Profile confirmation before any market search.
- SQLite-backed conversation sessions and farmer-intake profiles (switchable to PostgreSQL with `DATABASE_URL`).
- Language detection and English/Hindi intake prompts; quantity normalization for kg, tonnes and quintals.
- Optional capture of variety, quality grade, selling preference and storage ability.

## Important limitations
This is a development starter, not a production deployment. The current extraction is deterministic and supports a limited set of English/Hindi patterns; it is not a general-purpose multilingual LLM extractor. Database tables are currently created at startup with SQLAlchemy metadata; add Alembic migrations before production schema changes. The SQLite default is suitable for local development, while PostgreSQL is the intended shared deployment database. Browser speech recognition is not assumed; audio is sent to the backend transcription endpoint.

## Next build milestones
1. Replace rule-based extraction with multilingual LLM/NER extraction and language-aware prompts.
2. Add multilingual text-to-speech playback.
3. Persist conversations and farmer profiles in PostgreSQL/PostGIS.
4. Connect verified mandi data sources and build the Mandi Discovery + Price Intelligence agents.
5. Add buyer discovery, transport estimates/quotes, and the Net Realization Engine.
6. Add FPO/buyer/transporter workspaces and mobile app.

## Net realization rule
`Net Realization = Expected Sale Revenue - Transport - Handling - Storage - Expected Loss`

If expected loss is represented by reducing saleable quantity, do not subtract its value a second time.
