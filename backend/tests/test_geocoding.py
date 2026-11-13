import httpx
import pytest

from app.models import Mandi
from app.services import geocoding as G

PT = [{"lat": "15.40", "lon": "74.02", "display_name": "Ponda, North Goa, Goa, India"}]


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(G, "MIN_INTERVAL", 0)


def _client(fn, calls):
    def handler(req):
        calls.append(req.url.params["q"])
        return fn(req)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cache_hit_skips_network(db):
    calls = []
    c = _client(lambda r: httpx.Response(200, json=PT), calls)
    first = G.geocode(db, "Ponda, Goa", client=c)
    assert first == {"name": "Ponda, Goa", "lat": 15.40, "lon": 74.02, "status": "approximate"}
    assert G.geocode(db, "  ponda,  GOA ", client=c)["lat"] == first["lat"]
    assert len(calls) == 1


def test_network_error_returns_none_uncached(db):
    calls = []

    def boom(r):
        raise httpx.ConnectError("offline")
    assert G.geocode(db, "Ponda", client=_client(boom, calls)) is None
    assert G.geocode(db, "Ponda", client=_client(lambda r: httpx.Response(200, json=PT), calls))["lat"] == 15.40


def test_not_found_is_cached(db):
    calls = []
    c = _client(lambda r: httpx.Response(200, json=[]), calls)
    assert G.geocode(db, "xyzabc", client=c) is None
    assert G.geocode(db, "xyzabc", client=c) is None
    assert len(calls) == 1


def test_mandi_falls_back_to_district(db):
    db.add(Mandi(name="Unknownpur APMC", district="Solapur", state="Maharashtra"))
    db.commit()
    calls = []
    c = _client(lambda r: httpx.Response(200, json=[] if "Unknownpur" in r.url.params["q"] else PT), calls)
    assert G.geocode_mandis(db, client=c) == {"approximate": 1, "not_found": 0, "error": 0}
    m = db.query(Mandi).one()
    assert (m.geo_status, m.lat) == ("approximate", 15.40)
    assert calls[0] == "Unknownpur, Solapur, Maharashtra"  # 'APMC' suffix stripped


def test_mandi_left_pending_on_network_error(db):
    db.add(Mandi(name="X APMC", district="D", state="S"))
    db.commit()

    def boom(r):
        raise httpx.ConnectError("offline")
    assert G.geocode_mandis(db, client=_client(boom, []))["error"] == 1
    assert db.query(Mandi).one().geo_status == "pending"
