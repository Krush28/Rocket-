"""DEMO DATA. Synthetic, seeded, clearly labelled. Replace with real adapters (adapters.py) when keys/data exist.
Coordinates are approximate and UNVERIFIED. No phone numbers are invented. No real warehouse/transporter/buyer is implied."""
import zlib
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

DEMO = "DEMO DATA"
N_DAYS = 540

CROPS = {
    "onion": dict(base=1800, amp=0.30, phase=300, vol=0.014, max_hold_days=30, shrink_wk=1.5, cold_after_days=999,
                  aliases=["onion", "pyaz", "kanda", "प्याज", "कांदा"]),
    "tomato": dict(base=1500, amp=0.35, phase=120, vol=0.035, max_hold_days=7, shrink_wk=9.0, cold_after_days=2,
                   aliases=["tomato", "tomatoes", "tamatar", "टमाटर", "टोमॅटो", "टोमाटो"]),
    "potato": dict(base=1700, amp=0.18, phase=30, vol=0.009, max_hold_days=30, shrink_wk=1.0, cold_after_days=999,
                   aliases=["potato", "potatoes", "aloo", "batata", "आलू", "बटाटा"]),
}

# name: (lat, lon, state, price offset)
MANDIS = {
    "Lasalgaon APMC": (20.14, 74.24, "Maharashtra", 0.00),
    "Pimpalgaon Baswant APMC": (20.17, 73.99, "Maharashtra", -0.02),
    "Nashik APMC": (19.99, 73.79, "Maharashtra", 0.01),
    "Pune APMC": (18.52, 73.86, "Maharashtra", 0.05),
    "Vashi (Navi Mumbai) APMC": (19.07, 73.01, "Maharashtra", 0.09),
    "Kolhapur APMC": (16.70, 74.24, "Maharashtra", 0.03),
    "Belagavi APMC": (15.85, 74.50, "Karnataka", 0.02),
    "Mapusa Market": (15.59, 73.81, "Goa", 0.07),
    "Margao Market": (15.27, 73.96, "Goa", 0.08),
}

PLACES = {  # approximate, UNVERIFIED
    "niphad": (20.08, 74.11), "निफाड": (20.08, 74.11), "ponda": (15.40, 74.02), "पोंडा": (15.40, 74.02),
    "sinnar": (19.85, 73.99), "सिन्नर": (19.85, 73.99), "dindori": (20.20, 73.83), "दिंडोरी": (20.20, 73.83),
    "yeola": (20.04, 74.49), "येवला": (20.04, 74.49), "lasalgaon": (20.14, 74.24), "लासलगाव": (20.14, 74.24),
    "nashik": (19.99, 73.79), "नाशिक": (19.99, 73.79), "pune": (18.52, 73.86), "पुणे": (18.52, 73.86),
    "mapusa": (15.59, 73.81), "margao": (15.27, 73.96), "belagavi": (15.85, 74.50), "kolhapur": (16.70, 74.24),
    "कोल्हापूर": (16.70, 74.24), "पणजी": (15.49, 73.83), "panaji": (15.49, 73.83),
}

WAREHOUSES = [  # DEMO, fictional. availability is never claimed as confirmed.
    dict(id="W1", name="Demo Cold Store - Nashik belt", lat=20.05, lon=73.95, rate_qtl_day=2.2, min_days=3, handling_qtl=10,
         crops=["onion", "potato", "tomato"], type="cold storage", temp="2-6 C", capacity_qtl=8000),
    dict(id="W2", name="Demo Ventilated Onion Store - Lasalgaon", lat=20.13, lon=74.22, rate_qtl_day=0.8, min_days=7, handling_qtl=8,
         crops=["onion"], type="ventilated store", temp="ambient", capacity_qtl=15000),
    dict(id="W3", name="Demo Cold Store - Pune", lat=18.55, lon=73.90, rate_qtl_day=2.6, min_days=3, handling_qtl=12,
         crops=["onion", "potato", "tomato"], type="cold storage", temp="2-6 C", capacity_qtl=5000),
    dict(id="W4", name="Demo Cold Store - Goa", lat=15.45, lon=73.95, rate_qtl_day=3.0, min_days=2, handling_qtl=12,
         crops=["tomato", "potato", "onion"], type="cold storage", temp="2-6 C", capacity_qtl=2000),
]

TRANSPORTERS = [  # DEMO, fictional, no phone numbers
    dict(id="T1", name="Demo Fleet A (tempos)", vehicle="tempo", capacity_qtl=40, base=400, per_km=14, refrigerated=False),
    dict(id="T2", name="Demo Fleet B (trucks)", vehicle="truck", capacity_qtl=100, base=500, per_km=25, refrigerated=False),
    dict(id="T3", name="Demo Fleet C (reefer)", vehicle="reefer truck", capacity_qtl=100, base=1200, per_km=38, refrigerated=True),
]

BUYERS = [  # DEMO. "indicative" = interest only; "offer" = priced, time-bound (still demo).
    dict(id="B1", name="Demo Trader Co. (Mumbai)", kind="offer", crop="onion", lat=19.07, lon=73.01, qty_min=50, price_offset=0.03,
         pickup="buyer collects", grade="A"),
    dict(id="B2", name="Demo Food Processor (Pune)", kind="offer", crop="onion", lat=18.52, lon=73.86, qty_min=100, price_offset=0.02,
         pickup="delivery to plant", grade="A"),
    dict(id="B3", name="Demo Retail Chain (Pune)", kind="indicative", crop="onion", lat=18.52, lon=73.86, qty_min=30, price_offset=None,
         pickup="negotiable", grade="A"),
    dict(id="B4", name="Demo Trader Co. (Goa)", kind="offer", crop="tomato", lat=15.59, lon=73.81, qty_min=10, price_offset=0.06,
         pickup="buyer collects", grade="A"),
    dict(id="B5", name="Demo Wholesaler (Goa)", kind="indicative", crop="tomato", lat=15.27, lon=73.96, qty_min=10, price_offset=None,
         pickup="negotiable", grade="A"),
    dict(id="B6", name="Demo Trader Co. (Pune)", kind="offer", crop="potato", lat=18.52, lon=73.86, qty_min=50, price_offset=0.02,
         pickup="buyer collects", grade="A"),
]

RETAIL_CITIES = {"Mumbai": 0.55, "Pune": 0.50, "Panaji": 0.62}  # retail markup over wholesale (DEMO)

_cache: dict = {}


def series(crop: str, mandi: str) -> pd.DataFrame:
    """Daily demo wholesale prices (Rs/quintal) with ~4% missing days, ending today."""
    from . import adapters
    if adapters.live_mode():
        return adapters.live_df(crop, mandi)
    key = (crop, mandi)
    if key in _cache:
        return _cache[key]
    c, m = CROPS[crop], MANDIS[mandi]
    rng = np.random.default_rng(zlib.crc32(f"{crop}|{mandi}".encode()))
    idx = pd.date_range(end=pd.Timestamp(date.today()), periods=N_DAYS)
    doy = idx.day_of_year.values
    seasonal = c["amp"] * np.sin(2 * np.pi * (doy - c["phase"]) / 365)
    e = np.zeros(N_DAYS)
    for i in range(1, N_DAYS):
        e[i] = 0.94 * e[i - 1] + rng.normal(0, c["vol"])
    modal = c["base"] * (1 + seasonal) * np.exp(e) * (1 + m[3])
    arrivals = np.clip(260 * np.exp(-2.2 * (modal / c["base"] - 1)) * rng.lognormal(0, 0.12, N_DAYS), 20, None)
    df = pd.DataFrame({"date": idx, "modal": modal.round(0), "min": (modal * 0.86).round(0), "max": (modal * 1.14).round(0),
                       "arrivals_t": arrivals.round(1)})
    df = df[rng.random(N_DAYS) > 0.04].reset_index(drop=True)
    _cache[key] = df
    return df


def last_updated(crop, mandi):
    return datetime.combine(series(crop, mandi)["date"].iloc[-1].date(), datetime.min.time(), tzinfo=timezone.utc)


def has_data(crop, mandi) -> bool:
    return len(series(crop, mandi)) > 0


def live_mode_on() -> bool:
    from . import adapters
    return adapters.live_mode()


def source_label(crop, mandi) -> str:
    return "LIVE: data.gov.in Agmarknet (daily snapshots)" if live_mode_on() else f"{DEMO} (synthetic seeded series)"


def price_outlier(crop, modal):
    """Data-error guard (LIVE mode): a price far from today's national median for the crop is excluded with a reason, never silently ranked."""
    from . import adapters
    if not adapters.live_mode():
        return None
    med = adapters.crop_median(crop)
    if not med:
        return None
    if modal < 0.35 * med:
        return f"price is only {modal / med:.0%} of today's national median (Rs {med:,.0f}); likely a data error"
    if modal > 2.5 * med:
        return f"price is {modal / med:.1f}x today's national median (Rs {med:,.0f}); likely a data error"
    return None
