"""Transit spoilage risk.
risk = (transit_hours / remaining_shelf_life_hours) x temperature_multiplier, capped at 1. A risk FLAG used for ranking and warnings,
not a rupee deduction (weight loss is already modelled once as lower saleable quantity, so spoilage is never double counted)."""

SHELF_LIFE_H = {"onion": (120, 240), "tomato": (48, 96), "potato": (168, 504)}  # fresh produce (min, max) hours; we use the conservative min
HANDLING_H = 2.0  # loading/unloading/queueing added to driving time
AVG_KMH = 40.0
TIERS = [(0.20, "SAFE"), (0.40, "MODERATE"), (0.60, "HIGH"), (1.01, "CRITICAL")]


def temp_multiplier(c: float) -> float:
    return 0.6 if c < 20 else 1.0 if c < 30 else 1.4 if c < 35 else 2.0


def level(p: float) -> str:
    return next(name for cap, name in TIERS if p < cap)


def assess(crop: str, km: float, temp_c: float = 28.0, age_days: float = 0.0, refrigerated: bool = False) -> dict:
    life = SHELF_LIFE_H[crop][0]
    remaining = max(life - age_days * 24, 1.0)
    hours = km / AVG_KMH + HANDLING_H
    p = min(1.0, hours / remaining * temp_multiplier(temp_c) * (0.4 if refrigerated else 1.0))
    return {"probability": round(p, 3), "level": level(p), "transit_hours": round(hours, 1), "assumed_temp_c": temp_c,
            "note": "Heuristic flag from transit time vs shelf life; ambient temperature is an assumption."}
