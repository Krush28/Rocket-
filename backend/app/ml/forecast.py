"""Price forecasting: baselines + ETS + lag-Ridge + ensemble, rolling-origin backtest, honest gate.
Chronological splits only. A horizon is only 'ok' if the best model beats BOTH baselines by >=5% MAE
and its 80% interval coverage (on held-out folds) is within 0.2 of 0.8. Otherwise: no_reliable_forecast."""
import warnings
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

try:  # LightGBM when installed; sklearn's histogram GBM (same algorithm family) otherwise
    from lightgbm import LGBMRegressor as _GBM
    GBM_KW = dict(n_estimators=80, learning_rate=0.08, num_leaves=15, min_child_samples=10, verbose=-1)
    GBM_NAME = "lightgbm"
except Exception:
    from sklearn.ensemble import HistGradientBoostingRegressor as _GBM
    GBM_KW = dict(max_iter=80, learning_rate=0.08, max_leaf_nodes=15)
    GBM_NAME = "hist_gbm"

from app.repositories import market_data as MD
from app.core.meta import meta

HORIZONS = [1, 3, 7, 15, 30]
MIN_HISTORY = 120
N_FOLDS, STEP = 18, 5
BEAT_MARGIN, COVER_TOL = 0.05, 0.2
BASELINES = ("seasonal_naive", "ma7")
VERSION = "v2"  # v2: + SARIMA, + gradient boosting (LightGBM / hist GBM), 4-model ensemble
warnings.filterwarnings("ignore")


def daily(df: pd.DataFrame) -> pd.Series:
    s = df.set_index("date")["modal"].asfreq("D")
    return s.interpolate(limit=5, limit_area="inside")


def _predict_all(s: pd.Series, full: bool = True) -> dict:
    """Point forecasts for every horizon from every model, using only data in `s`. full=False skips SARIMA and GBM (fast path)."""
    last, n = s.iloc[-1], len(s)
    out = {m: {} for m in ("seasonal_naive", "ma7", "ets_damped", "sarima", "lag_ridge", "gbm", "ensemble")}
    ma = s.iloc[-7:].mean()
    for h in HORIZONS:
        ref = s.index[-1] + pd.Timedelta(days=h) - pd.Timedelta(days=365)
        out["seasonal_naive"][h] = s.get(ref, np.nan) if n > 365 else last
        if np.isnan(out["seasonal_naive"][h]):
            out["seasonal_naive"][h] = last
        out["ma7"][h] = ma
    try:
        fit = ExponentialSmoothing(np.log(s.iloc[-365:].values), trend="add", damped_trend=True).fit()
        fc = np.exp(fit.forecast(max(HORIZONS)))
        for h in HORIZONS:
            out["ets_damped"][h] = fc[h - 1]
    except Exception:
        for h in HORIZONS:
            out["ets_damped"][h] = last
    try:  # SARIMA(1,1,1)x(1,0,0,7): weekly market-day pattern; last 180 days keep it fast
        if not full:
            raise RuntimeError("fast path")
        sm = SARIMAX(np.log(s.iloc[-180:].values), order=(1, 1, 1), seasonal_order=(1, 0, 0, 7),
                     enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=25)
        fc = np.exp(sm.forecast(max(HORIZONS)))
        for h in HORIZONS:
            out["sarima"][h] = float(fc[h - 1])
    except Exception:
        for h in HORIZONS:
            out["sarima"][h] = last
    ls = np.log(s.values)
    lagset = (1, 2, 3, 7, 14, 28)
    r7 = pd.Series(ls).rolling(8).mean().values
    r28 = pd.Series(ls).rolling(29).mean().values
    doy = s.index.day_of_year.values
    base = np.column_stack([ls - np.roll(ls, L) for L in lagset] + [ls - r7, ls - r28])  # row t uses data <= t only
    t0 = 28
    for h in HORIZONS:
        t_all = np.arange(t0, n - h)
        if len(t_all) < 40:
            out["lag_ridge"][h] = out["gbm"][h] = last
            continue
        d = doy[t_all + h]
        X = np.column_stack([base[t_all], np.sin(2 * np.pi * d / 365), np.cos(2 * np.pi * d / 365)])
        y = ls[t_all + h] - ls[t_all]
        sc = StandardScaler().fit(X)
        r = Ridge(alpha=10.0).fit(sc.transform(X), y)
        dt = (s.index[-1] + pd.Timedelta(days=h)).day_of_year
        xt = np.concatenate([base[n - 1], [np.sin(2 * np.pi * dt / 365), np.cos(2 * np.pi * dt / 365)]])[None, :]
        out["lag_ridge"][h] = float(np.exp(ls[-1] + r.predict(sc.transform(xt))[0]))
        tt = t_all[-540:]  # gradient boosting on the same lag features (recent 1.5 years)
        Xg = X[-len(tt):]
        try:
            if not full:
                raise RuntimeError("fast path")
            g = _GBM(**GBM_KW).fit(Xg, y[-len(tt):])
            out["gbm"][h] = float(np.exp(ls[-1] + g.predict(xt)[0]))
        except Exception:
            out["gbm"][h] = last
    for h in HORIZONS:
        out["ensemble"][h] = float(np.mean([out[m][h] for m in (("ets_damped", "sarima", "lag_ridge", "gbm") if full else ("ets_damped", "lag_ridge"))]))
    if not full:
        del out["sarima"], out["gbm"]
    return out


def _metrics(g: pd.DataFrame) -> dict:
    e = g["actual"] - g["pred"]
    dirn = np.sign(g["pred"] - g["last"]) == np.sign(g["actual"] - g["last"])
    return {"mae": float(e.abs().mean()), "rmse": float(np.sqrt((e ** 2).mean())),
            "wape": float(e.abs().sum() / g["actual"].abs().sum()), "directional_accuracy": float(dirn.mean()), "n": int(len(g))}


def backtest(s: pd.Series, full: bool = True) -> pd.DataFrame:
    n = len(s)
    rows = []
    first = n - 1 - max(HORIZONS) - (N_FOLDS - 1) * STEP
    for fold, o in enumerate(range(first, n - max(HORIZONS), STEP)):
        pr = _predict_all(s.iloc[: o + 1], full)
        for m, d in pr.items():
            for h, p in d.items():
                a = s.iloc[o + h]
                if not np.isnan(a):
                    rows.append((fold, h, m, float(p), float(a), float(s.iloc[o])))
    return pd.DataFrame(rows, columns=["fold", "h", "model", "pred", "actual", "last"])


def _evaluate(bt: pd.DataFrame) -> dict:
    """Per horizon: metrics on held-out (second-half) folds; interval calibrated on first-half folds."""
    half = bt["fold"].max() // 2
    res = {}
    for h in HORIZONS:
        res[h] = {}
        for m, g in bt[bt.h == h].groupby("model"):
            cal, ev = g[g.fold <= half], g[g.fold > half]
            if len(cal) < 4 or len(ev) < 4:
                continue
            ratio = (cal.actual / cal.pred)
            lo_q, hi_q = ratio.quantile(0.10), ratio.quantile(0.90)
            cover = float(((ev.actual >= ev.pred * lo_q) & (ev.actual <= ev.pred * hi_q)).mean())
            full = g.actual / g.pred
            res[h][m] = {**_metrics(ev), "coverage_80": cover, "ratio_lo": float(full.quantile(0.10)), "ratio_hi": float(full.quantile(0.90))}
    return res


_POOL = None


def _cached(crop, mandi, last_date):
    from app.db import database
    from app.models import ForecastCache
    from sqlalchemy import select
    try:
        with database.SessionLocal() as db:
            return db.scalar(select(ForecastCache.payload).where(ForecastCache.crop == crop, ForecastCache.mandi == mandi,
                                                                 ForecastCache.last_date == last_date, ForecastCache.version == VERSION))
    except Exception:
        return None


def _store(crop, mandi, last_date, payload):
    from app.db import database
    from app.models import ForecastCache
    try:
        with database.SessionLocal() as db:
            db.add(ForecastCache(crop=crop, mandi=mandi, last_date=last_date, version=VERSION, payload=payload))
            db.commit()
    except Exception:
        pass  # a concurrent writer stored it first


def _full_in_background(crop, mandi, last_date):
    global _POOL
    if _POOL is None:
        from concurrent.futures import ThreadPoolExecutor
        _POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="forecast-full")

    def job():
        if _cached(crop, mandi, last_date) is None:
            _store(crop, mandi, last_date, _compute(crop, mandi, full=True))
            forecast.cache_clear()
    _POOL.submit(job)


@lru_cache(maxsize=256)
def forecast(crop: str, mandi: str) -> dict:
    """Full 6-model backtested forecast from forecast_cache when ready; otherwise the fast 4-model one now (ETS, lag-Ridge, baselines)
    while the full one is computed in the background (FORECAST_BACKGROUND=0 disables that; FORECAST_FULL_SYNC=1 computes it inline)."""
    import os
    df = MD.series(crop, mandi)
    if len(df) >= MIN_HISTORY:
        last = df["date"].iloc[-1].date()
        hit = _cached(crop, mandi, last)
        if hit:
            return hit
        if os.getenv("FORECAST_FULL_SYNC") == "1":
            out = _compute(crop, mandi, full=True)
            _store(crop, mandi, last, out)
            return out
        if os.getenv("FORECAST_BACKGROUND", "1") != "0":
            _full_in_background(crop, mandi, last)
    return _compute(crop, mandi, full=False)


def _compute(crop: str, mandi: str, full: bool) -> dict:
    df = MD.series(crop, mandi)
    base_meta = meta(MD.source_label(), MD.verification(), updated=MD.last_updated(crop, mandi) if len(df) else None)
    real_n = len(MD.real_only(df))
    if real_n < len(df):
        base_meta = {**base_meta, "history": {"real_days": real_n, "synthetic_days": len(df) - real_n, "note": MD.DEMO_HISTORY}}
    if len(df) < MIN_HISTORY:
        return {"status": "insufficient_data", "crop": crop, "mandi": mandi, "meta": {**base_meta, "error": f"only {len(df)} observations"}}
    s = daily(df)
    bt = backtest(s, full)
    ev = _evaluate(bt)
    pr = _predict_all(s, full)
    today = s.index[-1].date()
    out = []
    for h in HORIZONS:
        cand = {m: v for m, v in ev.get(h, {}).items() if m not in BASELINES}
        if not cand:
            out.append({"horizon_days": h, "status": "insufficient_data"})
            continue
        best = min(cand, key=lambda m: cand[m]["mae"])
        base_mae = min(ev[h][b]["mae"] for b in BASELINES if b in ev[h])
        e = cand[best]
        beats = e["mae"] <= base_mae * (1 - BEAT_MARGIN)
        calibrated = abs(e["coverage_80"] - 0.8) <= COVER_TOL
        point = pr[best][h]
        ok = beats and calibrated
        out.append({
            "horizon_days": h, "target_date": str(today + timedelta(days=h)),
            "status": "ok" if ok else "no_reliable_forecast",
            "predicted": round(point, 0), "lo": round(point * e["ratio_lo"], 0), "hi": round(point * e["ratio_hi"], 0),
            "interval": "80% empirical (residual ratios from backtest)",
            "model": best, "model_version": VERSION if full else VERSION + "-fast",
            "eval": {k: round(v, 3) for k, v in e.items() if k in ("mae", "rmse", "wape", "directional_accuracy", "coverage_80")},
            "baseline_mae": round(base_mae, 1), "eval_folds": e["n"],
            "gate": {"beats_baselines_by_5pct": bool(beats), "calibrated": bool(calibrated)},
            "confidence": ("moderate" if ok and e["wape"] < 0.08 else "low") if ok else "none",
        })
    return {"status": "ok", "crop": crop, "mandi": mandi, "current": float(s.iloc[-1]),
            "train_period": [str(s.index[0].date()), str(today)], "horizons": out,
            "trend_7d_pct": round((s.iloc[-1] / s.iloc[-8] - 1) * 100, 1), "trend_30d_pct": round((s.iloc[-1] / s.iloc[-31] - 1) * 100, 1),
            "note": "Forecasts are not guarantees. Evaluated on held-out chronological backtest folds.",
            "models": (["seasonal_naive", "ma7", "ets_damped", "sarima", "lag_ridge", GBM_NAME, "ensemble"] if full
                       else ["seasonal_naive", "ma7", "ets_damped", "lag_ridge", "ensemble"]),
            "meta": {**base_meta, "confidence": "see per-horizon"}}


def horizon(fc: dict, days: int) -> dict | None:
    for h in fc.get("horizons", []):
        if h["horizon_days"] == days:
            return h
    return None
