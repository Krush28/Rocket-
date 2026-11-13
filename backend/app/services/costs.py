"""Deterministic money maths: transport, net realization, hold economics, sell-vs-hold decision.
No LLM here. Every cost default is an unverified placeholder the user can override."""
import math
from datetime import date, timedelta

from app.services.demo_data import TRANSPORTERS

PLACEHOLDER = "[Unverified placeholder - edit me]"
DEFAULTS = dict(
    commission_pct=4.0, commission_payer="buyer",  # seller | buyer
    hamali_per_qtl=15.0, transit_loss_pct=0.5, risk_allowance_pct=0.0,
    road_factor=1.3, financing_annual_pct=12.0, ambient_temp_c=28.0, cold_shrink_factor=0.4,
    sources={k: "unverified" for k in ("commission", "hamali", "transit_loss", "vehicles", "storage", "financing")},
)
RISK_LAMBDA = 0.25  # ranking penalty weight on (expected - downside) for forecast-dependent options


def assumptions(override: dict | None = None) -> dict:
    a = {**DEFAULTS, **{k: v for k, v in (override or {}).items() if k in DEFAULTS and k != "sources"}}
    a["sources"] = {**DEFAULTS["sources"], **{k: "user" for k in (override or {}) if k in DEFAULTS}}
    return a


def transport(qty_qtl: float, km: float, refrigerated=False, quote: float | None = None) -> dict:
    """Cheapest vehicle type that can do the job (multiple trips if needed). ESTIMATE unless user-entered quote."""
    if qty_qtl <= 0:
        raise ValueError("quantity must be > 0")
    opts = []
    for v in TRANSPORTERS:
        if refrigerated and not v["refrigerated"]:
            continue
        if not refrigerated and v["refrigerated"]:
            continue
        trips = math.ceil(qty_qtl / v["capacity_qtl"])
        opts.append(dict(vehicle=v["vehicle"], transporter=v["name"], trips=trips, total=trips * (v["base"] + v["per_km"] * km),
                         capacity_qtl=v["capacity_qtl"]))
    best = min(opts, key=lambda o: o["total"])
    if quote is not None:
        best = {**best, "total": float(quote), "label": "USER QUOTE"}
    else:
        best["label"] = "ESTIMATE"
    best["per_qtl"] = round(best["total"] / qty_qtl, 2)
    best["km"] = round(km, 1)
    best["total"] = round(best["total"], 0)
    return best


def sell_option(price: float, qty: float, km: float, a: dict, *, delay_days=0, shrink_wk=0.0, transport_quote=None, label="") -> dict:
    """Sell in one go at a destination at `price` Rs/qtl. Shrinkage during `delay_days` (ambient) reduces saleable qty."""
    sale_qty = qty * (1 - a["transit_loss_pct"] / 100) * (1 - shrink_wk / 100 * delay_days / 7)
    revenue = sale_qty * price
    t = transport(qty, km, quote=transport_quote)
    commission = revenue * a["commission_pct"] / 100 if a["commission_payer"] == "seller" else 0.0
    handling = a["hamali_per_qtl"] * qty
    risk = revenue * a["risk_allowance_pct"] / 100
    net = revenue - t["total"] - commission - handling - risk
    return {"label": label, "price": round(price, 0), "saleable_qty": round(sale_qty, 1), "gross_revenue": round(revenue),
            "deductions": {"transport": t["total"], "commission": round(commission), "handling": round(handling), "risk_allowance": round(risk),
                           "storage": 0, "financing": 0},
            "expected_loss_qty": round(qty - sale_qty, 1), "transport": t, "net": round(net)}


def hold_option(days: int, price_future: float, price_now: float, qty: float, km_dest: float, store: dict | None,
                km_to_store: float, km_store_to_dest: float, a: dict, shrink_wk: float, price_lo: float | None = None) -> dict:
    """Hold `days` then sell. Spoilage/weight loss modelled ONLY as lower saleable qty (never also as a Rs deduction).
    store=None means farmer's own storage (no rent, ambient shrinkage)."""
    cold = store is not None and "cold" in store.get("type", "")
    shrink = shrink_wk * (a["cold_shrink_factor"] if cold else 1.0)
    sale_qty = qty * (1 - a["transit_loss_pct"] / 100) * max(0.0, 1 - shrink / 100 * days / 7)

    def net_at(p):
        revenue = sale_qty * p
        if store:
            t1, t2 = transport(qty, km_to_store, refrigerated=cold), transport(qty, km_store_to_dest, refrigerated=cold)
            transp = t1["total"] + t2["total"]
            storage = store["rate_qtl_day"] * max(days, store["min_days"]) * qty
            handling = store["handling_qtl"] * qty + a["hamali_per_qtl"] * qty
            tinfo = {"leg_to_store": t1, "leg_to_market": t2}
        else:
            t = transport(qty, km_dest)
            transp, storage, handling, tinfo = t["total"], 0.0, a["hamali_per_qtl"] * qty, {"direct": t}
        commission = revenue * a["commission_pct"] / 100 if a["commission_payer"] == "seller" else 0.0
        financing = price_now * qty * a["financing_annual_pct"] / 100 * days / 365
        risk = revenue * a["risk_allowance_pct"] / 100
        net = revenue - transp - storage - handling - commission - financing - risk
        return net, revenue, dict(transport=round(transp), storage=round(storage), handling=round(handling), commission=round(commission),
                                  financing=round(financing), risk_allowance=round(risk)), tinfo
    net, revenue, ded, tinfo = net_at(price_future)
    net_lo = net_at(price_lo)[0] if price_lo else None
    return {"days": days, "price": round(price_future), "saleable_qty": round(sale_qty, 1), "gross_revenue": round(revenue),
            "deductions": ded, "expected_loss_qty": round(qty - sale_qty, 1), "transport": tinfo, "net": round(net),
            "net_downside": round(net_lo) if net_lo is not None else None,
            "storage": store["name"] if store else "own storage"}


def p_decline(cur: float, pred: float, lo: float, hi: float) -> float:
    """P(future price < current) assuming normal with sigma from the 80% interval."""
    sigma = max((hi - lo) / (2 * 1.2816), 1e-6)
    return round(0.5 * (1 + math.erf((cur - pred) / sigma / math.sqrt(2))), 2)


def _pct(p):
    return "under 5%" if p < 0.05 else f"about {round(p * 100)}%"


def decide(sell_now: dict | None, holds: list[dict], today: date | None = None) -> dict:
    """SELL NOW / HOLD / INSUFFICIENT INFORMATION. HOLD only if expected gain beats margin and P(decline) is modest."""
    today = today or date.today()
    if not sell_now:
        return {"action": "INSUFFICIENT INFORMATION", "reason": "No current price available for the chosen crop.", "reconsider_on": str(today + timedelta(days=1))}
    margin = max(0.02 * abs(sell_now["net"]), 0)
    good = [h for h in holds if h["net"] - sell_now["net"] > margin and h["p_decline"] <= 0.40]
    if not good:
        why = ("No hold option clears the extra costs, loss and risk" if holds
               else "No reliable forecast or feasible storage for any hold window, so holding is not supported")
        return {"action": "SELL NOW", "reason": why + ".", "expected_incremental": max([h["net"] - sell_now["net"] for h in holds], default=0),
                "reconsider_on": str(today + timedelta(days=3))}
    best = max(good, key=lambda h: h["net"] - sell_now["net"])
    return {"action": "HOLD", "hold_days": best["days"], "expected_incremental": best["net"] - sell_now["net"], "p_decline": best["p_decline"],
            "reason": f"Expected net after storage, transport, loss and financing is higher by about Rs {best['net'] - sell_now['net']:,} "
                      f"with {_pct(best['p_decline'])} chance the price ends below today's. Not guaranteed.",
            "reconsider_on": str(today + timedelta(days=max(1, best["days"] // 2)))}
