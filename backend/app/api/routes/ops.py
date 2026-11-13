"""Portals API: login (phone + role), farmer journey, transporter loads (booking tokens), warehouse bookings, notifications,
FPO head dashboard, admin overview. Role tokens come from POST /api/login (header X-User-Token). Farmers are identified by their
device id (X-Device), the same id the voice agent uses."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import SaleOrder, StorageBooking, Warehouse
from app.services import ops

router = APIRouter(tags=["portals"])


class LoginIn(BaseModel):
    phone: str = Field(min_length=6, max_length=15, pattern=r"^\+?\d{6,15}$")
    role: str = Field(pattern="^(farmer|fpo|transporter|warehouse|admin)$")
    name: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=80)


class SaleIn(BaseModel):
    actual_price: float = Field(gt=0, le=1_000_000)
    actual_qty_kg: float | None = Field(default=None, gt=0, le=10_000_000)


def user(x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    u = ops.by_token(db, x_user_token)
    if not u:
        raise HTTPException(401, "login required")
    return u


def need(u, *roles):
    if u.role.value not in roles and u.role.value != "admin":
        raise HTTPException(403, f"needs role: {', '.join(roles)}")


def _err(e: Exception):
    if isinstance(e, KeyError):
        raise HTTPException(404, "not found")
    if isinstance(e, PermissionError):
        raise HTTPException(403, str(e))
    raise HTTPException(409, str(e))


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    return ops.login(db, body.phone, body.role, body.name, body.state)


@router.get("/me")
def me(u=Depends(user)):
    return ops.user_dict(u)


# ---------------------------------------------------------------- farmer (device)
@router.get("/farmer/{device}")
def farmer(device: str, db: Session = Depends(get_db)):
    return ops.farmer_overview(db, device[:100])


@router.post("/sale/{oid}/confirm")
def confirm_sale(oid: str, body: SaleIn, x_device: str | None = Header(default=None), db: Session = Depends(get_db)):
    o = db.get(SaleOrder, oid)
    if not o or o.device != x_device:
        raise HTTPException(404, "order not found for this device")
    try:
        return ops.order_event(db, oid, "confirm_sale", {"actual_price": body.actual_price, "actual_qty_kg": body.actual_qty_kg})
    except (KeyError, ValueError) as e:
        _err(e)


@router.post("/sale/{oid}/cancel")
def cancel_sale(oid: str, x_device: str | None = Header(default=None), db: Session = Depends(get_db)):
    o = db.get(SaleOrder, oid)
    if not o or o.device != x_device:
        raise HTTPException(404, "order not found for this device")
    try:
        return ops.order_event(db, oid, "cancel")
    except (KeyError, ValueError) as e:
        _err(e)


# ---------------------------------------------------------------- transporter
@router.get("/transport/jobs")
def jobs(scope: str = "open", u=Depends(user), db: Session = Depends(get_db)):
    need(u, "transporter")
    return ops.jobs_for(db, u, "open" if scope == "open" else "mine")


@router.post("/transport/jobs/{jid}/{action}")
def job_action(jid: str, action: str, u=Depends(user), db: Session = Depends(get_db)):
    need(u, "transporter")
    if action not in ("accept", "pickup", "deliver", "release"):
        raise HTTPException(400, "unknown action")
    try:
        return ops.job_action(db, jid, u, action)
    except (KeyError, ValueError, PermissionError) as e:
        _err(e)


# ---------------------------------------------------------------- warehouses / storage
@router.get("/warehouses")
def warehouses(lat: float, lon: float, crop: str | None = None, km: float = 150, db: Session = Depends(get_db)):
    return ops.warehouses_near(db, lat, lon, crop, max_km=min(km, 400), limit=20)


@router.get("/storage/bookings")
def bookings(u=Depends(user), db: Session = Depends(get_db)):
    need(u, "warehouse")
    q = db.query(StorageBooking).join(Warehouse, Warehouse.id == StorageBooking.warehouse_id)
    if u.role.value != "admin":
        q = q.filter((Warehouse.operator_id == u.id) | (Warehouse.state == (u.state or "-")))
    return [ops.booking_dict(db, b) for b in q.order_by(StorageBooking.created_at.desc()).limit(100)]


@router.get("/storage/mine")
def my_warehouses(u=Depends(user), db: Session = Depends(get_db)):
    need(u, "warehouse")
    return [ops.wh_dict(w) for w in db.query(Warehouse).filter(Warehouse.operator_id == u.id).limit(50)]


@router.post("/storage/bookings/{bid}/{action}")
def booking_action(bid: str, action: str, x_user_token: str | None = Header(default=None), x_device: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    b = db.get(StorageBooking, bid)
    if not b:
        raise HTTPException(404, "not found")
    u = ops.by_token(db, x_user_token)
    if action in ("confirm", "reject"):
        if not u or u.role.value not in ("warehouse", "admin"):
            raise HTTPException(403, "operator login required")
        actor = u.display_name or u.phone
    elif action in ("release", "cancel"):
        if b.device != x_device and not (u and u.role.value in ("warehouse", "admin")):
            raise HTTPException(403, "not your booking")
        actor = "farmer" if b.device == x_device else (u.display_name or u.phone)
    else:
        raise HTTPException(400, "unknown action")
    try:
        return ops.booking_action(db, bid, action, actor)
    except (KeyError, ValueError) as e:
        _err(e)


# ---------------------------------------------------------------- notifications + dashboards
def _aud(db, token, device):
    aud = [f"device:{device}"] if device else []
    u = ops.by_token(db, token)
    if u:
        aud += [f"user:{u.id}", f"role:{u.role.value}"]
    return aud


@router.get("/notifications")
def notifications(device: str | None = None, x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    aud = _aud(db, x_user_token, device)
    return ops.notifications(db, aud) if aud else []


@router.post("/notifications/read")
def notifications_read(device: str | None = None, x_user_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    aud = _aud(db, x_user_token, device)
    if aud:
        ops.mark_read(db, aud)
    return {"ok": True}


@router.get("/fpo/summary")
def fpo(u=Depends(user), db: Session = Depends(get_db)):
    need(u, "fpo")
    return ops.fpo_summary(db)


@router.get("/admin/overview")
def overview(u=Depends(user), db: Session = Depends(get_db)):
    need(u, "admin")
    from app.services.adapters import mandi_api
    return {**ops.admin_overview(db), "price_job": mandi_api.status()}


@router.get("/schemes")
def schemes(state: str | None = None, lang: str = "en", category: str | None = None, q: str | None = None):
    """Government schemes for a state (central + that state's), in en / hi / mr, each with its official portal.
    Optional filters: category (income|insurance|market|storage|farming) and q (a scheme id or name)."""
    from app.services import schemes as SC
    return SC.for_state(state, lang, category or None, q or None)
