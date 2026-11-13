from fastapi import APIRouter, HTTPException, Query

from app.ml import forecast as F
from app.repositories import market_data as MD

router = APIRouter(tags=["market"])


@router.get("/meta")
def meta():
    return {"crops": sorted(MD.crop_catalogue()), "data_mode": "LIVE" if MD.live() else "DEMO DATA", "source": MD.source_label()}


@router.get("/forecast")
def forecast(crop: str = Query(max_length=120), mandi_key: str = Query(max_length=300)):
    if MD.series(crop, mandi_key).empty:
        raise HTTPException(404, "no prices for this crop at this mandi")
    return F.forecast(crop, mandi_key)


@router.get("/series")
def series(crop: str = Query(max_length=120), mandi_key: str = Query(max_length=300), days: int = Query(180, ge=1, le=3650)):
    df = MD.series(crop, mandi_key)
    if df.empty:
        raise HTTPException(404, "no prices for this crop at this mandi")
    df = df.tail(days)
    syn = df["synthetic"].tolist() if "synthetic" in df.columns else [False] * len(df)
    return {"label": MD.source_label(), "verification": MD.verification(), "unit": "Rs/quintal", "synthetic": syn,
            "history_note": MD.DEMO_HISTORY if any(syn) else None,
            "history": [[str(d.date()), float(v)] for d, v in zip(df["date"], df["modal"])], "forecast": F.forecast(crop, mandi_key)}
