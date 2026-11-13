"""Users, farmer intake, conversation state, geocode cache, audit log."""
import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Role(str, enum.Enum):
    farmer = "farmer"
    fpo = "fpo"
    buyer = "buyer"
    transporter = "transporter"
    warehouse = "warehouse"
    admin = "admin"


class User(Timestamps, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.farmer)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")


class FarmerProfile(Timestamps, Base):
    __tablename__ = "farmer_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str | None] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    location_name: Mapped[str] = mapped_column(String(200))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    can_store: Mapped[bool] = mapped_column(Boolean, default=False)
    sell_pref: Mapped[str | None] = mapped_column(String(30))


class FarmerInventory(Timestamps, Base):
    __tablename__ = "farmer_inventory"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_profile_id: Mapped[int] = mapped_column(ForeignKey("farmer_profiles.id"), index=True)
    commodity_id: Mapped[int | None] = mapped_column(ForeignKey("commodities.id"))
    crop_key: Mapped[str] = mapped_column(String(120))
    variety: Mapped[str | None] = mapped_column(String(80))
    grade: Mapped[str | None] = mapped_column(String(30))
    qty_kg: Mapped[float] = mapped_column(Float)
    original_qty: Mapped[float] = mapped_column(Float)
    original_unit: Mapped[str] = mapped_column(String(20))
    harvest_date: Mapped[date | None] = mapped_column(Date)
    ready: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="available")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeocodeCache(Timestamps, Base):
    __tablename__ = "geocode_cache"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(300), unique=True)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    display_name: Mapped[str | None] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(20))  # approximate | not_found
    provider: Mapped[str] = mapped_column(String(40), default="nominatim")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(60))
    detail: Mapped[dict | None] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
