"""Farmer dashboard: everything about one farmer (device) in one call, for the final screen.
Crops with the best option, sell-or-hold verdict, forecast and confidence; sale tickets with their transport token; storage bookings
(or the suggested store when nothing is booked); transporter contacts; the conversation; alerts.

Honesty rules: every number comes from the deterministic plan or the database. A phone number appears only when a real person typed it
at sign-in (a transporter who accepted the load); it is labelled as not verified. Listed stores and fleets keep their verification code,
so the UI can mark them as sample data."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import orchestrator
from app.models import TransportJob, User
from app.repositories import farmers, sessions as SS
from app.services import crops as CR
from app.services import llm, ops

CHAT_KEY = "chat:{}"


def save_chat(db: Session, sid: str, history: list[dict]) -> None:
    """Keep the last turns of the conversation so the dashboard can show them after a reload or restart."""
    try:
        SS.save(db, CHAT_KEY.format(sid), {"turns": history[-30:]}, confirmed=True)
    except Exception:
        db.rollback()  # the chat log is a convenience; never break a reply over it


def load_chat(db: Session, sid: str) -> list[dict]:
    return (SS.load(db, CHAT_KEY.format(sid)) or {}).get("turns", [])


def _profile(farmer: dict, crop: str, lang: str) -> dict:
    lot = farmer["lots"][crop]
    return {"crop": crop, "qty_kg": lot["qty_kg"], "original_qty": lot["original_qty"], "original_unit": lot["original_unit"],
            "location": farmer["location"], "ready": farmer.get("ready"), "can_store": farmer.get("can_store"), "variety": None, "grade": None,
            "harvest_date": None, "sell_pref": None, "lang": lang}


def _forecast(plan: dict, mandi: str | None) -> dict | None:
    fc = plan.get("forecasts") or {}
    f = fc.get(mandi) if mandi else None
    if not f:
        f = next((v for v in fc.values() if isinstance(v, dict) and v.get("status") == "ok"), None)
    if not f or f.get("status") != "ok":
        return None
    pts = [{"days": h["horizon_days"], "date": h["target_date"], "predicted": h["predicted"], "lo": h["lo"], "hi": h["hi"], "confidence": h.get("confidence")}
           for h in f.get("horizons", []) if h.get("status") == "ok"]
    if not pts:
        return None
    last = pts[-1]["predicted"]
    return {"mandi": f.get("mandi"), "current": f.get("current"), "points": pts,
            "change_pct": round((last - f["current"]) / f["current"] * 100, 1) if f.get("current") else None,
            "note": "Forecast from past prices, checked against simple baselines. Not a guarantee."}


def _crop_card(plan: dict, crop: str, farmer: dict) -> dict:
    rec = plan.get("recommendation") or {}
    best = rec.get("best") or {}
    dec = rec.get("decision") or (plan.get("sell_vs_hold") or {}).get("decision") or {}
    sells = [o for o in plan.get("options") or [] if o.get("type") != "hold"][:4]
    store = (plan.get("storage") or [None])[0]
    trans = (plan.get("transport") or [None])[0]
    lot = farmer["lots"][crop]
    return {
        "crop": crop, "label": CR.name(crop, plan["profile"].get("lang") or "en"), "qty_kg": lot["qty_kg"],
        "original_qty": lot["original_qty"], "original_unit": lot["original_unit"],
        "best": {k: best.get(k) for k in ("label", "destination", "net", "gross_revenue", "total_deductions", "price", "distance_km", "type", "hold_days",
                                          "verification", "deductions")} if best else None,
        "no_best_reason": None if best else (rec.get("reason") or "No reliable option right now."),
        "decision": {k: dec.get(k) for k in ("action", "reason", "factors", "reconsider_on", "expected_incremental")} if dec else None,
        "confidence": rec.get("confidence"),
        "forecast": _forecast(plan, (best.get("destination") or "").split(", ")[0] if best else None),
        "options": [{k: o.get(k) for k in ("label", "destination", "net", "price", "distance_km", "verification")} for o in sells],
        "storage_suggestion": {k: store.get(k) for k in ("id", "name", "type", "distance_km", "rate_qtl_day", "est_cost_7d", "availability", "verification",
                                                        "cost_label")} if store else None,
        "transport": {"destination": trans.get("destination"), "distance_km": trans.get("distance_km"), "est_hours": trans.get("est_hours"),
                      "options": [{k: o.get(k) for k in ("transporter", "vehicle", "total", "per_qtl", "verification", "quote_status", "phone")}
                                  for o in trans.get("options", [])][:3]} if trans else None,
    }


def _contact(db: Session, order: dict) -> dict | None:
    """The transporter's own sign-in phone, only after they accepted this load. Never invented."""
    j = order.get("transport")
    if not j or j["status"] not in ("accepted", "picked_up", "delivered"):
        return None
    row = db.get(TransportJob, j["id"])
    u = db.get(User, row.transporter_id) if row and row.transporter_id else None
    if not u:
        return None
    return {"name": u.display_name or j.get("transporter"), "phone": u.phone, "note": "Phone the transporter gave at sign-in. Not verified."}


def build(db: Session, device: str, lang: str = "en", live_state: dict | None = None) -> dict:
    """live_state: the agent's in-memory state for this device (current plan and the farmer's own cost settings), if it has one."""
    L = lang if lang in ("en", "hi", "mr") else "en"
    farmer = (live_state or {}).get("farmer") or farmers.load(db, device)
    ov = ops.farmer_overview(db, device)
    orders = [{**o, "contact": _contact(db, o)} for o in ov["orders"]]
    out = {"device": device, "lang": L, "ai": llm.provider(), "farmer": None, "crops": [], "orders": orders, "storage": ov["storage"],
           "alerts": ops.notifications(db, [f"device:{device}"], 20), "chat": load_chat(db, device), "data_mode": None, "labels": None,
           "totals": {"expected_net": 0, "qty_kg": 0, "open_tickets": sum(o["status"] not in ("sale_confirmed", "cancelled") for o in orders),
                      "sold_net": sum((o["payload"].get("final") or {}).get("net_earnings") or 0 for o in orders)}}
    if not farmer:
        return out
    out["farmer"] = {"location": farmer["location"], "ready": farmer.get("ready"), "can_store": farmer.get("can_store"),
                     "crops": [{"crop": c, "label": CR.name(c, L), "qty": q["original_qty"], "unit": q["original_unit"]} for c, q in farmer["lots"].items()]}
    override = (live_state or {}).get("override") or None
    for crop in farmer["lots"]:
        plan = orchestrator.run(_profile(farmer, crop, L), override)
        card = _crop_card(plan, crop, farmer)
        out["crops"].append(card)
        out["data_mode"], out["labels"] = plan.get("data_mode"), plan.get("labels")
        out["totals"]["qty_kg"] += farmer["lots"][crop]["qty_kg"]
        out["totals"]["expected_net"] += (card["best"] or {}).get("net") or 0
    active = (live_state or {}).get("active")
    if active:
        out["crops"].sort(key=lambda c: c["crop"] != active)
    return out
