"""Regression tests for the Phase 1 final-review findings."""
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents import orchestrator
from app.conversation import profile_agent as P
from app.core import ratelimit
from app.main import app
from app.models import Mandi
from app.services import geocoding as G
from app.services.adapters import agmarknet_datagov as adapters

client = TestClient(app)


@pytest.fixture(autouse=True)
def _iso():
    P.SESSIONS.clear()
    ratelimit.hits.clear()


def test_long_place_text_is_not_geocoded_or_cached(db):
    calls = []
    c = httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(1) or httpx.Response(200, json=[])))
    assert G.geocode(db, "near " + "x" * 400, client=c) is None
    assert calls == []  # never sent, so never written into the 300-char cache column


def test_turn_after_confirmation_does_not_crash(db):
    for t in ["", "1000 kg tomato", "near Ponda", "yes", "no", "yes"]:
        r = P.chat("done1", t, db=db)
    assert r["done"]
    r = P.chat("done1", "yes", db=db)  # client retry after confirmation
    assert r["state"] == "confirmed" and not r["done"]


def test_orders_list_and_operator_events_need_admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "t0ken")
    assert client.get("/api/orders").status_code == 403
    o = client.post("/api/orders", json={"option": {"net": 1, "price": 1, "destination": "x"}, "profile": {"crop": "tomato"}}).json()
    assert client.post(f"/api/orders/{o['id']}/event", json={"event": "request_transport"}).status_code == 403
    assert client.get("/api/orders", headers={"X-Admin-Token": "t0ken"}).status_code == 200


def test_rate_limited_response_keeps_cors_headers(monkeypatch):
    monkeypatch.setattr(ratelimit, "READ_LIMIT", 1)
    h = {"Origin": "http://localhost:3000"}
    client.get("/api/meta", headers=h)
    r = client.get("/api/meta", headers=h)
    assert r.status_code == 429 and r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_stale_prices_explained(db):
    old = (date.today() - timedelta(days=20)).strftime("%d/%m/%Y")
    adapters.upsert([adapters.parse_record({"market": "Mapusa APMC", "district": "North Goa", "state": "Goa", "commodity": "Tomato",
                                            "arrival_date": old, "min_price": 1200, "max_price": 1600, "modal_price": 1400})])
    m = db.query(Mandi).one()
    m.lat, m.lon, m.geo_status = 15.59, 73.81, "approximate"
    db.commit()
    p = orchestrator.run({"crop": "tomato", "qty_kg": 1000, "original_qty": 1000, "original_unit": "kg",
                          "location": {"name": "Ponda", "lat": 15.40, "lon": 74.02}, "ready": True, "can_store": False, "lang": "en"})
    assert "older than 7 days" in p["recommendation"]["reason"]
