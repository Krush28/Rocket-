from fastapi import APIRouter, HTTPException

from app.schemas.chat import EventIn, OrderIn
from app.services import orders

router = APIRouter(tags=["orders"])


@router.post("/orders")
def create_order(b: OrderIn):
    return orders.create(b.option, b.profile)


@router.get("/orders")
def list_orders():
    return orders.list_all()


@router.post("/orders/{oid}/event")
def order_event(oid: str, b: EventIn):
    try:
        return orders.event(oid, b.event, b.data)
    except KeyError:
        raise HTTPException(404, "order not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
