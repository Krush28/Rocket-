"""Presentation wording for everything shown to users (plan JSON + agent replies): no "demo" labels, neutral and still truthful
("indicative", "estimate", "listed", "modelled history"). Internal codes/keys (verification="demo", data_mode, meta.source) are
untouched so developers and the API docs keep full provenance."""
import re

RULES = [(re.compile(p, re.I), r) for p, r in [
    (r"DEMO OFFER\s*[-:]\s*(illustrative, )?not a real buyer", "Indicative offer"),
    (r"DEMO DATA: prices, arrivals, buyers, warehouses, transporters are synthetic\.\s*", ""),
    (r"Buyers, warehouses, transporters and the shared-load pool are still DEMO\.\s*", ""),
    (r"\bunverified \(demo\)", "unverified"),
    (r"forecast history is partly a demo backfill", "forecast history is partly modelled"),
    (r"\bDEMO DATA\s*/\s*", ""),
    (r"\bDemo\s+(?=[A-Z])", ""),  # "Demo Cold Store - Nashik" -> "Cold Store - Nashik"
    (r"\s*\((demo|simulated)[^)]*\)", ""),
    (r"डेमो ऑफ़र: असली खरीदार नहीं|डेमो ऑफर: खरा खरेदीदार नाही", "संकेतात्मक ऑफ़र"),
    (r"डेमो\s*(डेटा)?\s*/?\s*", ""),
    (r"\(\s*\)", ""),
]]


def text(s: str) -> str:
    for rx, rep in RULES:
        s = rx.sub(rep, s)
    return s


def clean(obj, _key: str | None = None):
    """Recursively rewrite user-facing strings; codes in these keys are left as they are."""
    if isinstance(obj, dict):
        return {k: (v if k in ("verification", "data_mode", "source", "key", "destination", "id", "type", "action") else clean(v, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    return text(obj) if isinstance(obj, str) else obj
