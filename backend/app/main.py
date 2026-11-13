"""KRISHI-X API. Run in Docker: `docker compose up backend` (applies migrations, then serves on :8000)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

from app.api.routes import admin, agent, chat, market, orders, voice, ops
from app.core import ratelimit
from app.core.config import settings
from app.db import database
from app.models import MandiPrice
from app.repositories import market_data as MD

app = FastAPI(title="KRISHI-X API", version="0.2.0",
              description="Voice-first mandi price intelligence: net realization, sell vs hold, storage and transport.")
app.middleware("http")(ratelimit.middleware)  # registered first = inner layer, so CORS headers also reach 429 responses
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Admin-Token"])
for r in (agent.router, chat.router, market.router, orders.router, admin.router, voice.router, ops.router):
    app.include_router(r, prefix="/api")


@app.on_event("startup")
def _warm():
    """Load offline voices in the background so the first spoken reply is fast (no-op if Piper is not installed)."""
    from app.services import tts
    tts.warm()
    from app.services import llm
    llm.warm()
    from app.services.adapters import mandi_api  # live prices + history from the keyless Mandi API, refreshed every 6 h (resumable)
    mandi_api.start_background()
    try:  # storage network for every district that has a mandi (idempotent)
        from app.db.database import SessionLocal
        from app.services import ops
        with SessionLocal() as db:
            ops.seed_warehouses(db)
    except Exception as e:
        print("warehouse seed skipped:", e, flush=True)


@app.get("/health")
def health():
    try:
        with database.SessionLocal() as s:
            s.execute(text("select 1"))
            last = s.scalar(select(func.max(MandiPrice.price_date)))
        ok = True
    except Exception:
        ok, last = False, None
    return {"status": "ok", "db": ok, "data_mode": ("LIVE" if MD.live() else "DEMO DATA") if ok else "unknown",
            "last_price_date": str(last) if last else None}
