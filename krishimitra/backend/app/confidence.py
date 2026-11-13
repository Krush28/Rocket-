"""Explainable plan confidence: a score built from named, checkable signals (pattern adapted from AgroPrice-AI's confidence engine).
Weights are a transparent heuristic, NOT a calibrated probability. Every point added or removed is listed in contributors/detractors."""
import statistics

from . import demo_data as D


def assess(st: dict) -> dict:
    crop = st["profile"]["crop"]
    prices = st["prices"]
    usable = {n: p for n, p in prices.items() if not p["stale"] and not p.get("suspect")}
    score, pos, neg = 0.45, [], []

    n = len(usable)
    if n >= 5:
        score += 0.12; pos.append(f"{n} mandis with usable prices")
    elif n >= 3:
        score += 0.07; pos.append(f"{n} mandis with usable prices")
    elif n <= 1:
        score -= 0.10; neg.append("only one mandi has usable prices to compare")

    age = max((p["age_days"] for p in usable.values()), default=99)
    if age == 0:
        score += 0.05; pos.append("prices are from today")
    elif age > 3:
        score -= 0.10; neg.append(f"prices are up to {age} days old")

    hist = min((len(D.series(crop, m)) for m in usable), default=0)
    if hist >= 365:
        score += 0.15; pos.append(f"{hist} days of price history")
    elif hist >= 120:
        score += 0.08; pos.append(f"{hist} days of price history")
    elif hist < 30:
        score -= 0.12; neg.append(f"only {hist} day{'s' if hist != 1 else ''} of stored price history")

    vals = [p["modal"] for p in usable.values()]
    if len(vals) >= 3:
        cv = statistics.pstdev(vals) / (statistics.mean(vals) or 1)
        if cv < 0.12:
            score += 0.05; pos.append("mandi prices agree closely")
        elif cv > 0.40:
            score -= 0.08; neg.append("mandi prices disagree widely")

    bad = [n_ for n_, p in prices.items() if p.get("suspect")]
    if bad:
        pos.append(f"data-error guard excluded {len(bad)} suspect price(s)")

    ok_h = [h for f in st.get("forecasts", {}).values() if f.get("status") == "ok" for h in f["horizons"] if h["status"] == "ok"]
    if ok_h:
        score += 0.10; pos.append("a backtested forecast passed the reliability gate")
    else:
        score -= 0.08; neg.append("no forecast has passed the reliability gate yet")

    if not D.live_mode_on():
        score -= 0.25; neg.append("prices are DEMO DATA")

    score = round(min(0.95, max(0.05, score)), 2)
    return {"score": score, "label": "high" if score >= 0.7 else "medium" if score >= 0.5 else "low", "contributors": pos, "detractors": neg,
            "note": "Heuristic weights, not a calibrated probability."}
