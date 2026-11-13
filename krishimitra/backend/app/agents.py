"""The KRISHI-X agents. Each takes the shared `state` and returns {"data": ..., "meta": ...} (structured, no free-text claims).
Agents never calculate with an LLM: money is in costs.py, forecasts in forecast.py, pooling in logistics.py."""
from datetime import date, timedelta

import numpy as np

from . import costs, demo_data as D, forecast as F, logistics
from .geo import road_km
from .meta import meta

DEMO_SRC = f"{D.DEMO} (synthetic)"
STALE_DAYS = 7
HOLD_DAYS = [3, 7, 15, 30]


def _farm(st):
    return (st["profile"]["location"]["lat"], st["profile"]["location"]["lon"])


def _qtl(st):
    return st["profile"]["qty_kg"] / 100


def _rk(st, a, b):
    return road_km(a, b, st["assumptions"]["road_factor"])


# 2 ---------------------------------------------------------------- Mandi Discovery
def mandi_discovery(st):
    farm, out = _farm(st), []
    for name, (lat, lon, state, _) in D.MANDIS.items():
        if not D.has_data(st["profile"]["crop"], name):
            continue  # live mode: no data for this mandi -> excluded, never filled with demo values
        km = _rk(st, farm, (lat, lon))
        out.append({"name": name, "state": state, "lat": lat, "lon": lon, "distance_km": round(km, 1), "distance_label": "ESTIMATE (straight-line x road factor)",
                    "schedule": "Mon-Sat (DEMO, unverified)", "trading_status": "unknown (not verified)"})
    out = sorted([m for m in out if m["distance_km"] <= 450], key=lambda m: m["distance_km"])[:7]
    if not out:
        raise RuntimeError("no price data for this crop at any known mandi (run a data refresh)")
    st["mandis"] = {m["name"]: m for m in out}
    return {"data": out, "meta": meta(D.source_label(st["profile"]["crop"], out[0]["name"]) + "; coordinates approximate and unverified", "live" if D.live_mode_on() else "demo")}


# 4 ---------------------------------------------------------------- Price Intelligence
def price_intelligence(st):
    crop, out = st["profile"]["crop"], {}
    for name in st["mandis"]:
        df = D.series(crop, name)
        age = (date.today() - df["date"].iloc[-1].date()).days
        last3 = df["modal"].iloc[-3:]
        rec = {"mandi": name, "latest_date": str(df["date"].iloc[-1].date()), "age_days": age, "modal": float(last3.median()),
               "min": float(df["min"].iloc[-1]), "max": float(df["max"].iloc[-1]), "arrivals_t": None if np.isnan(df["arrivals_t"].iloc[-1]) else float(df["arrivals_t"].iloc[-1]),
               "avg7": round(float(df["modal"].iloc[-7:].mean())), "avg30": round(float(df["modal"].iloc[-30:].mean())),
               "trend_30d_pct": round((df["modal"].iloc[-1] / df["modal"].iloc[-30] - 1) * 100, 1) if len(df) >= 30 else None,
               "history": [[str(d.date()), float(v)] for d, v in zip(df["date"].iloc[-90:], df["modal"].iloc[-90:])],
               "stale": age > STALE_DAYS, "unit": "Rs/quintal", "price_basis": "median of last 3 observed modal prices",
               "meta": meta(D.source_label(crop, name), "live" if D.live_mode_on() else "demo", updated=D.last_updated(crop, name))}
        out[name] = rec
    st["prices"] = out
    # retail = consumer-market context ONLY, never a farmer price
    base = float(np.mean([p["avg7"] for p in out.values()]))
    retail = [{"city": c, "retail_price": round(base * (1 + mk)), "unit": "Rs/quintal-equivalent",
               "spread_vs_wholesale_pct": round(mk * 100), "note": "Consumer price context. NOT what a farmer receives."} for c, mk in D.RETAIL_CITIES.items()]
    return {"data": {"mandis": out, "retail_context": retail}, "meta": meta(DEMO_SRC, "demo")}


def market_activity(st):
    out = {}
    for name in st["mandis"]:
        a = D.series(st["profile"]["crop"], name)["arrivals_t"]
        if a.isna().all():
            out[name] = {"arrivals_7d_t": None, "arrivals_30d_t": None, "change_pct": None, "signal": "arrivals not available from this source"}
            continue
        r7, r30 = float(a.iloc[-7:].mean()), float(a.iloc[-30:].mean())
        ch = (r7 / r30 - 1) * 100
        out[name] = {"arrivals_7d_t": round(r7, 1), "arrivals_30d_t": round(r30, 1), "change_pct": round(ch),
                     "signal": "arrivals rising (price pressure down)" if ch > 10 else "arrivals falling (price support up)" if ch < -10 else "arrivals steady"}
    return {"data": out, "meta": meta(DEMO_SRC + " arrivals", "demo", note="Arrivals are demo values, not a live feed.")}


# 3 ---------------------------------------------------------------- Buyer Discovery
def buyer_discovery(st):
    if D.live_mode_on():  # never mix invented offers with real prices
        return {"data": [], "meta": meta("none", "unverified", note="No real buyer offers are connected. Demo buyers are hidden in LIVE mode.")}
    crop, qtl, farm, out = st["profile"]["crop"], _qtl(st), _farm(st), []
    base = np.mean([p["avg7"] for p in st["prices"].values()])
    for b in D.BUYERS:
        if b["crop"] != crop:
            continue
        km = _rk(st, farm, (b["lat"], b["lon"]))
        rec = {"id": b["id"], "name": b["name"], "kind": b["kind"], "distance_km": round(km, 1), "min_qty_qtl": b["qty_min"], "grade": b["grade"],
               "pickup": b["pickup"], "meets_min_qty": qtl >= b["qty_min"], "phone": None, "verification": "unverified (demo)"}
        if b["kind"] == "offer":
            rec.update(price=round(base * (1 + b["price_offset"])), valid_until=str(date.today() + timedelta(days=2)),
                       label="DEMO OFFER - illustrative, not a real buyer")
        else:
            rec.update(price=None, label="INDICATIVE DEMAND - interest only, no price committed")
        out.append(rec)
    return {"data": out, "meta": meta(DEMO_SRC, "demo", note="No real buyer offers are connected yet.")}


# 7 ---------------------------------------------------------------- Cold Storage
def cold_storage(st):
    crop, farm, qtl, out = st["profile"]["crop"], _farm(st), _qtl(st), []
    for w in D.WAREHOUSES:
        if crop not in w["crops"]:
            continue
        km = _rk(st, farm, (w["lat"], w["lon"]))
        if km > 200:
            continue
        out.append({**{k: w[k] for k in ("id", "name", "lat", "lon", "type", "temp", "rate_qtl_day", "min_days", "handling_qtl")},
                    "distance_km": round(km, 1), "declared_capacity_qtl": w["capacity_qtl"], "available_capacity_qtl": None,
                    "availability": "UNCONFIRMED - send an enquiry; operator must confirm", "phone": None, "verification": "unverified (demo)",
                    "est_cost_7d": round(w["rate_qtl_day"] * max(7, w["min_days"]) * qtl + w["handling_qtl"] * qtl), "cost_label": "ESTIMATE",
                    "crop_suitable": True})
    return {"data": sorted(out, key=lambda w: w["rate_qtl_day"]), "meta": meta(DEMO_SRC, "demo")}


# 8 ---------------------------------------------------------------- Transport
def _net_now_rows(st):
    rows = []
    for name, p in st["prices"].items():
        if p["stale"]:
            continue
        km = st["mandis"][name]["distance_km"]
        rows.append((name, costs.sell_option(p["modal"], _qtl(st), km, st["assumptions"], label=name)))
    return sorted(rows, key=lambda r: -r[1]["net"])


def transport_agent(st):
    qtl, out = _qtl(st), []
    for name, m in list(st["mandis"].items())[:4]:
        t = costs.transport(qtl, m["distance_km"])
        out.append({"destination": name, "distance_km": m["distance_km"], "est_hours": round(m["distance_km"] / 40, 1), **t,
                    "options": [{"transporter": v["name"], "vehicle": v["vehicle"], "capacity_qtl": v["capacity_qtl"], "phone": None,
                                 "verification": "unverified (demo)", "quote_status": "ESTIMATE - no quote requested",
                                 "total": round(-(-qtl // v["capacity_qtl"]) * (v["base"] + v["per_km"] * m["distance_km"])),
                                 "per_qtl": round(-(-qtl // v["capacity_qtl"]) * (v["base"] + v["per_km"] * m["distance_km"]) / qtl, 1)}
                                for v in D.TRANSPORTERS if not v["refrigerated"]]})
    return {"data": out, "meta": meta(DEMO_SRC + " rate card", "estimate", note="Rates are unverified placeholders.")}


def shared_load(st):
    rows = _net_now_rows(st)
    if not rows:
        return {"data": {"status": "no_match", "reason": "No fresh price data."}, "meta": meta(DEMO_SRC, "demo", error="no fresh prices")}
    dest = rows[0][0]
    m = st["mandis"][dest]
    pool = logistics.simulated_pool(st["profile"]["crop"], dest, (m["lat"], m["lon"]), _farm(st), factor=st["assumptions"]["road_factor"])
    res = logistics.match(_qtl(st), m["distance_km"], pool)
    res["destination"] = dest
    st["shared"] = res
    return {"data": res, "meta": meta("OR-Tools CP-SAT on SIMULATED pool", "demo", note="Pool members are simulated; no real coordination claimed.")}


# 5 ---------------------------------------------------------------- Price Forecast
def price_forecast(st):
    crop, out = st["profile"]["crop"], {}
    cands = [n for n, _ in _net_now_rows(st)[:3]]
    for n in cands:
        out[n] = F.forecast(crop, n)
    st["forecasts"] = out
    return {"data": out, "meta": meta(DEMO_SRC + " + ETS / lag-Ridge / baselines", "demo",
                                      note="Backtested on a synthetic series: accuracy here says nothing about real mandis.")}


# 6 ---------------------------------------------------------------- Sell now vs Hold
def sell_vs_hold(st):
    crop, qtl, a, prof = st["profile"]["crop"], _qtl(st), st["assumptions"], st["profile"]
    rows = _net_now_rows(st)
    if not rows:
        d = costs.decide(None, [])
        return {"data": {"decision": d}, "meta": meta("costs.py", "estimate", error="no fresh price")}
    dest, sell = rows[0]
    cprops = D.CROPS[crop]
    fc = st["forecasts"].get(dest, {})
    holds, skipped = [], []
    farm, m = _farm(st), st["mandis"][dest]
    stores = [None] if prof["can_store"] else []
    stores += [w for w in st["storage"]]
    for days in HOLD_DAYS:
        if days > cprops["max_hold_days"]:
            skipped.append({"days": days, "why": f"{crop} shelf life is about {cprops['max_hold_days']} days"})
            continue
        h = F.horizon(fc, days) if fc.get("status") == "ok" else None
        if not h or h["status"] != "ok":
            skipped.append({"days": days, "why": "no reliable forecast for this horizon" if h else "insufficient data"})
            continue
        best = None
        for store in stores:
            if store is None and days > cprops["cold_after_days"]:
                continue  # own ambient storage unsuitable for this crop/duration
            opt = costs.hold_option(days, h["predicted"], sell["price"], qtl, m["distance_km"], store,
                                    _rk(st, farm, (store["lat"], store["lon"])) if store else 0,
                                    _rk(st, (store["lat"], store["lon"]), (m["lat"], m["lon"])) if store else 0,
                                    a, cprops["shrink_wk"], price_lo=h["lo"])
            if best is None or opt["net"] > best["net"]:
                best = opt
        if best is None:
            skipped.append({"days": days, "why": "no suitable storage"})
            continue
        best.update(p_decline=costs.p_decline(sell["price"], h["predicted"], h["lo"], h["hi"]), forecast=h, destination=dest,
                    incremental=best["net"] - sell["net"], confidence=h["confidence"])
        holds.append(best)
    decision = costs.decide(sell, holds)
    return {"data": {"destination": dest, "sell_now": sell, "holds": holds, "skipped": skipped, "decision": decision,
                     "formulas": {"sell_now": "revenue - transport - handling - other selling costs",
                                  "hold": "future revenue (qty reduced by weight loss/spoilage, not double counted) - storage - handling - transport - financing"}},
            "meta": meta("costs.py (deterministic)", "estimate", confidence=decision.get("action"))}


# 11 --------------------------------------------------------------- Net Realization
def net_realization(st):
    a, qtl, farm, opts = st["assumptions"], _qtl(st), _farm(st), []
    sh = st["sellhold"]
    for name, o in _net_now_rows(st):
        p = st["prices"][name]
        opts.append(_opt("mandi_now", f"Sell at {name} today", name, o, st["mandis"][name]["distance_km"], "today / next market day", None, p["age_days"],
                         ["Modal price is not a guaranteed price for your lot", "Transport is an ESTIMATE"]))
    for b in st["buyers"]:
        if b["kind"] != "offer" or not b["meets_min_qty"]:
            continue
        a2 = {**a, "commission_pct": 0.0}
        o = costs.sell_option(b["price"], qtl, b["distance_km"], a2, transport_quote=0.0 if b["pickup"] == "buyer collects" else None, label=b["name"])
        if b["pickup"] == "buyer collects":
            o["transport"]["label"] = "BUYER COLLECTS"
        opts.append(_opt("direct_buyer", f"Direct sale to {b['name']}", b["name"], o, b["distance_km"], "1-2 days", None, 0,
                         ["DEMO OFFER: not a real buyer", f"Offer valid until {b['valid_until']}", "Quality grading may change the price"]))
    for h in sh.get("holds", []):
        low = h["net_downside"]
        o = {**h, "gross_revenue": h["gross_revenue"]}
        opts.append(_opt("hold", f"Hold {h['days']} days ({h['storage']}), sell at {h['destination']}", h["destination"], o, st["mandis"][h["destination"]]["distance_km"],
                         f"in {h['days']} days", h["confidence"], st["prices"][h["destination"]]["age_days"],
                         [f"{costs._pct(h['p_decline'])} chance price ends below today's", "Forecast is not a guarantee", "Storage availability must be confirmed"],
                         downside=low, tr=sum(t["total"] for t in h["transport"].values())))
    shr = st.get("shared", {})
    if shr.get("status") == "ok" and shr["you"]["saving"] > 0:
        base = next((o for o in opts if o["type"] == "mandi_now" and o["destination"] == shr["destination"]), None)
        if base:
            o = dict(base)
            o["type"], o["label"] = "shared_transport", f"Sell at {shr['destination']} with shared truck"
            o["transport_cost"] = shr["you"]["pooled"]
            o["net"] = base["net"] + shr["you"]["saving"]
            o["deductions"] = {**base["deductions"], "transport": shr["you"]["pooled"]}
            o["total_deductions"] = sum(o["deductions"].values())
            o["risks"] = ["Pool members are SIMULATED; needs real coordination", *base["risks"]]
            o["score"] = o["net"]
            opts.append(o)
    opts.sort(key=lambda o: -o["score"])
    for i, o in enumerate(opts, 1):
        o["rank"] = i
    st["options"] = opts
    nearest = min(st["mandis"], key=lambda n: st["mandis"][n]["distance_km"])
    ref = next((o for o in opts if o["type"] == "mandi_now" and o["destination"] == nearest), None)
    return {"data": {"options": opts, "reference_nearest_mandi_now": ref["net"] if ref else None,
                     "formula": "net = revenue - transport - handling - storage - financing - commission (if seller pays) - risk allowance; losses via lower saleable qty",
                     "rank_rule": f"score = expected net - {costs.RISK_LAMBDA} x (expected net - downside net) for forecast-dependent options"},
            "meta": meta("costs.py (deterministic)", "estimate")}


def _opt(kind, label, dest, o, km, when, conf, age, risks, downside=None, tr=None):
    ded = o["deductions"]
    tot = sum(ded.values())
    net = o["net"]
    pen = costs.RISK_LAMBDA * max(0, net - downside) if downside is not None else 0
    return {"type": kind, "label": label, "destination": dest, "price": o["price"], "saleable_qty": o["saleable_qty"], "gross_revenue": o["gross_revenue"],
            "deductions": ded, "total_deductions": tot, "net": net, "net_downside": downside, "score": round(net - pen), "distance_km": km,
            "transport_cost": tr if tr is not None else ded.get("transport"), "expected_selling_time": when, "forecast_confidence": conf or "n/a (current price)",
            "data_freshness_days": age, "expected_loss_qty": o["expected_loss_qty"], "risks": risks, "verification": "LIVE PRICE / ESTIMATED COSTS" if (D.live_mode_on() and kind != "direct_buyer") else "DEMO DATA / ESTIMATE",
            "hold_days": o.get("days")}


# 12 --------------------------------------------------------------- Recommendation
def recommendation(st):
    opts = st["options"]
    if not opts:
        return {"data": {"status": "insufficient_information"}, "meta": meta("recommendation", "estimate", error="no feasible options")}
    best, sh = opts[0], st["sellhold"]["decision"]
    near = st["net"]["reference_nearest_mandi_now"]
    top_mandi_now = next((o for o in opts if o["type"] == "mandi_now"), None)
    hi_modal = max(st["prices"].values(), key=lambda p: p["modal"])["mandi"]
    notes = []
    if top_mandi_now and top_mandi_now["destination"] != hi_modal:
        notes.append(f"{hi_modal} shows the highest modal price, but after transport and handling it is not the best net option.")
    answers = {
        "q1_current_prices": {n: {"modal": p["modal"], "min": p["min"], "max": p["max"], "age_days": p["age_days"]} for n, p in st["prices"].items()},
        "q2_best_net": {"option": best["label"], "net": best["net"]},
        "q3_direction": {n: {"trend_30d_pct": f["trend_30d_pct"], "reliable_horizons": [h["horizon_days"] for h in f["horizons"] if h["status"] == "ok"]}
                         for n, f in st["forecasts"].items() if f.get("status") == "ok"},
        "q4_sell_or_hold": sh,
        "q5_logistics": {"storage": [w["name"] for w in st["storage"][:2]], "transport": st["transport"][0]["vehicle"] if st["transport"] else None},
    }
    facts = {"best": best["label"], "net_rs": best["net"], "sell_or_hold": sh["action"], "reason": sh["reason"], "notes": notes}
    from . import llm
    text = llm.explain(facts, st["profile"].get("lang", "en")) or (
        f"Best estimated net: {best['label']} - about Rs {best['net']:,} after about Rs {round(best['total_deductions']):,} of costs. "
        f"Sell vs hold: {sh['action']}. {sh['reason']} " + " ".join(notes))
    return {"data": {"best": best, "decision": sh, "answers": answers, "estimated_gain_vs_nearest_mandi_today": (best["net"] - near) if near is not None else None,
                     "gain_note": "Model-estimated versus selling at the nearest mandi today. Not a measured result.",
                     "explanation": text, "explanation_by": "local LLM" if llm.enabled() else "template", "reconsider_on": sh["reconsider_on"]},
            "meta": meta("recommendation agent", "estimate", confidence=best["forecast_confidence"])}
