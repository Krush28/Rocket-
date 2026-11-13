"""KRISHIMITRA API (KRISHI-X engine). Run: uvicorn app.main:app --reload  (from krishimitra/backend)"""
import os
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import adapters, agent, demo_data as D, forecast as F, llm, orchestrator, orders, profile as P

app = FastAPI(title="KrishiMitra - KRISHI-X engine", version="0.1.0")
FRONT = Path(__file__).resolve().parents[2] / "frontend"


class ChatIn(BaseModel):
    session_id: str | None = None
    text: str = ""
    lang: str | None = None


class LotIn(BaseModel):
    crop: str
    qty_kg: float = Field(gt=0)
    place: str
    ready: bool = True
    can_store: bool = False
    lang: str = "en"
    assumptions: dict | None = None


class OrderIn(BaseModel):
    option: dict
    profile: dict


class EventIn(BaseModel):
    event: str
    data: dict | None = None


@app.on_event("startup")
def warm():
    def go():  # precompute forecasts so the first user request is fast
        for c in D.CROPS:
            for m in D.MANDIS:
                try:
                    F.forecast(c, m)
                except Exception:
                    pass
    threading.Thread(target=go, daemon=True).start()

    def auto_refresh():  # keep prices live: pull every 3 hours when a key is configured
        import time
        while adapters.api_key():
            try:
                adapters.refresh()
                F.forecast.cache_clear()
            except Exception:
                pass
            time.sleep(3 * 3600)
    if adapters.api_key():
        threading.Thread(target=auto_refresh, daemon=True).start()

    def watch():  # auto-import the daily CSV the moment it lands in Downloads
        import time
        while True:
            try:
                if adapters.scan_and_import():
                    F.forecast.cache_clear()
            except Exception:
                pass
            time.sleep(30)
    threading.Thread(target=watch, daemon=True).start()


@app.get("/api/health")
def health():
    live = adapters.live_mode()
    return {"ok": True, "data_mode": "LIVE" if live else D.DEMO, "llm": "ollama" if llm.enabled() else "off (rules + templates)",
            "live_adapters": ["data.gov.in"] if live else [], "key_configured": bool(adapters.api_key()), "last_import": adapters.last_import(), "watching": [str(d) for d in adapters.watch_dirs()],
            "note": "Live mandi prices loaded." if live else "No live rows yet. Set DATA_GOV_API_KEY and POST /api/admin/refresh. Until then all market data is DEMO DATA."}


@app.post("/api/admin/scan")
def scan():
    """Check the watched folders for a new price CSV right now."""
    r = adapters.scan_and_import()
    if r:
        F.forecast.cache_clear()
    return {"imported": r, "watching": [str(d) for d in adapters.watch_dirs()]}


@app.post("/api/admin/refresh")
def refresh():
    """Pull today's prices from data.gov.in into the local snapshot store (needs DATA_GOV_API_KEY)."""
    if not adapters.api_key():
        raise HTTPException(400, "DATA_GOV_API_KEY is not set (env var or backend/.env)")
    F.forecast.cache_clear()
    return adapters.refresh()


@app.get("/api/meta")
def meta_():
    return {"crops": list(D.CROPS), "places": sorted({k.title() for k in D.PLACES if k.isascii()}), "mandis": list(D.MANDIS)}


class AgentIn(BaseModel):
    session_id: str | None = None
    text: str = ""
    lang: str | None = None


@app.post("/api/agent")
def agent_endpoint(b: AgentIn):
    """The action agent: free-form request -> tools that open views, change the plan, or (after confirmation) create orders."""
    return agent.handle(b.session_id or uuid.uuid4().hex[:10], b.text, b.lang)


@app.post("/api/chat")
def chat(b: ChatIn):
    sid = b.session_id or uuid.uuid4().hex[:10]
    r = P.chat(sid, b.text, b.lang)
    r["session_id"] = sid
    if r["done"]:
        r["plan"] = orchestrator.run(r["profile"])  # market work starts ONLY after explicit confirmation
    return r


@app.post("/api/plan")
def plan(b: LotIn):
    key = b.place.strip().lower()
    if key not in D.PLACES:
        raise HTTPException(422, f"Unknown place. Known (demo): {sorted(k for k in D.PLACES if k.isascii())}")
    if b.crop not in D.CROPS:
        raise HTTPException(422, f"crop must be one of {list(D.CROPS)}")
    prof = {"crop": b.crop, "qty_kg": b.qty_kg, "original_qty": b.qty_kg, "original_unit": "kg",
            "location": {"name": b.place.title(), "lat": D.PLACES[key][0], "lon": D.PLACES[key][1]}, "ready": b.ready, "can_store": b.can_store, "lang": b.lang}
    return orchestrator.run(prof, b.assumptions)


@app.get("/api/forecast")
def forecast(crop: str, mandi: str):
    if crop not in D.CROPS or mandi not in D.MANDIS:
        raise HTTPException(404, "unknown crop or mandi")
    return F.forecast(crop, mandi)


@app.get("/api/series")
def series(crop: str, mandi: str, days: int = 180):
    if crop not in D.CROPS or mandi not in D.MANDIS:
        raise HTTPException(404, "unknown crop or mandi")
    df = D.series(crop, mandi).tail(days)
    return {"label": D.DEMO, "history": [[str(d.date()), float(v)] for d, v in zip(df["date"], df["modal"])], "forecast": F.forecast(crop, mandi)}


@app.post("/api/orders")
def create_order(b: OrderIn):
    return orders.create(b.option, b.profile)


@app.get("/api/orders")
def list_orders():
    return orders.list_all()


@app.post("/api/orders/{oid}/event")
def order_event(oid: str, b: EventIn):
    try:
        return orders.event(oid, b.event, b.data)
    except KeyError:
        raise HTTPException(404, "order not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/")
def index():
    return FileResponse(FRONT / "index.html")


app.mount("/static", StaticFiles(directory=FRONT), name="static")
