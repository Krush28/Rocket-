"""Execution: create order -> book transport -> book storage (if needed) -> track delivery -> confirm sale.
SQLite-backed state machine. Bookings are REQUESTS; nothing is 'confirmed' by a third party unless an operator/admin event says so."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "krishimitra.db"
FLOW = {  # status -> allowed events -> next status
    "created": {"request_transport": "transport_requested", "cancel": "cancelled"},
    "transport_requested": {"request_storage": "storage_enquiry_sent", "transporter_accepts": "transport_accepted", "cancel": "cancelled"},
    "storage_enquiry_sent": {"operator_confirms_storage": "storage_confirmed", "transporter_accepts": "transport_accepted", "cancel": "cancelled"},
    "storage_confirmed": {"transporter_accepts": "transport_accepted", "cancel": "cancelled"},
    "transport_accepted": {"pickup": "in_transit", "cancel": "cancelled"},
    "in_transit": {"deliver": "delivered"},
    "delivered": {"confirm_sale": "sale_confirmed"},
    "sale_confirmed": {}, "cancelled": {},
}


def _c():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("create table if not exists orders(id text primary key, created text, status text, payload text, log text)")
    return c


def _row(r):
    return {"id": r["id"], "created": r["created"], "status": r["status"], "payload": json.loads(r["payload"]), "log": json.loads(r["log"]),
            "next_events": list(FLOW[r["status"]])}


def create(option: dict, profile: dict) -> dict:
    oid = "KX-" + uuid.uuid4().hex[:8].upper()
    now = datetime.now(timezone.utc).isoformat()
    log = [{"at": now, "event": "create_order", "status": "created", "note": "Order created from recommended option (expected, not final)."}]
    with _c() as c:
        c.execute("insert into orders values(?,?,?,?,?)", (oid, now, "created", json.dumps({"option": option, "profile": profile, "final": None}), json.dumps(log)))
    return get(oid)


def get(oid: str):
    with _c() as c:
        r = c.execute("select * from orders where id=?", (oid,)).fetchone()
    return _row(r) if r else None


def list_all():
    with _c() as c:
        return [_row(r) for r in c.execute("select * from orders order by created desc limit 50")]


def event(oid: str, ev: str, data: dict | None = None) -> dict:
    o = get(oid)
    if not o:
        raise KeyError(oid)
    nxt = FLOW[o["status"]].get(ev)
    if not nxt:
        raise ValueError(f"event '{ev}' not allowed from '{o['status']}'")
    payload = o["payload"]
    note = {"request_transport": "Transport REQUEST sent (estimate, not a confirmed quote).",
            "request_storage": "Storage ENQUIRY sent. Availability is not confirmed until the operator confirms.",
            "operator_confirms_storage": "Operator confirmed storage (demo operator action).",
            "transporter_accepts": "Transporter accepted (demo transporter action).", "pickup": "Produce picked up.", "deliver": "Delivered to destination."}.get(ev, ev)
    if ev == "confirm_sale":
        d = data or {}
        if float(d.get("actual_price", 0)) <= 0 or float(d.get("actual_qty_kg", 0)) <= 0:
            raise ValueError("actual_price (Rs/qtl) and actual_qty_kg must be > 0")
        costs = float(d.get("actual_costs", 0))
        revenue = float(d["actual_price"]) * float(d["actual_qty_kg"]) / 100
        payload["final"] = {"actual_price": float(d["actual_price"]), "actual_qty_kg": float(d["actual_qty_kg"]), "revenue": round(revenue),
                            "costs": costs, "net_earnings": round(revenue - costs), "expected_net": payload["option"].get("net")}
        note = "Sale confirmed with farmer-entered actuals."
    log = o["log"] + [{"at": datetime.now(timezone.utc).isoformat(), "event": ev, "status": nxt, "note": note}]
    with _c() as c:
        c.execute("update orders set status=?, payload=?, log=? where id=?", (nxt, json.dumps(payload), json.dumps(log), oid))
    return get(oid)
