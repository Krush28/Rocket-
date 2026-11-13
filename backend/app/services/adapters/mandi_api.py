"""Live prices from the keyless Mandi Price API (https://mandi-api.onrender.com/v1, data.gov.in mirror; 100 req / 15 min / IP).
- latest per-market prices for state x crop -> mandi_prices (verification "official", source "mandi-api")
- state-average daily history -> state_price_history (shapes the hybrid history in market_data.series)
- new mandis are geocoded offline with the GeoNames gazetteer (instant, no Nominatim calls)
Runs as a throttled background job (`start_background`) and from the CLI:  python -m app.services.adapters.mandi_api [state] [crop]"""
import os
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import select, text

from app.db import database
from app.models import Mandi, StatePriceHistory
from app.repositories import sessions as SS
from app.services.adapters.agmarknet_datagov import commodity_key, upsert

BASE = os.getenv("MANDI_API_URL", "https://mandi-api.onrender.com/v1")
SOURCE = "Mandi Price API (data.gov.in mirror)"
STATES = ["Maharashtra", "Uttar Pradesh", "Punjab", "Madhya Pradesh", "Karnataka"]
CROPS = ["Onion", "Tomato", "Potato", "Brinjal", "Green Chilli", "Cauliflower", "Cabbage", "Bhindi(Ladies Finger)", "Wheat", "Soyabean",
         "Garlic", "Ginger(Green)", "Banana", "Carrot", "Bitter gourd", "Bottle gourd", "Capsicum", "Cucumbar(Kheera)", "Pomegranate", "Maize",
         "Cotton", "Coriander(Leaves)", "Green Peas", "Grapes", "Paddy(Common)"]
MIN_GAP_S = float(os.getenv("MANDI_API_GAP_S", "9.5"))  # 100 requests per 15 minutes
JOB_KEY = "job:mandi_api"
_last = 0.0
_lock = threading.Lock()


def _get(path: str, params: dict) -> list:
    """Throttled GET; waits out HTTP 429 using the ratelimit-reset header. Returns the `data` list ([] on failure)."""
    global _last
    for _ in range(3):
        with _lock:
            wait = MIN_GAP_S - (time.monotonic() - _last)
            if wait > 0:
                time.sleep(wait)
            _last = time.monotonic()
        try:
            r = httpx.get(BASE + path, params=params, timeout=60)
        except httpx.HTTPError:
            time.sleep(5)
            continue
        if r.status_code == 429:
            time.sleep(min(int(r.headers.get("ratelimit-reset", "60") or 60) + 1, 900))
            continue
        if r.status_code != 200:
            return []
        try:
            return r.json().get("data") or []
        except ValueError:
            return []
    return []


def to_row(r: dict) -> dict | None:
    try:
        modal = float(r["modal_price"])
        d = str(r["arrival_date"])[:10]
        date.fromisoformat(d)
    except (KeyError, TypeError, ValueError):
        return None
    if modal <= 0:
        return None
    name = str(r.get("commodity") or "").strip()
    lo, hi = float(r.get("min_price") or modal), float(r.get("max_price") or modal)
    return dict(market=" ".join(str(r.get("market") or "").split()), state=str(r.get("state") or "").strip(), district=str(r.get("district") or "").strip(),
                commodity=commodity_key(name), commodity_name=name, variety=str(r.get("variety") or "").strip(), grade=str(r.get("grade") or "").strip(),
                date=d, min_price=lo, max_price=hi, modal_price=modal)


def import_latest(state: str, crop: str) -> int:
    rows = [x for x in (to_row(r) for r in _get("/prices", {"state": state, "commodity": crop})) if x and x["market"]]
    return upsert(rows, source=SOURCE, source_url=BASE, kind="open_api") if rows else 0


def import_history(state: str, crop: str, days: int = 365) -> int:
    data, start = [], date.today() - timedelta(days=days)
    with database.SessionLocal() as s:  # resume after the newest day we already have
        have = s.scalar(select(StatePriceHistory.price_date).where(StatePriceHistory.state == state, StatePriceHistory.commodity_key == commodity_key(crop))
                        .order_by(StatePriceHistory.price_date.desc()).limit(1))
    if have:
        start = have + timedelta(days=1)
    for _ in range(8):  # the API returns about 30 days per call: page forward by date window
        if start > date.today():
            break
        page = _get("/prices/history", {"state": state, "commodity": crop, "from": str(start), "to": str(date.today())})
        if not page:
            break
        data += page
        start = date.fromisoformat(str(page[-1]["arrival_date"])[:10]) + timedelta(days=1)
    vals = []
    for r in data:
        try:
            vals.append(dict(state=state, commodity_key=commodity_key(crop), price_date=date.fromisoformat(str(r["arrival_date"])[:10]),
                             avg_modal=float(r["avg_modal_price"]), avg_min=float(r.get("avg_min_price") or 0) or None,
                             avg_max=float(r.get("avg_max_price") or 0) or None, data_points=int(r.get("data_points") or 0)))
        except (KeyError, TypeError, ValueError):
            continue
    if not vals:
        return 0
    with database.SessionLocal() as s:
        if s.bind.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        stmt = insert(StatePriceHistory).values(vals)
        s.execute(stmt.on_conflict_do_update(index_elements=["state", "commodity_key", "price_date"],
                                             set_={c: stmt.excluded[c] for c in ("avg_modal", "avg_min", "avg_max", "data_points")}))
        s.commit()
    from app.repositories import market_data
    market_data.clear()
    return len(vals)


def geocode_new_mandis() -> int:
    """Place every not-yet-geocoded mandi with the offline gazetteer (market town + district, else district HQ)."""
    from app.services import gazetteer
    from app.services.geocoding import clean_mandi_name
    n = 0
    with database.SessionLocal() as s:
        pg = s.bind.dialect.name == "postgresql"
        for m in s.scalars(select(Mandi).where(Mandi.lat.is_(None))).all():
            name = clean_mandi_name(m.name).replace("Agricultural Produce Market Committee", "").strip(" ,")
            hit = None
            for q in (f"{name}, {m.district}, {m.state}", f"{m.district}, {m.state}"):
                hit = gazetteer.find(s, q) if q.strip(", ") else None
                if hit and (hit.get("state") or "").lower() in ("", m.state.lower()):
                    break
                hit = None
            if not hit:
                continue
            m.lat, m.lon, m.geo_status = hit["lat"], hit["lon"], "approximate"
            if pg:
                s.flush()
                s.execute(text("UPDATE mandis SET geog = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography WHERE id = :id"),
                          {"lon": m.lon, "lat": m.lat, "id": m.id})
            n += 1
        s.commit()
    from app.repositories import market_data
    market_data.clear()
    return n


def run(states=None, crops=None, history=True) -> dict:
    """One full refresh. Progress is saved per state x crop so a restart resumes instead of re-fetching."""
    out = {"prices": 0, "history_days": 0, "geocoded": 0, "pairs": 0}
    with database.SessionLocal() as s:
        job = SS.load(s, JOB_KEY) or {}
    today = str(date.today())
    done = set(job.get("done", [])) if job.get("day") == today else set()
    for st in states or STATES:
        for c in crops or CROPS:
            pair = f"{st}|{c}"
            if pair in done:
                continue
            out["prices"] += import_latest(st, c)
            if history:
                out["history_days"] += import_history(st, c)
            done.add(pair)
            out["pairs"] += 1
            with database.SessionLocal() as s:
                SS.save(s, JOB_KEY, {"day": today, "done": sorted(done), "updated": datetime.now(timezone.utc).isoformat()}, confirmed=False)
        out["geocoded"] += geocode_new_mandis()
        from app.services import ops  # new districts get a storage network too
        with database.SessionLocal() as s:
            ops.seed_warehouses(s)
    return out


def status() -> dict:
    with database.SessionLocal() as s:
        job = SS.load(s, JOB_KEY) or {}
    return {"day": job.get("day"), "pairs_done": len(job.get("done", [])), "pairs_total": len(STATES) * len(CROPS), "updated": job.get("updated")}


def start_background() -> None:
    """Daily refresh in a daemon thread (first run at startup, resumable). Disabled with MANDI_API_JOB=0 (tests)."""
    if os.getenv("MANDI_API_JOB", "1") == "0":
        return

    def loop():
        while True:
            try:
                run()
            except Exception as e:  # a failed refresh must never take the API down
                print("mandi_api job error:", e, flush=True)
            time.sleep(6 * 3600)
    threading.Thread(target=loop, daemon=True, name="mandi-api-job").start()


if __name__ == "__main__":
    a = sys.argv[1:]
    print(run([a[0]] if a else None, [a[1]] if len(a) > 1 else None), flush=True)
