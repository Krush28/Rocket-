from fastapi import APIRouter, Header, HTTPException

from app.api.routes.admin import _auth
from app.schemas.chat import EventIn, OrderIn
from app.services import orders

router = APIRouter(tags=["orders"])


@router.post("/orders")
def create_order(b: OrderIn):
    return orders.create(b.option, b.profile)


@router.get("/orders")
def list_orders(x_admin_token: str | None = Header(default=None)):
    """Contains farmers' locations: admin only until Phase 8 adds per-user access."""
    _auth(x_admin_token)
    return orders.list_all()


@router.post("/orders/{oid}/event")
def order_event(oid: str, b: EventIn, x_admin_token: str | None = Header(default=None)):
    """Status changes (transport accepted, storage confirmed, sale confirmed) are operator actions: admin only for now."""
    _auth(x_admin_token)
    try:
        return orders.event(oid, b.event, b.data)
    except KeyError:
        raise HTTPException(404, "order not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
