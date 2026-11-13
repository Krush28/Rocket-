"""Rocket v2 features: data-error guard, transit spoilage risk, explainable confidence (ported from Krush28/Rocket- tests)."""
from datetime import date

from app.agents import orchestrator
from app.models import Mandi
from app.repositories import market_data as MD
from app.services import spoilage
from app.services.adapters import agmarknet_datagov as adapters

TODAY = date.today().strftime("%d/%m/%Y")


def _rows(state, crop, prices, district="x"):
    return [adapters.parse_record({"market": m, "state": state, "district": district, "commodity": crop, "variety": "v", "grade": "g",
                                   "arrival_date": TODAY, "min_price": p - 100, "max_price": p + 100, "modal_price": p}) for m, p in prices]


def test_spoilage_tiers_and_cold_chain():
    near, far = spoilage.assess("tomato", 20), spoilage.assess("tomato", 900)
    assert near["level"] in ("SAFE", "MODERATE") and far["level"] in ("HIGH", "CRITICAL")
    assert spoilage.assess("tomato", 900, refrigerated=True)["probability"] < far["probability"]
    assert spoilage.assess("tomato", 100, temp_c=38)["probability"] > spoilage.assess("tomato", 100, temp_c=15)["probability"]
    assert spoilage.assess("onion", 900)["probability"] < far["probability"]
    assert spoilage.assess("tomato", 10, age_days=30)["probability"] == 1.0
    assert spoilage.assess("brinjal", 100) is None  # unknown shelf life: no flag rather than a guess


def test_price_outlier_guard_excludes_data_errors():
    adapters.upsert(_rows("Maharashtra", "Tomato", [(f"M{i}", 2500) for i in range(6)]))
    assert MD.crop_median("tomato") == 2500
    assert MD.price_outlier("tomato", 200) and MD.price_outlier("tomato", 9000)
    assert MD.price_outlier("tomato", 2600) is None


def test_data_error_excluded_with_reason_not_ranked(db):
    adapters.upsert(_rows("Karnataka", "Tomato", [(f"M{i}", 2500) for i in range(6)]))
    adapters.upsert(_rows("Karnataka", "Tomato", [("Belgaum APMC", 200)], district="Belagavi"))
    for m in db.query(Mandi).all():
        m.lat, m.lon, m.geo_status = (15.85, 74.50, "approximate") if m.name == "Belgaum APMC" else (25.0, 80.0, "approximate")
    db.commit()
    r = orchestrator.run({"crop": "tomato", "qty_kg": 1000, "original_qty": 1000, "original_unit": "kg",
                          "location": {"name": "Ponda", "lat": 15.40, "lon": 74.02}, "ready": True, "can_store": False, "lang": "en"})["recommendation"]
    assert r["status"] == "insufficient_information" and any("Belgaum" in e["mandi"] and "data error" in e["reason"] for e in r["excluded"])


def test_confidence_and_factors_explain_themselves():
    p = orchestrator.run({"crop": "onion", "qty_kg": 5000, "original_qty": 50, "original_unit": "quintal",
                          "location": {"name": "Niphad", "lat": 20.08, "lon": 74.11}, "ready": True, "can_store": False, "lang": "en"})
    c = p["recommendation"]["confidence"]
    assert 0.05 <= c["score"] <= 0.95 and c["label"] in ("low", "medium", "high") and (c["contributors"] or c["detractors"])
    assert p["recommendation"]["decision"]["factors"]
    assert all(o["spoilage"] for o in p["options"] if o["type"] == "mandi_now")
