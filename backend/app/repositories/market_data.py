"""One place agents read mandis and prices from. LIVE when mandi_prices has any row (real data only, never padded with demo
values); DEMO otherwise (Rocket's labelled synthetic series). Mandi key = "<market>, <district>, <state>" in LIVE mode."""
import os
import re
import zlib
from functools import lru_cache
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import func, select

from app.db import database
from app.models import Commodity, Mandi, MandiPrice, StatePriceHistory
from app.services import demo_data as D
from app.services.adapters import agmarknet_datagov as adapters

LIVE_SOURCE = "data.gov.in Agmarknet daily price (official)"
COLS = ["date", "modal", "min", "max", "arrivals_t"]
HIST_DAYS = 3 * 365  # hybrid history length (forecasting needs >= 120 days; the gate backtests on it)
DEMO_HISTORY = "DEMO HISTORY: real mandi prices + Mandi-API state averages, older days a seasonal backfill anchored to them"


def clear() -> None:
    """Reads are cached for speed (a plan re-reads the same series many times); call after any price import or geocode."""
    for f in (live, mandis_with_prices, series, real_series, _state_hist, crop_median, crop_catalogue):
        f.cache_clear()


@lru_cache(maxsize=4096)
def live() -> bool:
    return adapters.live_mode()


@lru_cache(maxsize=4096)
def mandis_with_prices(crop: str) -> list[dict]:
    """Geocoded mandis that have at least one price row for this crop."""
    if not live():
        return [{"key": n, "name": n, "district": None, "state": s, "lat": la, "lon": lo}
                for n, (la, lo, s, _) in D.MANDIS.items()] if crop in D.CROPS else []
    with database.SessionLocal() as s:
        rows = s.execute(select(Mandi).distinct().join(MandiPrice, MandiPrice.mandi_id == Mandi.id)
                         .join(Commodity, Commodity.id == MandiPrice.commodity_id)
                         .where(Commodity.key == crop, Mandi.lat.isnot(None), Mandi.lon.isnot(None))).scalars().all()
    return [{"key": f"{m.name}, {m.district}, {m.state}", "name": m.name, "district": m.district, "state": m.state, "lat": m.lat, "lon": m.lon}
            for m in rows]


@lru_cache(maxsize=4096)
def series(crop: str, key: str) -> pd.DataFrame:
    """Daily modal/min/max (Rs/quintal) used for trends and forecasting. LIVE: the mandi's real rows, extended to HIST_DAYS by
    `_hybrid` (column `synthetic` marks every day that is not this mandi's own observation). Empty if the mandi has no real row."""
    if not live():
        return D.series(crop, key) if crop in D.CROPS and key in D.MANDIS else pd.DataFrame(columns=COLS)
    real = real_series(crop, key)
    if real.empty or os.getenv("KRISHIX_HYBRID_HISTORY", "1") == "0":
        return real.assign(synthetic=False)
    return _hybrid(crop, key, real)


def real_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["synthetic"]] if "synthetic" in df.columns else df


@lru_cache(maxsize=512)
def _state_hist(crop: str, state: str) -> pd.Series:
    with database.SessionLocal() as s:
        rows = s.execute(select(StatePriceHistory.price_date, StatePriceHistory.avg_modal)
                         .where(StatePriceHistory.commodity_key == crop, StatePriceHistory.state == state)).all()
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series([r[1] for r in rows], index=pd.to_datetime([r[0] for r in rows])).sort_index()


def _hybrid(crop: str, key: str, real: pd.DataFrame) -> pd.DataFrame:
    """Real days stay exactly as observed. Other days: the state-average shape scaled to this mandi, then a seasonal + AR(1) series
    (crop seasonality from services/crops.py) whose level is pinned to the real points (log-residual interpolation). Deterministic per key."""
    from app.services import crops as CR
    p = CR.params(crop)
    rng = np.random.default_rng(zlib.crc32(f"{crop}|{key}".encode()))
    end = real["date"].max()
    idx = pd.date_range(end - pd.Timedelta(days=HIST_DAYS - 1), end, freq="D")
    known = pd.Series(np.nan, index=idx)
    known.loc[real["date"]] = real["modal"].values
    is_real = known.notna().values
    sh = _state_hist(crop, key.rsplit(", ", 1)[-1])
    if len(sh):
        both = sh.reindex(real["date"]).values
        ok = ~np.isnan(both)
        ratio = float(np.median(real["modal"].values[ok] / both[ok])) if ok.any() else float(real["modal"].iloc[-1] / sh.iloc[-1])
        fill = (sh * ratio).reindex(idx)
        known = known.where(known.notna(), fill)
    t = idx.dayofyear.values
    ar = np.zeros(len(idx))
    for i in range(1, len(idx)):
        ar[i] = 0.97 * ar[i - 1] + rng.normal(0, p["vol"])
    synth = p["amp"] * np.sin(2 * np.pi * (t - p.get("phase", 0)) / 365) + ar + np.cumsum(rng.normal(0, p["vol"] / 6, len(idx)))
    k = known.notna().values
    resid = np.interp(np.arange(len(idx)), np.flatnonzero(k), np.log(known.values[k]) - synth[k])
    modal = np.where(k, known.values, np.exp(synth + resid))
    spread = float(np.clip(np.nanmedian((real["max"] - real["min"]) / real["modal"]) / 2, 0.05, 0.4)) if len(real) else 0.15
    out = pd.DataFrame({"date": idx, "modal": np.round(modal), "min": np.round(modal * (1 - spread)), "max": np.round(modal * (1 + spread)),
                        "arrivals_t": np.nan, "synthetic": ~is_real})
    r = real.set_index("date")
    out.loc[is_real, ["min", "max"]] = r.loc[idx[is_real], ["min", "max"]].values
    return out


@lru_cache(maxsize=4096)
def real_series(crop: str, key: str) -> pd.DataFrame:
    """Only this mandi's own observed rows (median across varieties/grades per day)."""
    parts = key.rsplit(", ", 2)
    if len(parts) != 3:
        return pd.DataFrame(columns=COLS)
    with database.SessionLocal() as s:
        rows = s.execute(select(MandiPrice.price_date, MandiPrice.modal_price, MandiPrice.min_price, MandiPrice.max_price)
                         .join(Mandi, Mandi.id == MandiPrice.mandi_id).join(Commodity, Commodity.id == MandiPrice.commodity_id)
                         .where(Commodity.key == crop, Mandi.name == parts[0], Mandi.district == parts[1], Mandi.state == parts[2])).all()
    if not rows:
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame([tuple(r) for r in rows], columns=["date", "modal", "min", "max"])
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby("date").agg(modal=("modal", "median"), min=("min", "min"), max=("max", "max")).reset_index()
    g["arrivals_t"] = float("nan")  # this source publishes no arrivals
    return g.sort_values("date").reset_index(drop=True)


def last_updated(crop: str, key: str) -> datetime | None:
    df = series(crop, key)
    return datetime.combine(df["date"].iloc[-1].date(), datetime.min.time(), tzinfo=timezone.utc) if len(df) else None


@lru_cache(maxsize=4096)
def crop_median(crop: str) -> float | None:
    """Median modal price for the crop across ALL mandis on the latest loaded date (needs >= 5 rows): the data-error yardstick."""
    with database.SessionLocal() as s:
        d = s.scalar(select(func.max(MandiPrice.price_date)).join(Commodity, Commodity.id == MandiPrice.commodity_id).where(Commodity.key == crop))
        if d is None:
            return None
        v = sorted(s.scalars(select(MandiPrice.modal_price).join(Commodity, Commodity.id == MandiPrice.commodity_id)
                             .where(Commodity.key == crop, MandiPrice.price_date == d)))
    return v[len(v) // 2] if len(v) >= 5 else None


def price_outlier(crop: str, modal: float) -> str | None:
    """LIVE mode guard: a price far from today's national median is excluded with a visible reason, never silently ranked."""
    if not live():
        return None
    med = crop_median(crop)
    if not med:
        return None
    if modal < 0.35 * med:
        return f"price is only {modal / med:.0%} of today's national median (Rs {med:,.0f}); likely a data error"
    if modal > 2.5 * med:
        return f"price is {modal / med:.1f}x today's national median (Rs {med:,.0f}); likely a data error"
    return None


def verification() -> str:
    return "official" if live() else "demo"


def source_label(crop: str | None = None, key: str | None = None) -> str:
    return LIVE_SOURCE if live() else f"{D.DEMO} (synthetic seeded series)"


def crop_params(crop: str) -> dict | None:
    """Shelf life / shrinkage / seasonality for ANY crop (services/crops.py: category defaults + calibrated overrides)."""
    from app.services import crops as CR
    return CR.params(crop)


@lru_cache(maxsize=4096)
def crop_catalogue() -> dict[str, list[str]]:
    """crop key -> spoken/written aliases. Rocket's multilingual aliases plus every commodity seen in the price feed."""
    from app.services import crops as CR
    cat = {k: list(c["aliases"]) for k, c in D.CROPS.items()}
    for k in CR.C:
        cat.setdefault(k, [])
        cat[k] += [a for a in CR.aliases(k) if a not in cat[k]]
    with database.SessionLocal() as s:
        for key in s.scalars(select(Commodity.key)):
            short = re.sub(r"\s*\(.*?\)\s*", " ", key).strip()
            inner = [x.strip() for x in re.findall(r"\(([^)]*)\)", key) for x in re.split(r"[/,]", x)]
            combo = [f"{short} {x}" for x in inner if x and x not in CR.GENERIC_INNER]  # "paddy basmati" beats plain "paddy"
            own = [x for x in inner if len(x) >= 4 and x not in CR.GENERIC_INNER]  # "basmati", "badam", "anjeer"
            cat.setdefault(key, [])
            cat[key] += [a for a in (key, short, *combo, *own) if a and a not in cat[key]]
    for alias, key in CR.EXTRA.items():  # local / Hinglish names, only for crops that exist in the catalogue
        if key in cat and alias not in cat[key]:
            cat[key].append(alias)
    return cat
