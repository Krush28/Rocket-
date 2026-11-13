"""End-to-end operations: sale orders, transport jobs (booking token), warehouses, storage bookings, notifications.
Warehouses are DEMO records until real operators register (verification="demo"); nothing is claimed as confirmed unless the
counterpart acts in their portal."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class _TS:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SaleOrder(_TS, Base):
    __tablename__ = "sale_orders"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # KX-XXXXXXXX
    device: Mapped[str] = mapped_column(String(100), index=True)  # farmer's device/session id
    crop: Mapped[str] = mapped_column(String(160))
    qty_kg: Mapped[float] = mapped_column(Float)
    destination: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default="created")
    payload: Mapped[dict] = mapped_column(JSON)  # {option, profile, final, pickup}
    log: Mapped[list] = mapped_column(JSON, default=list)


class TransportJob(_TS, Base):
    __tablename__ = "transport_jobs"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # TR-XXXXXX: the token the farmer and driver share
    order_id: Mapped[str] = mapped_column(ForeignKey("sale_orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open")  # open -> accepted -> picked_up -> delivered | cancelled
    pickup: Mapped[dict] = mapped_column(JSON)
    drop: Mapped[dict] = mapped_column(JSON)
    crop: Mapped[str] = mapped_column(String(160))
    qty_kg: Mapped[float] = mapped_column(Float)
    vehicle: Mapped[str | None] = mapped_column(String(40))
    distance_km: Mapped[float | None] = mapped_column(Float)
    est_fare: Mapped[float | None] = mapped_column(Float)
    transporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    transporter_name: Mapped[str | None] = mapped_column(String(120))
    log: Mapped[list] = mapped_column(JSON, default=list)


class Warehouse(_TS, Base):
    __tablename__ = "warehouses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # cold | ventilated | godown
    temp: Mapped[str] = mapped_column(String(30))
    district: Mapped[str] = mapped_column(String(120), default="")
    state: Mapped[str] = mapped_column(String(80), default="", index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    capacity_qtl: Mapped[float] = mapped_column(Float)
    free_qtl: Mapped[float] = mapped_column(Float)
    rate_qtl_day: Mapped[float] = mapped_column(Float)
    min_days: Mapped[int] = mapped_column(Integer, default=3)
    handling_qtl: Mapped[float] = mapped_column(Float, default=10)
    categories: Mapped[list] = mapped_column(JSON)  # crop categories it can keep (services/crops.py)
    verification: Mapped[str] = mapped_column(String(20), default="demo")


class StorageBooking(_TS, Base):
    __tablename__ = "storage_bookings"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # ST-XXXXXX
    device: Mapped[str] = mapped_column(String(100), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    crop: Mapped[str] = mapped_column(String(160))
    qty_kg: Mapped[float] = mapped_column(Float)
    days: Mapped[int] = mapped_column(Integer)
    est_cost: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="requested")  # requested -> confirmed -> released | rejected | cancelled
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    log: Mapped[list] = mapped_column(JSON, default=list)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    audience: Mapped[str] = mapped_column(String(140), index=True)  # device:<id> | role:<role> | user:<id>
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(600), default="")
    link: Mapped[str | None] = mapped_column(String(200))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
