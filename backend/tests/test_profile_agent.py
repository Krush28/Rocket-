import pytest

from app.conversation import profile_agent as P
from app.models import Commodity, FarmerInventory, FarmerProfile
from app.services import geocoding

LUDHIANA = {"name": "Ludhiana", "lat": 30.90, "lon": 75.85, "status": "approximate"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    P.SESSIONS.clear()
    monkeypatch.setattr(geocoding, "geocode", lambda db, q, **k: LUDHIANA if "ludhiana" in q.lower() else None)


def test_geocoded_place_any_india(db):
    P.chat("a", "", db=db)
    r = P.chat("a", "500 kg onion near Ludhiana", db=db)
    assert r["slots"]["location"]["name"] == "Ludhiana" and r["slots"]["location"]["lat"] == 30.90
    assert r["awaiting"] == "ready"


def test_geocoder_down_reasks(db):
    P.chat("b", "", db=db)
    P.chat("b", "500 kg onion", db=db)
    r = P.chat("b", "xyzabc village", db=db)
    assert r["awaiting"] == "location" and r["state"] == "collecting"
    assert "district" in r["reply"]


def test_catalogue_crop_from_db(db):
    db.add(Commodity(name="Brinjal", key="brinjal"))
    db.add(Commodity(name="Rice", key="rice"))
    db.commit()
    P.chat("c", "", db=db)
    r = P.chat("c", "I have 10 quintal brinjals at a good price", db=db)
    assert r["slots"]["crop"] == "brinjal" and r["slots"]["qty"]["qty_kg"] == 1000  # 'price' must not match 'rice'


def test_session_persists_across_calls(db):
    P.chat("d", "", db=db)
    P.chat("d", "1000 kg tomato", db=db)
    P.SESSIONS.clear()  # e.g. a server restart
    r = P.chat("d", "near Ludhiana", db=db)
    assert r["slots"]["crop"] == "tomato" and r["awaiting"] == "ready"


def test_hindi_quintal(db):
    P.chat("e", "", db=db)
    r = P.chat("e", "10 क्विंटल प्याज", db=db)
    assert r["slots"]["qty"]["qty_kg"] == 1000 and r["lang"] == "hi"


def test_on_confirm_saves_profile_and_inventory(db):
    for t in ["", "1000 kg tomato", "near Ludhiana", "yes", "no"]:
        r = P.chat("f", t, db=db)
    r = P.chat("f", "yes", db=db)
    assert r["done"]
    inv_id = P.on_confirm(db, "f", r["profile"])
    inv = db.get(FarmerInventory, inv_id)
    assert (inv.qty_kg, inv.original_qty, inv.original_unit, inv.crop_key) == (1000, 1000, "kg", "tomato")
    assert db.get(FarmerProfile, inv.farmer_profile_id).location_name == "Ludhiana"
