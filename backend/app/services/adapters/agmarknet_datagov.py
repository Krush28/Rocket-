"""Live data adapter: official data.gov.in Agmarknet daily mandi prices (API with DATA_GOV_API_KEY, or the portal's CSV download).
Rows go into mandi_prices (verification_status="official") so history accumulates day by day; `import_csv` also backfills exports.
No captcha bypass, no scraping. In live mode mandis with no live rows are EXCLUDED (never filled with demo values)."""
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
from sqlalchemy import exists, select

from app.db import database
from app.models import AuditLog, Commodity, DataSource, Mandi, MandiPrice

RESOURCE = os.getenv("DATA_GOV_RESOURCE", "9ef84268-d588-465a-a308-a864a43d0070")  # "Current Daily Price ... (Mandi)", verified 2026-11-13
URL = "https://api.data.gov.in/resource/{}"
SOURCE = "data.gov.in 9ef84268 (Agmarknet daily prices)"
COMMODITY = {"onion": "Onion", "tomato": "Tomato", "potato": "Potato"}
STATES = ["Maharashtra", "Goa", "Karnataka"]


def api_key() -> str | None:
    """DATA_GOV_API_KEY from the environment, else from backend/.env (gitignored). Never logged."""
    if os.getenv("DATA_GOV_API_KEY"):
        return os.getenv("DATA_GOV_API_KEY")
    env = Path(__file__).resolve().parents[3] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATA_GOV_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def live_mode() -> bool:
    with database.SessionLocal() as s:
        return bool(s.scalar(select(exists().where(MandiPrice.id.isnot(None)))))


def commodity_key(name: str) -> str:
    return " ".join(str(name).lower().split())


def _txt(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def parse_record(r: dict) -> dict | None:
    """One API record -> normalised row, or None if unusable (missing/NA/non-positive prices, bad date)."""
    try:
        modal = float(r["modal_price"])
        d = datetime.strptime(str(r["arrival_date"]), "%d/%m/%Y").date().isoformat()
        lo, hi = float(r.get("min_price") or modal), float(r.get("max_price") or modal)
    except (KeyError, ValueError, TypeError):
        return None
    if not modal > 0 or pd.isna(lo) or pd.isna(hi):
        return None
    name = _txt(r.get("commodity"))
    return dict(market=_txt(r.get("market")), state=_txt(r.get("state")), district=_txt(r.get("district")), commodity=commodity_key(name),
                commodity_name=name, variety=_txt(r.get("variety")), grade=_txt(r.get("grade")), date=d, min_price=lo, max_price=hi, modal_price=modal)


def _insert(s):
    if s.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert


def upsert(rows: list[dict], observed_at: datetime | None = None) -> int:
    """Idempotent write of parsed rows; creates mandis/commodities on first sight. Returns rows written."""
    if not rows:
        return 0
    obs = observed_at or datetime.now(timezone.utc)
    with database.SessionLocal() as s:
        src = s.scalar(select(DataSource).where(DataSource.name == SOURCE))
        if not src:
            src = DataSource(name=SOURCE, kind="government_api", url=f"https://data.gov.in/resource/{RESOURCE}",
                             licence_note="Government Open Data License - India")
            s.add(src)
            s.flush()
        com = {c.key: c.id for c in s.scalars(select(Commodity))}
        man = {(m.name, m.district, m.state): m.id for m in s.scalars(select(Mandi))}
        for r in rows:
            if r["commodity"] not in com:
                c = Commodity(name=r.get("commodity_name") or r["commodity"].title(), key=r["commodity"])
                s.add(c)
                s.flush()
                com[c.key] = c.id
            mk = (r["market"], r["district"], r["state"])
            if mk not in man:
                m = Mandi(name=mk[0], district=mk[1], state=mk[2])
                s.add(m)
                s.flush()
                man[mk] = m.id
        vals = {}
        for r in rows:  # last row wins within one batch, same as the unique key
            k = (man[(r["market"], r["district"], r["state"])], com[r["commodity"]], r["variety"], r["grade"], date.fromisoformat(r["date"]))
            vals[k] = dict(mandi_id=k[0], commodity_id=k[1], variety=k[2], grade=k[3], price_date=k[4], min_price=r["min_price"],
                           max_price=r["max_price"], modal_price=r["modal_price"], source_id=src.id, observed_at=obs, verification_status="official")
        ins = _insert(s)
        batch = list(vals.values())
        for i in range(0, len(batch), 1000):
            stmt = ins(MandiPrice).values(batch[i:i + 1000])
            s.execute(stmt.on_conflict_do_update(index_elements=["mandi_id", "commodity_id", "variety", "grade", "price_date"],
                                                 set_={c: stmt.excluded[c] for c in ("min_price", "max_price", "modal_price", "observed_at")}))
        s.commit()
    return len(vals)


def _get(key: str, params: dict, tries: int = 3):
    """GET with backoff: the API is slow and rate-limits (HTTP 429, and shared public keys hit it constantly)."""
    import time
    last = None
    for i in range(tries):
        try:
            r = httpx.get(URL.format(RESOURCE), timeout=60, params={"api-key": key, **params})
            if r.status_code != 429:
                return r
            last = r
        except httpx.TimeoutException as e:
            last = e
        time.sleep(4 * 3 ** i)
    if isinstance(last, Exception):
        raise RuntimeError(f"data.gov.in timed out after {tries} tries")
    return last


def fetch(crop: str, state: str, key: str | None = None, page: int = 500, max_pages: int = 20) -> list[dict]:
    key = key or api_key()
    if not key:
        raise RuntimeError("DATA_GOV_API_KEY is not set (free key: data.gov.in -> My Account)")
    out, offset = [], 0
    for _ in range(max_pages):
        r = _get(key, {"format": "json", "offset": offset, "limit": page, "filters[state]": state, "filters[commodity]": COMMODITY[crop]})
        if r.status_code != 200:
            raise RuntimeError(f"data.gov.in returned HTTP {r.status_code}: {r.text[:160]}")
        recs = r.json().get("records", [])
        out += [p for p in map(parse_record, recs) if p]
        if len(recs) < page:
            break
        offset += page
    return out


def refresh(crops=None, states=None) -> dict:
    n, errs = 0, []
    for crop in crops or COMMODITY:
        for st in states or STATES:
            try:
                n += upsert(fetch(crop, st))
            except Exception as e:  # report, keep going
                errs.append(f"{crop}/{st}: {e}")
    return {"rows_upserted": n, "errors": errs}


def import_csv(path: str) -> dict:
    """Backfill from a data.gov.in / Agmarknet / CEDA CSV. Needs market, state, commodity, date and modal price columns."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    low = {c.lower().strip(): c for c in df.columns}

    def pick(*names):  # exact header first, then "starts with" (e.g. "Modal Price (Rs./Quintal)")
        return next((low[n] for n in names if n in low), None) or next((c for k, c in low.items() if any(k.startswith(n) for n in names)), None)
    m = dict(market=pick("market", "market name", "mandi"), state=pick("state", "state name"), commodity=pick("commodity", "commodity name"),
             date=pick("arrival_date", "date", "price date", "reported date"), mn=pick("min_price", "min_x0020_price", "min price", "min x"),
             mx=pick("max_price", "max_x0020_price", "max price", "max x"), md=pick("modal_price", "modal_x0020_price", "modal price", "modal x"), var=pick("variety"),
             gr=pick("grade"), dist=pick("district", "district name"))
    if any(m[k] is None for k in ("market", "state", "commodity", "date", "md")):
        raise ValueError(f"CSV is missing required columns; found {list(df.columns)}")
    dates = pd.to_datetime(df[m["date"]], dayfirst=True, errors="coerce", format="mixed")
    col = lambda k: df[m[k]] if m[k] else pd.Series([""] * len(df))  # noqa: E731
    recs = [parse_record({"market": a, "state": b, "district": c, "commodity": d, "variety": e, "grade": f,
                          "arrival_date": dt.strftime("%d/%m/%Y") if not pd.isna(dt) else "", "min_price": g or None, "max_price": h or None, "modal_price": i})
            for a, b, c, d, e, f, dt, g, h, i in zip(col("market"), col("state"), col("dist"), col("commodity"), col("var"), col("gr"),
                                                     dates, col("mn"), col("mx"), col("md"))]
    rows = [r for r in recs if r]
    obs = datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc)
    n = upsert(rows, observed_at=obs)
    return {"rows_read": len(df), "rows_upserted": n, "rows_skipped": len(df) - len(rows)}


def watch_dirs() -> list[Path]:
    """Folders scanned for the daily data.gov.in CSV (override with KRISHIX_WATCH_DIRS, separated by ';')."""
    env = os.getenv("KRISHIX_WATCH_DIRS")
    if env:
        return [Path(x) for x in env.split(";") if x.strip()]
    dl = Path.home() / "Downloads"
    root = Path(__file__).resolve().parents[4]
    return list(dict.fromkeys([dl, dl / "mandiproject", root / "data" / "raw", Path("/data/raw")]))


def _seen(path: str, mtime: float) -> bool:
    with database.SessionLocal() as s:
        return bool(s.scalar(select(exists().where(AuditLog.action == "csv_import", AuditLog.entity_id == f"{mtime}", AuditLog.entity == path))))


def _log_import(path: str, mtime: float, report: dict):
    with database.SessionLocal() as s:
        s.add(AuditLog(actor="system", action="csv_import", entity=path, entity_id=f"{mtime}", detail=report))
        s.commit()


def scan_and_import(dirs=None, pattern: str = "9ef84268*.csv") -> list[dict]:
    """Import any not-yet-imported data.gov.in price CSV (same resource-id filename the portal's Download button gives)."""
    done = []
    for d in dirs or watch_dirs():
        if not d.is_dir():
            continue
        for f in sorted(d.glob(pattern)):
            mt = f.stat().st_mtime
            if _seen(str(f), mt):
                continue
            try:
                rep = import_csv(str(f))
            except Exception as e:  # unreadable/partial download: try again next scan
                done.append({"file": str(f), "error": str(e)})
                continue
            _log_import(str(f), mt, rep)
            done.append({"file": str(f), "rows": rep["rows_upserted"]})
    return done


def last_import() -> dict | None:
    with database.SessionLocal() as s:
        r = s.scalars(select(AuditLog).where(AuditLog.action == "csv_import").order_by(AuditLog.id.desc())).first()
    return {"file": Path(r.entity).name, "rows": (r.detail or {}).get("rows_upserted"), "at": r.at.isoformat() if r.at else None} if r else None




if __name__ == "__main__":  # python -m app.services.adapters.agmarknet_datagov refresh | import <file.csv>
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        print(refresh())
    elif len(sys.argv) > 2 and sys.argv[1] == "import":
        print(import_csv(sys.argv[2]))
    else:
        print("usage: python -m app.services.adapters.agmarknet_datagov refresh | import <file.csv>")
