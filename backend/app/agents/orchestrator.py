"""KRISHI-X Orchestrator: explicit typed workflow over the agents. A failing agent degrades the plan, never crashes it."""
import time

from app.agents import agents as A
from app.services import costs
from app.repositories import market_data as MD
from app.services import demo_data as D
from app.core.meta import meta

PIPELINE = [  # (agent name, function, state key)
    ("Mandi Discovery Agent", A.mandi_discovery, "mandis_list"),
    ("Price Intelligence Agent", A.price_intelligence, "price_intel"),
    ("Market Activity Agent", A.market_activity, "activity"),
    ("Buyer Discovery Agent", A.buyer_discovery, "buyers"),
    ("Cold Storage Agent", A.cold_storage, "storage"),
    ("Transport Agent", A.transport_agent, "transport"),
    ("Shared Load Optimization Agent", A.shared_load, "shared_out"),
    ("Price Forecast Agent", A.price_forecast, "forecast_out"),
    ("Sell Now vs Hold Agent", A.sell_vs_hold, "sellhold"),
    ("Net Realization Agent", A.net_realization, "net"),
    ("Recommendation Agent", A.recommendation, "reco"),
]


def run(profile: dict, assumption_override: dict | None = None) -> dict:
    if profile["qty_kg"] <= 0:
        raise ValueError("quantity must be > 0")
    st = {"profile": profile, "assumptions": costs.assumptions(assumption_override)}
    trace, outputs = [{"agent": "Farmer Profile Agent", "status": "ok", "ms": 0, "detail": "profile confirmed by farmer"}], {}
    for name, fn, key in PIPELINE:
        t0 = time.time()
        try:
            r = fn(st)
            st[key] = r["data"]
            outputs[name] = r
            trace.append({"agent": name, "status": "ok", "ms": round((time.time() - t0) * 1000), "meta": r["meta"]})
        except Exception as e:  # degrade gracefully, report why
            outputs[name] = {"data": None, "meta": meta("orchestrator", "unverified", error=f"{type(e).__name__}: {e}")}
            trace.append({"agent": name, "status": "failed", "ms": round((time.time() - t0) * 1000), "error": f"{type(e).__name__}: {e}"})
            if name in ("Mandi Discovery Agent", "Price Intelligence Agent"):
                break  # nothing downstream is meaningful without prices
            for k in ("buyers", "storage", "transport"):
                st.setdefault(k, [])
            st.setdefault("sellhold", {"decision": {"action": "INSUFFICIENT INFORMATION", "reason": "upstream agent failed", "reconsider_on": None}, "holds": []})
            st.setdefault("net", {"options": [], "reference_nearest_mandi_now": None})
            st.setdefault("options", [])
    reco = outputs.get("Recommendation Agent", {}).get("data")
    return {"profile": profile, "assumptions": {**st["assumptions"], "placeholder_note": costs.PLACEHOLDER}, "trace": trace,
            "recommendation": reco, "options": st.get("options", []),
            "mandis": st.get("mandis_list"), "prices": (st.get("price_intel") or {}).get("mandis"), "retail": (st.get("price_intel") or {}).get("retail_context"), "activity": st.get("activity"),
            "forecasts": st.get("forecast_out"), "sell_vs_hold": st.get("sellhold"), "storage": st.get("storage"),
            "transport": st.get("transport"), "shared_load": st.get("shared_out"), "buyers": st.get("buyers"),
            "data_mode": "LIVE" if MD.live() else "DEMO",
            "labels": ("LIVE prices from data.gov.in (Agmarknet). Buyers, warehouses, transporters and the shared-load pool are still DEMO. " if MD.live()
                       else "DEMO DATA: prices, arrivals, buyers, warehouses, transporters are synthetic. ") + "Costs are ESTIMATES unless marked otherwise."}
