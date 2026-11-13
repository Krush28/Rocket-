"""Farmer memory between visits, keyed by a random device id the browser keeps (no accounts, no Aadhaar).
Stored in farmer_profiles (session_id = device id) + farmer_inventory rows with status "available".
farmer = {"location": {name, lat, lon}, "ready", "can_store", "lang", "lots": {crop: {"qty_kg", "original_qty", "original_unit"}}}"""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Commodity, FarmerInventory, FarmerProfile


def load(db: Session, device: str) -> dict | None:
    fp = db.scalar(select(FarmerProfile).where(FarmerProfile.session_id == device))
    if not fp:
        return None
    rows = db.scalars(select(FarmerInventory).where(FarmerInventory.farmer_profile_id == fp.id, FarmerInventory.status == "available")
                      .order_by(FarmerInventory.id)).all()
    if not rows:
        return None
    return {"location": {"name": fp.location_name, "lat": fp.lat, "lon": fp.lon, "status": "approximate"}, "ready": rows[0].ready,
            "can_store": fp.can_store, "lang": fp.preferred_language,
            "lots": {r.crop_key: {"qty_kg": r.qty_kg, "original_qty": r.original_qty, "original_unit": r.original_unit} for r in rows}}


def save(db: Session, device: str, farmer: dict) -> None:
    """Upsert the profile and replace the available lots (one row per crop)."""
    loc = farmer["location"]
    fp = db.scalar(select(FarmerProfile).where(FarmerProfile.session_id == device))
    if not fp:
        fp = FarmerProfile(session_id=device, location_name=loc["name"])
        db.add(fp)
    fp.location_name, fp.lat, fp.lon = loc["name"], loc.get("lat"), loc.get("lon")
    fp.can_store, fp.preferred_language = bool(farmer.get("can_store")), farmer.get("lang") or "en"
    db.flush()
    db.execute(delete(FarmerInventory).where(FarmerInventory.farmer_profile_id == fp.id, FarmerInventory.status == "available"))
    for crop, q in farmer["lots"].items():
        db.add(FarmerInventory(farmer_profile_id=fp.id, crop_key=crop, commodity_id=db.scalar(select(Commodity.id).where(Commodity.key == crop)),
                               qty_kg=q["qty_kg"], original_qty=q["original_qty"], original_unit=q["original_unit"], ready=bool(farmer.get("ready", True))))
    db.commit()


def clear(db: Session, device: str) -> None:
    """'Start over' forgets the farmer's available lots (orders and history rows are kept)."""
    fp = db.scalar(select(FarmerProfile).where(FarmerProfile.session_id == device))
    if fp:
        db.execute(delete(FarmerInventory).where(FarmerInventory.farmer_profile_id == fp.id, FarmerInventory.status == "available"))
        db.commit()
