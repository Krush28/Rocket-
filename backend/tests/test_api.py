import pytest
from fastapi.testclient import TestClient

from app.conversation import profile_agent as P
from app.core import ratelimit
from app.main import app
from app.services import geocoding

client = TestClient(app)
PONDA = {"name": "Ponda", "lat": 15.40, "lon": 74.02, "status": "approximate"}


@pytest.fixture(autouse=True)
def _iso(monkeypatch):
    P.SESSIONS.clear()
    ratelimit.hits.clear()
    monkeypatch.setattr(geocoding, "geocode", lambda db, q, **k: PONDA if "ponda" in q.lower() else None)


def _say(sid, text):
    r = client.post("/api/chat", json={"session_id": sid, "text": text})
    assert r.status_code == 200, r.text
    return r.json()


def test_chat_flow_to_confirmed_plan():
    _say("api1", "")
    for t in ["1000 kg tomato", "near Ponda", "yes", "no"]:
        r = _say("api1", t)
    assert r["state"] == "confirming" and "plan" not in r  # nothing market-related before confirmation
    r = _say("api1", "yes")
    assert r["done"] and isinstance(r["inventory_id"], int)
    assert isinstance(r["plan"]["options"], list) and r["plan"]["data_mode"] == "DEMO"


def test_plan_409_before_confirm_and_404_unknown():
    _say("api2", "")
    _say("api2", "1000 kg tomato")
    assert client.post("/api/plan", json={"session_id": "api2"}).status_code == 409
    assert client.post("/api/plan", json={"session_id": "nope"}).status_code == 404


def test_plan_after_confirm():
    for t in ["", "1000 kg tomato", "near Ponda", "yes", "no", "yes"]:
        _say("api3", t)
    r = client.post("/api/plan", json={"session_id": "api3"})
    assert r.status_code == 200 and r.json()["profile"]["qty_kg"] == 1000


def test_admin_import_needs_token_and_rejects_outside_data_raw(monkeypatch):
    assert client.post("/api/admin/import", json={"path": "x.csv"}).status_code == 403
    monkeypatch.setenv("ADMIN_TOKEN", "t0ken")
    h = {"X-Admin-Token": "t0ken"}
    assert client.post("/api/admin/import", json={"path": "../../etc/passwd"}, headers=h).status_code == 400
    assert client.post("/api/admin/import", json={"path": "x.csv"}, headers={"X-Admin-Token": "bad"}).status_code == 403


def test_rate_limit_429(monkeypatch):
    monkeypatch.setattr(ratelimit, "LIMIT", 3)
    codes = [client.get("/api/meta").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_health_reports_mode():
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["db"] is True and h["data_mode"] == "DEMO DATA" and h["last_price_date"] is None


def test_chat_rejects_oversized_text():
    assert client.post("/api/chat", json={"session_id": "big", "text": "x" * 3000}).status_code == 422


def test_forecast_unknown_404():
    assert client.get("/api/forecast", params={"crop": "tomato", "mandi_key": "Nowhere"}).status_code == 404
