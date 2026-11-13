"""End-to-end operations in Postgres (replaces the SQLite demo order store).
SELL: order (created) -> request_transport: a transport job / booking token TR-XXXXXX goes to every transporter's portal ->
      a transporter ACCEPTS -> PICKUP -> DELIVER -> farmer CONFIRMS the actual sale price -> sale_confirmed (done screen).
HOLD: storage booking ST-XXXXXX (requested) -> the warehouse operator CONFIRMS or REJECTS in their portal -> farmer later RELEASES
      it and sells (the AI plans again from the warehouse).
Every status change writes a log line and a notification for the other side. Warehouses are DEMO until real operators register."""
import random
import uuid
import zlib
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FarmerInventory, Mandi, Notification, SaleOrder, StorageBooking, TransportJob, User, Warehouse
from app.models.core import Role
from app.services import crops as CR
from app.services.geo import haversine_km

ORDER_FLOW = {  # order status -> farmer events allowed
    "created": {"request_transport": "transport_requested", "cancel": "cancelled"},
    "transport_requested": {"cancel": "cancelled"},
    "transport_accepted": {"cancel": "cancelled"},
    "in_transit": {},
    "delivered": {"confirm_sale": "sale_confirmed"},
    "sale_confirmed": {}, "cancelled": {},
}
JOB_FLOW = {"open": {"accept": "accepted"}, "accepted": {"pickup": "picked_up", "release": "open"}, "picked_up": {"deliver": "delivered"}}
JOB_TO_ORDER = {"accepted": "transport_accepted", "picked_up": "in_transit", "delivered": "delivered", "open": "transport_requested"}
STORE_FLOW = {"requested": {"confirm": "confirmed", "reject": "rejected", "cancel": "cancelled"}, "confirmed": {"release": "released", "cancel": "cancelled"}}
KINDS = {  # demo warehouse types: what they keep, temperature, Rs per quintal per day
    "cold": (["soft", "gourd", "fruit", "leafy", "flower", "root"], "2-8 C", (1.8, 3.2)),
    "ventilated": (["root"], "ambient, ventilated", (0.5, 1.0)),
    "godown": (["grain", "pulse", "oilseed", "fibre", "spice"], "dry, ambient", (0.25, 0.6)),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, n: int = 6) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:n].upper()}"


def notify(db: Session, audience: str, title: str, body: str = "", link: str | None = None) -> None:
    db.add(Notification(audience=audience, title=title[:200], body=body[:600], link=link))


# ---------------------------------------------------------------- warehouses (DEMO seed, then real operators)
def seed_warehouses(db: Session) -> int:
    """One cold store + one dry godown (+ a ventilated onion/potato store in every third district) per district that has a geocoded
    mandi. Fictional (verification='demo'), deterministic per district, never claimed as confirmed capacity."""
    seen = set(db.execute(select(Warehouse.district, Warehouse.state).distinct()).all())  # idempotent: only districts without one
    n = 0
    for m in db.scalars(select(Mandi).where(Mandi.lat.isnot(None))).all():
        k = (m.district, m.state)
        if k in seen:
            continue
        seen.add(k)
        rng = random.Random(zlib.crc32(f"{m.district}|{m.state}".encode()))
        kinds = ["cold", "godown"] + (["ventilated"] if len(seen) % 3 == 0 else [])
        for kind in kinds:
            cats, temp, (lo, hi) = KINDS[kind]
            cap = rng.choice([2000, 3000, 5000, 8000, 12000])
            label = {"cold": "Cold Store", "ventilated": "Ventilated Store", "godown": "Godown"}[kind]
            db.add(Warehouse(code=f"W{zlib.crc32(f'{k}{kind}'.encode()) % 10**7:07d}", name=f"{m.district} {label}", kind=kind, temp=temp,
                             district=m.district, state=m.state, lat=m.lat + rng.uniform(-0.06, 0.06), lon=m.lon + rng.uniform(-0.06, 0.06),
                             capacity_qtl=cap, free_qtl=round(cap * rng.uniform(0.2, 0.8)), rate_qtl_day=round(rng.uniform(lo, hi), 2),
                             min_days=3 if kind == "cold" else 7, handling_qtl=10 if kind == "cold" else 6, categories=cats))
            n += 1
    db.commit()
    return n


def wh_dict(w: Warehouse, km: float | None = None, qtl: float | None = None) -> dict:
    d = {"id": w.code, "db_id": w.id, "name": w.name, "type": {"cold": "cold storage", "ventilated": "ventilated store", "godown": "dry godown"}[w.kind],
         "kind": w.kind, "temp": w.temp, "lat": w.lat, "lon": w.lon, "district": w.district, "state": w.state, "rate_qtl_day": w.rate_qtl_day,
         "min_days": w.min_days, "handling_qtl": w.handling_qtl, "declared_capacity_qtl": w.capacity_qtl, "free_qtl": w.free_qtl,
         "available_capacity_qtl": w.free_qtl if w.verification != "demo" else None,
         "availability": "UNCONFIRMED - book to send a request; the operator must confirm", "phone": None,
         "verification": "listed" if w.verification == "demo" else w.verification, "crop_suitable": True, "cost_label": "ESTIMATE"}
    if km is not None:
        d["distance_km"] = round(km, 1)
    if qtl is not None:
        d["est_cost_7d"] = round(w.rate_qtl_day * max(7, w.min_days) * qtl + w.handling_qtl * qtl)
    return d


def warehouses_near(db: Session, lat: float, lon: float, crop: str | None = None, max_km: float = 150, limit: int = 8, qtl: float | None = None) -> list[dict]:
    cat = CR.params(crop)["category"] if crop else None
    box = max_km / 100
    rows = db.scalars(select(Warehouse).where(Warehouse.lat.between(lat - box, lat + box), Warehouse.lon.between(lon - box, lon + box))).all()
    out = []
    for w in rows:
        km = haversine_km((lat, lon), (w.lat, w.lon)) * 1.3
        if km <= max_km and (cat is None or cat in w.categories):
            out.append((km, w))
    return [wh_dict(w, km, qtl) for km, w in sorted(out, key=lambda x: (x[1].rate_qtl_day * 30 + x[0] * 0.5))[:limit]]


# ---------------------------------------------------------------- sale orders + transport jobs
def order_dict(db: Session, o: SaleOrder) -> dict:
    job = db.scalar(select(TransportJob).where(TransportJob.order_id == o.id).order_by(TransportJob.created_at.desc()))
    return {"id": o.id, "created": o.created_at.isoformat() if o.created_at else None, "status": o.status, "payload": o.payload, "log": o.log,
            "next_events": list(ORDER_FLOW.get(o.status, {})), "transport": job_dict(job) if job else None}


def job_dict(j: TransportJob) -> dict:
    return {"id": j.id, "token": j.id, "order_id": j.order_id, "status": j.status, "pickup": j.pickup, "drop": j.drop, "crop": j.crop,
            "crop_label": CR.name(j.crop, "en"), "qty_kg": j.qty_kg, "vehicle": j.vehicle, "distance_km": j.distance_km, "est_fare": j.est_fare,
            "fare_label": "ESTIMATE", "transporter": j.transporter_name, "log": j.log, "next": list(JOB_FLOW.get(j.status, {})),
            "created": j.created_at.isoformat() if j.created_at else None}


def create_order(db: Session, device: str, option: dict, profile: dict, transport: dict | None = None) -> dict:
    o = SaleOrder(id=_id("KX", 8), device=device, crop=profile["crop"], qty_kg=profile["qty_kg"], destination=option.get("destination") or "",
                  status="created", payload={"option": option, "profile": profile, "final": None, "transport_quote": transport},
                  log=[{"at": _now(), "event": "create_order", "status": "created", "note": "Order created from the recommended option (expected, not final)."}])
    db.add(o)
    notify(db, "role:fpo", f"New sale order {o.id}", f"{CR.name(o.crop, 'en')} {o.qty_kg:,.0f} kg to {o.destination.split(', ')[0]}", "/fpo")
    db.commit()
    return order_dict(db, o)


def get_order(db: Session, oid: str) -> dict | None:
    o = db.get(SaleOrder, oid)
    return order_dict(db, o) if o else None


def _mandi_point(db: Session, key: str) -> dict:
    parts = key.rsplit(", ", 2)
    m = db.scalar(select(Mandi).where(Mandi.name == parts[0], Mandi.district == parts[1], Mandi.state == parts[2])) if len(parts) == 3 else None
    return {"name": key, "lat": m.lat if m else None, "lon": m.lon if m else None}


def order_event(db: Session, oid: str, ev: str, data: dict | None = None) -> dict:
    """Farmer-side events: request_transport, cancel, confirm_sale."""
    o = db.get(SaleOrder, oid)
    if not o:
        raise KeyError(oid)
    nxt = ORDER_FLOW.get(o.status, {}).get(ev)
    if not nxt:
        raise ValueError(f"'{ev}' is not possible while the order is '{o.status}'")
    note = ev
    if ev == "request_transport":
        prof, q = o.payload["profile"], (o.payload.get("transport_quote") or {})
        loc = prof["location"]
        job = TransportJob(id=_id("TR"), order_id=o.id, status="open", pickup={"name": loc["name"], "lat": loc["lat"], "lon": loc["lon"]},
                           drop=_mandi_point(db, o.destination), crop=o.crop, qty_kg=o.qty_kg, vehicle=q.get("vehicle"),
                           distance_km=q.get("distance_km") or o.payload["option"].get("distance_km"), est_fare=q.get("total") or o.payload["option"].get("transport"),
                           log=[{"at": _now(), "status": "open", "note": "Load posted to transporters (fare is an ESTIMATE, not a quote)."}])
        db.add(job)
        note = f"Transport request {job.id} sent to transporters (estimate, not a confirmed quote)."
        notify(db, "role:transporter", f"New load {job.id}", f"{CR.name(o.crop, 'en')} {o.qty_kg:,.0f} kg: {loc['name']} -> {o.destination.split(', ')[0]}"
               + (f", est. Rs {job.est_fare:,.0f}" if job.est_fare else ""), "/transporter")
    elif ev == "cancel":
        for j in db.scalars(select(TransportJob).where(TransportJob.order_id == o.id, TransportJob.status.in_(["open", "accepted"]))):
            j.status = "cancelled"
            j.log = j.log + [{"at": _now(), "status": "cancelled", "note": "Farmer cancelled the order."}]
            if j.transporter_id:
                notify(db, f"user:{j.transporter_id}", f"Load {j.id} cancelled", "The farmer cancelled this order.", "/transporter")
        note = "Order cancelled by the farmer."
    elif ev == "confirm_sale":
        d = data or {}
        price, qty = float(d.get("actual_price") or 0), float(d.get("actual_qty_kg") or o.qty_kg)
        if price <= 0 or qty <= 0:
            raise ValueError("actual_price (Rs/quintal) and quantity must be > 0")
        costs = float(d.get("actual_costs") if d.get("actual_costs") is not None else o.payload["option"].get("total_deductions") or 0)
        revenue = price * qty / 100
        o.payload = {**o.payload, "final": {"actual_price": price, "actual_qty_kg": qty, "revenue": round(revenue), "costs": round(costs),
                                            "net_earnings": round(revenue - costs), "expected_net": o.payload["option"].get("net")}}
        note = "Sale confirmed with the farmer's actual price."
        notify(db, "role:fpo", f"Sale closed {o.id}", f"Net Rs {revenue - costs:,.0f}", "/fpo")
    o.status = nxt
    o.log = o.log + [{"at": _now(), "event": ev, "status": nxt, "note": note}]
    db.commit()
    return order_dict(db, o)


def jobs_for(db: Session, user: User | None, scope: str = "open") -> list[dict]:
    q = select(TransportJob).order_by(TransportJob.created_at.desc()).limit(100)
    if scope == "open":
        q = q.where(TransportJob.status == "open")
    elif user is not None:
        q = q.where(TransportJob.transporter_id == user.id)
    return [job_dict(j) for j in db.scalars(q)]


def job_action(db: Session, jid: str, user: User, action: str) -> dict:
    j = db.get(TransportJob, jid)
    if not j:
        raise KeyError(jid)
    nxt = JOB_FLOW.get(j.status, {}).get(action)
    if not nxt:
        raise ValueError(f"'{action}' is not possible while the load is '{j.status}'")
    if j.status != "open" and j.transporter_id != user.id:
        raise PermissionError("this load belongs to another transporter")
    name = user.display_name or f"Transporter {user.phone}"
    if action == "accept":
        j.transporter_id, j.transporter_name = user.id, name
    elif action == "release":
        j.transporter_id = j.transporter_name = None
    j.status = nxt
    j.log = j.log + [{"at": _now(), "status": nxt, "note": f"{action} by {name}"}]
    o = db.get(SaleOrder, j.order_id)
    o.status = JOB_TO_ORDER[nxt]
    msg = {"accept": f"{name} accepted your load {j.id}. Truck: {j.vehicle or 'vehicle'}.", "pickup": f"Your produce was picked up ({j.id}).",
           "deliver": f"Delivered to {j.drop['name'].split(', ')[0]}. Tell the AI the price you got to close the sale.",
           "release": f"The transporter released load {j.id}; it is open again."}[action]
    o.log = o.log + [{"at": _now(), "event": f"transport_{action}", "status": o.status, "note": msg}]
    notify(db, f"device:{o.device}", {"accept": "Truck accepted", "pickup": "Picked up", "deliver": "Delivered", "release": "Truck released"}[action], msg, "/")
    db.commit()
    return job_dict(j)


# ---------------------------------------------------------------- storage bookings
def booking_dict(db: Session, b: StorageBooking) -> dict:
    w = db.get(Warehouse, b.warehouse_id)
    return {"id": b.id, "status": b.status, "crop": b.crop, "crop_label": CR.name(b.crop, "en"), "qty_kg": b.qty_kg, "days": b.days,
            "est_cost": b.est_cost, "cost_label": "ESTIMATE", "warehouse": wh_dict(w) if w else None, "log": b.log, "device": b.device,
            "next": list(STORE_FLOW.get(b.status, {})), "created": b.created_at.isoformat() if b.created_at else None}


def book_storage(db: Session, device: str, wh_code: str, crop: str, qty_kg: float, days: int = 7) -> dict:
    w = db.scalar(select(Warehouse).where(Warehouse.code == wh_code))
    if not w:
        raise KeyError(wh_code)
    qtl = qty_kg / 100
    days = max(days, w.min_days)
    b = StorageBooking(id=_id("ST"), device=device, warehouse_id=w.id, crop=crop, qty_kg=qty_kg, days=days,
                       est_cost=round(w.rate_qtl_day * days * qtl + w.handling_qtl * qtl), status="requested",
                       log=[{"at": _now(), "status": "requested", "note": "Storage request sent; the operator must confirm (estimate, not a quote)."}])
    db.add(b)
    notify(db, f"user:{w.operator_id}" if w.operator_id else "role:warehouse", f"Storage request {b.id}",
           f"{CR.name(crop, 'en')} {qty_kg:,.0f} kg for {days} days at {w.name}", "/warehouse")
    db.commit()
    return booking_dict(db, b)


def booking_action(db: Session, bid: str, action: str, actor: str) -> dict:
    b = db.get(StorageBooking, bid)
    if not b:
        raise KeyError(bid)
    nxt = STORE_FLOW.get(b.status, {}).get(action)
    if not nxt:
        raise ValueError(f"'{action}' is not possible while the booking is '{b.status}'")
    w = db.get(Warehouse, b.warehouse_id)
    if action == "confirm":
        w.free_qtl = max(0.0, w.free_qtl - b.qty_kg / 100)
    elif action in ("release", "cancel") and b.status == "confirmed":
        w.free_qtl = min(w.capacity_qtl, w.free_qtl + b.qty_kg / 100)
    b.status = nxt
    b.log = b.log + [{"at": _now(), "status": nxt, "note": f"{action} by {actor}"}]
    if action in ("confirm", "reject"):
        notify(db, f"device:{b.device}", "Storage confirmed" if action == "confirm" else "Storage not available",
               f"{w.name}: {b.id} {'confirmed' if action == 'confirm' else 'rejected'}." + (" Ask the AI when you want to sell." if action == "confirm" else ""), "/")
    else:
        notify(db, "role:warehouse", f"Booking {b.id} {nxt}", f"{CR.name(b.crop, 'en')} {b.qty_kg:,.0f} kg", "/warehouse")
    db.commit()
    return booking_dict(db, b)


# ---------------------------------------------------------------- people, notifications, dashboards
def login(db: Session, phone: str, role: str, name: str | None, state: str | None) -> dict:
    """Demo login: phone + role, no password (labelled demo). Returns a session token."""
    u = db.scalar(select(User).where(User.phone == phone))
    if not u:
        u = User(phone=phone, role=Role(role), display_name=name or None, state=state or None)
        db.add(u)
    else:
        u.role, u.display_name, u.state = Role(role), name or u.display_name, state or u.state
    u.token = uuid.uuid4().hex
    db.commit()
    if u.role == Role.warehouse and state:  # a demo operator adopts the unclaimed demo warehouses of their state
        for w in db.scalars(select(Warehouse).where(Warehouse.state == state, Warehouse.operator_id.is_(None)).limit(6)):
            w.operator_id = u.id
        db.commit()
    return {"token": u.token, "user": user_dict(u)}


def user_dict(u: User) -> dict:
    return {"id": u.id, "phone": u.phone, "name": u.display_name, "role": u.role.value, "state": u.state, "demo_login": True}


def by_token(db: Session, token: str | None) -> User | None:
    return db.scalar(select(User).where(User.token == token)) if token else None


def notifications(db: Session, audiences: list[str], limit: int = 30) -> list[dict]:
    rows = db.scalars(select(Notification).where(Notification.audience.in_(audiences)).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit))
    return [{"id": n.id, "title": n.title, "body": n.body, "link": n.link, "read": n.read, "at": n.created_at.isoformat() if n.created_at else None} for n in rows]


def mark_read(db: Session, audiences: list[str]) -> None:
    for n in db.scalars(select(Notification).where(Notification.audience.in_(audiences), Notification.read.is_(False))):
        n.read = True
    db.commit()


def farmer_overview(db: Session, device: str) -> dict:
    orders = [order_dict(db, o) for o in db.scalars(select(SaleOrder).where(SaleOrder.device == device).order_by(SaleOrder.created_at.desc()).limit(20))]
    books = [booking_dict(db, b) for b in db.scalars(select(StorageBooking).where(StorageBooking.device == device).order_by(StorageBooking.created_at.desc()).limit(20))]
    return {"orders": orders, "storage": books}


def fpo_summary(db: Session) -> dict:
    """FPO / association head: members' produce waiting to be sold (aggregated) and the pipeline of orders."""
    lots = db.execute(select(FarmerInventory.crop_key, func.count(func.distinct(FarmerInventory.farmer_profile_id)), func.sum(FarmerInventory.qty_kg))
                      .where(FarmerInventory.status == "available").group_by(FarmerInventory.crop_key)).all()
    status = dict(db.execute(select(SaleOrder.status, func.count()).group_by(SaleOrder.status)).all())
    net = db.scalars(select(SaleOrder).where(SaleOrder.status == "sale_confirmed")).all()
    return {"members_produce": [{"crop": c, "crop_label": CR.name(c, "en"), "farmers": int(n), "qty_kg": float(q or 0),
                                 "trucks_10t": round(float(q or 0) / 10000, 1)} for c, n, q in sorted(lots, key=lambda r: -(r[2] or 0))],
            "orders_by_status": status, "sales_closed": len(net),
            "net_earnings_total": round(sum((o.payload.get("final") or {}).get("net_earnings", 0) for o in net)),
            "recent_orders": [order_dict(db, o) for o in db.scalars(select(SaleOrder).order_by(SaleOrder.created_at.desc()).limit(15))]}


def admin_overview(db: Session) -> dict:
    c = lambda m: db.scalar(select(func.count()).select_from(m))  # noqa: E731
    return {"orders": c(SaleOrder), "transport_jobs": c(TransportJob), "warehouses": c(Warehouse), "storage_bookings": c(StorageBooking),
            "users": c(User), "notifications": c(Notification)}
