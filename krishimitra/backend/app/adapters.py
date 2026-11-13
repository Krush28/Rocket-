"""Live data adapter: official data.gov.in Agmarknet daily mandi prices (needs your free DATA_GOV_API_KEY).
Rows are snapshotted into SQLite so history accumulates day by day; `import_csv` backfills history from an Agmarknet/CEDA export.
No captcha bypass, no scraping. In live mode mandis with no live rows are EXCLUDED (never filled with demo values)."""
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

DB = Path(__file__).resolve().parents[1] / "live_prices.db"
RESOURCE = os.getenv("DATA_GOV_RESOURCE", "9ef84268-d588-465a-a308-a864a43d0070")  # current daily prices (id unverified; override via env)
URL = "https://api.data.gov.in/resource/{}"
COMMODITY = {"onion": "Onion", "tomato": "Tomato", "potato": "Potato"}
STATES = ["Maharashtra", "Goa", "Karnataka"]
ALIASES = {"Lasalgaon APMC": ["lasalgaon"], "Pimpalgaon Baswant APMC": ["pimpalgaon"], "Nashik APMC": ["nashik", "nasik"],
           "Pune APMC": ["pune"], "Vashi (Navi Mumbai) APMC": ["vashi", "navi mumbai"], "Kolhapur APMC": ["kolhapur"],
           "Belagavi APMC": ["belgaum", "belagavi"], "Mapusa Market": ["mapusa"], "Margao Market": ["margao", "madgaon"]}


def _con():
    c = sqlite3.connect(DB)
    c.execute("""create table if not exists prices(market text, state text, district text, commodity text, variety text, grade text,
                 date text, min_price real, max_price real, modal_price real, fetched text,
                 primary key(market, state, commodity, variety, grade, date))""")
    return c


def live_mode() -> bool:
    if not DB.exists():
        return False
    with _con() as c:
        return c.execute("select count(*) from prices").fetchone()[0] > 0


def parse_record(r: dict) -> dict | None:
    """One API record -> normalised row, or None if unusable (missing/NA/non-positive prices, bad date)."""
    try:
        modal = float(r["modal_price"])
        date = datetime.strptime(str(r["arrival_date"]), "%d/%m/%Y").date().isoformat()
        lo, hi = float(r.get("min_price") or modal), float(r.get("max_price") or modal)
    except (KeyError, ValueError, TypeError):
        return None
    if modal <= 0:
        return None
    return dict(market=r.get("market", ""), state=r.get("state", ""), district=r.get("district", ""), commodity=str(r.get("commodity", "")).lower(),
                variety=r.get("variety", ""), grade=r.get("grade", ""), date=date, min_price=lo, max_price=hi, modal_price=modal)


def upsert(rows: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _con() as c:
        c.executemany("insert or replace into prices values(:market,:state,:district,:commodity,:variety,:grade,:date,:min_price,:max_price,:modal_price,:fetched)",
                      [{**r, "fetched": now} for r in rows])
    return len(rows)


def fetch(crop: str, state: str, key: str | None = None, page: int = 500, max_pages: int = 20) -> list[dict]:
    key = key or os.getenv("DATA_GOV_API_KEY")
    if not key:
        raise RuntimeError("DATA_GOV_API_KEY is not set (free key: data.gov.in -> My Account)")
    out, offset = [], 0
    for _ in range(max_pages):
        r = httpx.get(URL.format(RESOURCE), timeout=30, params={"api-key": key, "format": "json", "offset": offset, "limit": page,
                                                                "filters[state]": state, "filters[commodity]": COMMODITY[crop]})
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


def import_csv(path: str) -> int:
    """Backfill from an Agmarknet/CEDA CSV export. Needs columns for market, state, commodity, date and modal price."""
    df = pd.read_csv(path)
    low = {c.lower().strip(): c for c in df.columns}

    def pick(*names):  # exact header first, then "starts with" (e.g. "Modal Price (Rs./Quintal)")
        return next((low[n] for n in names if n in low), None) or next((c for k, c in low.items() if any(k.startswith(n) for n in names)), None)
    m = dict(market=pick("market", "market name", "mandi"), state=pick("state", "state name"), commodity=pick("commodity", "commodity name"),
             date=pick("arrival_date", "date", "price date", "reported date"), mn=pick("min_price", "min_x0020_price", "min price", "min x"),
             mx=pick("max_price", "max_x0020_price", "max price", "max x"), md=pick("modal_price", "modal_x0020_price", "modal price", "modal x"), var=pick("variety"),
             gr=pick("grade"), dist=pick("district", "district name"))
    if any(m[k] is None for k in ("market", "state", "commodity", "date", "md")):
        raise ValueError(f"CSV is missing required columns; found {list(df.columns)}")
    rows = []
    for _, r in df.iterrows():
        rec = parse_record({"market": r[m["market"]], "state": r[m["state"]], "district": r[m["dist"]] if m["dist"] else "", "commodity": r[m["commodity"]],
                            "variety": r[m["var"]] if m["var"] else "", "grade": r[m["gr"]] if m["gr"] else "",
                            "arrival_date": pd.to_datetime(r[m["date"]], dayfirst=True).strftime("%d/%m/%Y"),
                            "min_price": r[m["mn"]] if m["mn"] else None, "max_price": r[m["mx"]] if m["mx"] else None, "modal_price": r[m["md"]]})
        if rec:
            rows.append(rec)
    return upsert(rows)


def live_df(crop: str, mandi: str) -> pd.DataFrame:
    """Daily series for one of our mandis from live rows (median across varieties/grades per day). Empty if none."""
    from .demo_data import MANDIS
    empty = pd.DataFrame(columns=["date", "modal", "min", "max", "arrivals_t"])
    if not DB.exists():
        return empty
    with _con() as c:
        rows = c.execute("select market,date,min_price,max_price,modal_price from prices where commodity=? and state=?", (crop, MANDIS[mandi][2])).fetchall()
    al = ALIASES.get(mandi, [mandi.split()[0].lower()])
    df = pd.DataFrame([r for r in rows if any(a in r[0].lower() for a in al)], columns=["market", "date", "min", "max", "modal"])
    if df.empty:
        return empty
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby("date").agg(modal=("modal", "median"), min=("min", "min"), max=("max", "max")).reset_index()
    g["arrivals_t"] = float("nan")  # this resource has no arrivals column
    return g.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":  # python -m app.adapters refresh | import <file.csv>
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        print(refresh())
    elif len(sys.argv) > 2 and sys.argv[1] == "import":
        print({"rows_upserted": import_csv(sys.argv[2])})
    else:
        print("usage: python -m app.adapters refresh | import <file.csv>")
