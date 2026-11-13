"""Commodity catalogue, mandis, wholesale prices and their data provenance."""
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.core import Timestamps


class DataSource(Timestamps, Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(40))  # government_api | csv_export | demo | operator
    url: Mapped[str | None] = mapped_column(String(400))
    licence_note: Mapped[str | None] = mapped_column(Text)


class Provenance:
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")  # official|verified|unverified|estimate|demo


class Commodity(Timestamps, Base):
    __tablename__ = "commodities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)


class CropVariety(Timestamps, Base):
    __tablename__ = "crop_varieties"
    __table_args__ = (UniqueConstraint("commodity_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    commodity_id: Mapped[int] = mapped_column(ForeignKey("commodities.id"))
    name: Mapped[str] = mapped_column(String(120))


class Mandi(Timestamps, Base):
    __tablename__ = "mandis"
    __table_args__ = (UniqueConstraint("name", "district", "state"), Index("ix_mandis_state_district", "state", "district"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    district: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    geo_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approximate | not_found


class MandiPrice(Timestamps, Provenance, Base):
    __tablename__ = "mandi_prices"
    __table_args__ = (UniqueConstraint("mandi_id", "commodity_id", "variety", "grade", "price_date", name="uq_mandi_price"),
                      Index("ix_mandi_prices_commodity_date", "commodity_id", "price_date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    mandi_id: Mapped[int] = mapped_column(ForeignKey("mandis.id"))
    commodity_id: Mapped[int] = mapped_column(ForeignKey("commodities.id"))
    variety: Mapped[str] = mapped_column(String(120), default="")
    grade: Mapped[str] = mapped_column(String(40), default="")
    price_date: Mapped[date] = mapped_column(Date)
    min_price: Mapped[float | None] = mapped_column(Float)
    max_price: Mapped[float | None] = mapped_column(Float)
    modal_price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="Rs/quintal")


class Place(Base):
    """Offline India gazetteer (GeoNames, CC-BY 4.0): one row per searchable key (English, ASCII, Devanagari name or pincode)."""
    __tablename__ = "places"
    __table_args__ = (Index("ix_places_key", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(160))        # lowercased search key
    name: Mapped[str] = mapped_column(String(160))       # English name
    name_dev: Mapped[str | None] = mapped_column(String(160))  # Devanagari name when GeoNames has one
    admin1: Mapped[str] = mapped_column(String(80), default="")  # state
    admin2: Mapped[str] = mapped_column(String(120), default="")  # district
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(default=0)
    kind: Mapped[str] = mapped_column(String(8))  # P town/village | A state/district | PIN post office


class NameTranslation(Base):
    """Devanagari spelling of a mandi / district / state name not in the gazetteer (local-LLM transliteration, cached)."""
    __tablename__ = "name_translations"
    src: Mapped[str] = mapped_column(String(200), primary_key=True)  # lowercased English name
    dev: Mapped[str] = mapped_column(String(200))


class StatePriceHistory(Base):
    """State-average daily price per crop from the Mandi API (`/prices/history` without market). Shapes the hybrid history."""
    __tablename__ = "state_price_history"
    __table_args__ = (UniqueConstraint("state", "commodity_key", "price_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[str] = mapped_column(String(80))
    commodity_key: Mapped[str] = mapped_column(String(160))
    price_date: Mapped[date] = mapped_column(Date)
    avg_modal: Mapped[float] = mapped_column(Float)
    avg_min: Mapped[float | None] = mapped_column(Float)
    avg_max: Mapped[float | None] = mapped_column(Float)
    data_points: Mapped[int] = mapped_column(default=0)


class ForecastCache(Base):
    """Full backtested forecast (all models) per crop x mandi x last price date. Computed in the background; plans read it instantly."""
    __tablename__ = "forecast_cache"
    __table_args__ = (UniqueConstraint("crop", "mandi", "last_date", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(160))
    mandi: Mapped[str] = mapped_column(String(300))
    last_date: Mapped[date] = mapped_column(Date)
    version: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
