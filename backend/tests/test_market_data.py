from app.agents import orchestrator
from app.models import Mandi
from app.repositories import market_data as MD
from app.services.adapters import agmarknet_datagov as adapters


def _row(market, district, state, crop, modal, d="13/11/2026"):
    return adapters.parse_record({"market": market, "district": district, "state": state, "commodity": crop, "variety": "Local",
                                  "grade": "FAQ", "arrival_date": d, "min_price": modal - 200, "max_price": modal + 200, "modal_price": modal})


def _seed(db, rows, coords):
    adapters.upsert(rows)
    for m in db.query(Mandi).all():
        if m.name in coords:
            m.lat, m.lon, m.geo_status = *coords[m.name], "approximate"
    db.commit()


def _profile(crop, lat, lon):
    return {"crop": crop, "qty_kg": 1000, "original_qty": 10, "original_unit": "quintal", "location": {"name": "Ponda", "lat": lat, "lon": lon},
            "ready": True, "can_store": False, "lang": "en"}


def test_live_mode_excludes_ungeocoded_and_never_demo(db):
    _seed(db, [_row("Mapusa APMC", "North Goa", "Goa", "Tomato", 1400), _row("Margao APMC", "South Goa", "Goa", "Tomato", 1500)],
          {"Mapusa APMC": (15.59, 73.81)})
    ms = MD.mandis_with_prices("tomato")
    assert [m["key"] for m in ms] == ["Mapusa APMC, North Goa, Goa"]
    assert MD.series("tomato", "Pune APMC").empty  # a demo mandi name returns nothing in live mode
    assert MD.series("tomato", ms[0]["key"])["modal"].iloc[0] == 1400


def test_orchestrator_live_ranks_real_mandi(db):
    _seed(db, [_row("Mapusa APMC", "North Goa", "Goa", "Tomato", 1400)], {"Mapusa APMC": (15.59, 73.81)})
    p = orchestrator.run(_profile("tomato", 15.40, 74.02))
    assert p["data_mode"] == "LIVE"
    assert [m["name"] for m in p["mandis"]] == ["Mapusa APMC, North Goa, Goa"]
    assert p["prices"]["Mapusa APMC, North Goa, Goa"]["meta"]["verification"] == "official"
    assert any(o["type"] == "mandi_now" for o in p["options"])
    assert p["retail"] == []  # no real retail source: nothing invented
    assert not any(o["type"] == "shared_transport" for o in p["options"])  # simulated pool never ranked beside real prices


def test_any_crop_uses_category_shelf_life_for_hold(db):
    _seed(db, [_row("Mapusa APMC", "North Goa", "Goa", "Brinjal", 1800)], {"Mapusa APMC": (15.59, 73.81)})
    p = orchestrator.run({**_profile("brinjal", 15.40, 74.02), "can_store": True})
    sh = p["sell_vs_hold"]
    assert sh["holds"] == [] and sh["sell_now"]["net"] > 0
    assert any("shelf life is about 5 days" in s["why"] for s in sh["skipped"])  # brinjal: soft vegetable, 15/30-day holds ruled out
    assert p["recommendation"]["decision"]["action"] == "SELL NOW"


def test_no_mandi_in_radius_insufficient(db):
    _seed(db, [_row("Mapusa APMC", "North Goa", "Goa", "Tomato", 1400)], {"Mapusa APMC": (15.59, 73.81)})
    p = orchestrator.run(_profile("tomato", 28.6, 77.2))  # Delhi, ~1,500 km away
    failed = [t for t in p["trace"] if t["status"] == "failed"]
    assert failed and failed[0]["agent"] == "Mandi Discovery Agent" and "450 km" in failed[0]["error"]
    assert p["options"] == [] and p["recommendation"] is None


def test_crop_catalogue_includes_db_commodities(db):
    _seed(db, [_row("Mapusa APMC", "North Goa", "Goa", "Paddy(Common)", 2300)], {})
    cat = MD.crop_catalogue()
    assert "paddy" in cat["paddy(common)"] and "onion" in cat
