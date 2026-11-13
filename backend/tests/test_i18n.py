from app.agents import orchestrator
from app.core import i18n


def _plan(lang):
    return orchestrator.run({"crop": "tomato", "qty_kg": 1000, "original_qty": 10, "original_unit": "quintal",
                             "location": {"name": "Ponda", "lat": 15.40, "lon": 74.02}, "ready": True, "can_store": True, "lang": lang})


def _strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
    elif isinstance(x, str):
        yield x


def test_template_translation_keeps_params():
    assert i18n.tr("Sell at Mapusa APMC, North Goa, Goa today", "hi") == "आज Mapusa APMC, North Goa, Goa में बेचें"
    assert i18n.tr("tomato shelf life is about 7 days", "mr") == "टोमॅटो सुमारे 7 दिवसच टिकतो"
    assert i18n.tr("Pune APMC", "hi") == "Pune APMC"  # names and keys are never touched
    assert i18n.tr("Sell at X today", "en") == "Sell at X today"


def test_hindi_plan_has_no_english_template_sentences():
    p = _plan("hi")
    english = {en for en, _, _ in i18n.TEMPLATES if "{" not in en}
    leaked = [s for s in _strings({k: p[k] for k in ("options", "sell_vs_hold", "storage", "transport", "recommendation", "labels")}) if s in english]
    assert leaked == []
    assert p["sell_vs_hold"]["decision"]["action"] == "SELL NOW"  # codes stay codes
    assert p["options"][0]["destination"] in {m["name"] for m in p["mandis"]}  # mandi keys untouched (used for /api/series)
