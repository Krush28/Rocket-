"""Mandi API rows + hybrid history (real points kept exactly, backfill labelled) + fast/full forecast split."""
from datetime import date, timedelta

from app.ml import forecast as F
from app.repositories import market_data as MD
from app.services.adapters import mandi_api
from app.services.adapters.agmarknet_datagov import upsert


def _rows(n=5, crop="Brinjal"):
    d0 = date.today() - timedelta(days=n)
    return [mandi_api.to_row({"state": "Maharashtra", "district": "Pune", "market": "Pune APMC ", "commodity": crop, "variety": "Other",
                              "grade": "FAQ", "arrival_date": str(d0 + timedelta(days=i)), "min_price": 1000, "max_price": 2000,
                              "modal_price": 1500 + 10 * i}) for i in range(n)]


def test_mandi_api_row_parsing():
    r = _rows(1)[0]
    assert r["market"] == "Pune APMC" and r["commodity"] == "brinjal" and r["modal_price"] == 1500
    assert mandi_api.to_row({"modal_price": 0, "arrival_date": "2026-10-01"}) is None
    assert mandi_api.to_row({"modal_price": 10, "arrival_date": "bad"}) is None


def test_hybrid_keeps_real_points_and_labels_backfill(db, monkeypatch):
    upsert(_rows(), source=mandi_api.SOURCE)
    monkeypatch.setenv("KRISHIX_HYBRID_HISTORY", "1")
    MD.clear()
    key = "Pune APMC, Pune, Maharashtra"
    df = MD.series("brinjal", key)
    assert len(df) == MD.HIST_DAYS and int((~df["synthetic"]).sum()) == 5
    real = MD.real_only(df)
    assert list(real["modal"]) == [1500, 1510, 1520, 1530, 1540]  # observed values untouched
    assert (df["modal"] > 0).all() and df["date"].is_monotonic_increasing
    assert MD.series("brinjal", key)["modal"].equals(df["modal"])  # deterministic


def test_fast_forecast_runs_on_hybrid_and_reports_history(db, monkeypatch):
    upsert(_rows(), source=mandi_api.SOURCE)
    monkeypatch.setenv("KRISHIX_HYBRID_HISTORY", "1")
    MD.clear()
    F.forecast.cache_clear()
    fc = F.forecast("brinjal", "Pune APMC, Pune, Maharashtra")
    assert fc["status"] == "ok" and fc["meta"]["history"]["real_days"] == 5
    assert "sarima" not in fc["models"] and all(h.get("model_version", "v2-fast").endswith("fast") for h in fc["horizons"] if "model" in h)
