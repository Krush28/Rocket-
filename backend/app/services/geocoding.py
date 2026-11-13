"""Place-name -> approximate coordinates via OpenStreetMap Nominatim (no key). Every result is cached in geocode_cache,
including not-found, and marked "approximate". Network errors are NOT cached so they retry later.
Nominatim policy: max 1 request/s, identifying User-Agent, cache results."""
import re
import time

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import GeocodeCache, Mandi

MIN_INTERVAL = 1.0
MAX_QUERY = 200  # geocode_cache.query is String(300)
UA = "KRISHI-X/0.1 (mandi price intelligence; dev)"
_last = 0.0
SUFFIX = re.compile(r"\b(apmc|a\.p\.m\.c\.?|mandi|market yard|market|\(f&v\)|f&v|\(.*?\))", re.I)


def _norm(q: str) -> str:
    return " ".join(q.lower().replace(",", ", ").split()).replace(" ,", ",")


def _lookup(db: Session, query: str, client: httpx.Client | None):
    """-> ("hit", dict) | ("miss", None) | ("error", None)."""
    global _last
    key = _norm(query)
    c = db.scalar(select(GeocodeCache).where(GeocodeCache.query == key))
    if c:
        return ("hit", {"name": query.strip(), "lat": c.lat, "lon": c.lon, "status": "approximate"}) if c.status == "approximate" else ("miss", None)
    own = client is None
    client = client or httpx.Client(timeout=20, headers={"User-Agent": UA})
    try:
        wait = MIN_INTERVAL - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        r = client.get(settings.geocoder_url, params={"q": query, "format": "jsonv2", "countrycodes": "in", "limit": 1})
        if r.status_code != 200:
            return ("error", None)
        res = r.json()
    except (httpx.HTTPError, ValueError):
        return ("error", None)
    finally:
        if own:
            client.close()
    if not res:
        _cache(db, GeocodeCache(query=key, status="not_found"))
        return ("miss", None)
    lat, lon = float(res[0]["lat"]), float(res[0]["lon"])
    _cache(db, GeocodeCache(query=key, lat=lat, lon=lon, display_name=(res[0].get("display_name") or "")[:400], status="approximate"))
    return ("hit", {"name": query.strip(), "lat": lat, "lon": lon, "status": "approximate"})


def _cache(db: Session, row: GeocodeCache):
    """A cache write must never fail the farmer's turn (e.g. a concurrent insert of the same query)."""
    try:
        db.add(row)
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def geocode(db: Session, query: str, *, client: httpx.Client | None = None) -> dict | None:
    if not query or not query.strip() or len(query) > MAX_QUERY:  # a whole paragraph is not a place name
        return None
    from app.services import gazetteer  # offline first: instant, works for villages and pincodes
    def offline(fuzzy=False):
        try:
            return gazetteer.find(db, query, fuzzy)
        except SQLAlchemyError:
            db.rollback()
            return None
    return offline() or _lookup(db, query, client)[1] or offline(fuzzy=True)


def clean_mandi_name(name: str) -> str:
    return " ".join(SUFFIX.sub(" ", name).split()) or name


def geocode_mandis(db: Session, limit: int | None = None, *, client: httpx.Client | None = None) -> dict:
    """Geocode pending mandis: name+district+state, name+state (Agmarknet district spellings often differ from OSM), then
    district+state. Errors leave the mandi pending."""
    out = {"approximate": 0, "not_found": 0, "error": 0}
    q = select(Mandi).where(Mandi.geo_status == "pending").order_by(Mandi.id)
    pg = db.bind.dialect.name == "postgresql"
    for m in db.scalars(q.limit(limit) if limit else q).all():
        status, hit = "miss", None
        name = clean_mandi_name(m.name)
        for query in (f"{name}, {m.district}, {m.state}", f"{name}, {m.state}", f"{m.district}, {m.state}"):
            status, hit = _lookup(db, query, client)
            if status != "miss":
                break
        if status == "error":
            out["error"] += 1
            continue
        if hit:
            m.lat, m.lon, m.geo_status = hit["lat"], hit["lon"], "approximate"
            if pg:
                db.flush()
                db.execute(text("UPDATE mandis SET geog = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography WHERE id = :id"),
                           {"lon": m.lon, "lat": m.lat, "id": m.id})
        else:
            m.geo_status = "not_found"
        out[m.geo_status] += 1
        db.commit()
    from app.repositories import market_data
    market_data.clear()  # new coordinates change which mandis can be ranked
    return out
