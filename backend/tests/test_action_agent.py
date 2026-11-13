"""Voice action agent + multi-crop intake + farmer memory (ported from Rocket's test_agent / test_multicrop)."""
import pytest

from app.agents import action_agent as A
from app.conversation import intake
from app.services import llm


@pytest.fixture(autouse=True)
def _clean():
    A.STATE.clear()
    intake.S.clear()


def say(db, sid, text, lang=None):
    return A.handle(sid, text, lang, db)


def _onboard(db, sid):
    say(db, sid, "")
    for t in ["I grow onion and tomato", "50 quintal", "1000 kg", "near Niphad", "yes", "no"]:
        r = say(db, sid, t)
    return r


def test_multi_crop_intake_asks_each_quantity_then_confirms(db):
    assert "crops" in say(db, "m1", "")["reply"]
    r = say(db, "m1", "I grow onion and tomato")
    assert r["awaiting"] == "qty" and "onion" in r["reply"] and [c["crop"] for c in r["crops"]] == ["onion", "tomato"]
    assert "tomato" in say(db, "m1", "50 quintal")["reply"]
    assert say(db, "m1", "1000 kg")["awaiting"] == "location"
    say(db, "m1", "near Niphad")
    say(db, "m1", "yes")
    r = say(db, "m1", "no")
    assert r["awaiting"] == "confirm" and not r.get("done") and not r["actions"]  # nothing runs before the yes
    r = say(db, "m1", "yes")
    assert r["done"] and r["actions"][0]["type"] == "plan" and r["state"] == "plan"


def test_hindi_two_crops_in_one_sentence(db):
    say(db, "h1", "")
    r = say(db, "h1", "मेरे पास 10 क्विंटल प्याज और 5 क्विंटल टमाटर है")
    assert r["lang"] == "hi" and r["awaiting"] == "location" and "खेत" in r["reply"]
    assert {c["crop"]: c["qty"] for c in r["crops"]} == {"onion": 10, "tomato": 5}


def test_returning_farmer_remembered_after_restart_and_can_switch(db):
    _onboard(db, "r1")
    say(db, "r1", "yes")
    A.STATE.clear()
    intake.S.clear()  # server restart
    r = say(db, "r1", "")
    assert r["done"] and "Welcome back" in r["reply"] and r["actions"][0]["type"] == "plan"
    r = say(db, "r1", "show my tomato")
    assert next(c for c in r["crops"] if c["active"])["crop"] == "tomato"


def test_actions_compare_order_with_confirmation_and_track(db):
    _onboard(db, "a1")
    say(db, "a1", "yes")
    r = say(db, "a1", "where should I sell")
    assert "Best option" in r["reply"] and {"type": "tab", "value": "compare"} in r["actions"]
    r = say(db, "a1", "create the order")
    assert r["state"] == "confirming_action" and "yes or no" in r["reply"]
    assert say(db, "a1", "no")["reply"].startswith("Okay")
    say(db, "a1", "create the order")
    r = say(db, "a1", "yes")
    assert "created" in r["reply"] and r["actions"][0]["type"] == "order"
    assert "created" in say(db, "a1", "track my order")["reply"]


def test_cost_change_validated(db):
    _onboard(db, "c1")
    say(db, "c1", "yes")
    assert "recalculated" in say(db, "c1", "set hamali to 15")["reply"]
    assert "cannot change" in say(db, "c1", "set road factor to 50")["reply"]


def test_hindi_commands_answer_in_hindi(db):
    say(db, "hh", "")
    for t in ["मेरे पास 10 क्विंटल प्याज है", "निफाड", "हाँ", "नहीं", "हाँ"]:
        r = say(db, "hh", t)
    assert r["done"] and r["lang"] == "hi"
    r = say(db, "hh", "भाव अनुमान दिखाओ")
    assert "अनुमान" in r["reply"] and r["lang"] == "hi"
    r = say(db, "hh", "कहाँ बेचूँ")
    assert "सबसे अच्छा विकल्प" in r["reply"]


def test_rules_first_llm_not_called_when_rules_understand(db, monkeypatch):
    _onboard(db, "f1")
    say(db, "f1", "yes")
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "pick_tool", lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM called on the fast path")))
    assert "Best option" in say(db, "f1", "where should I sell")["reply"]


def test_llm_plan_is_validated_and_executed_by_python(db, monkeypatch):
    _onboard(db, "f2")
    say(db, "f2", "yes")
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "order_event", "args": {}}])  # not a brain tool -> ignored
    assert "did not understand" in say(db, "f2", "blah blah")["reply"]
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "sell_or_hold", "args": {}}])
    assert "SELL NOW" in say(db, "f2", "kuch bhi batao")["reply"] or "HOLD" in say(db, "f2", "kuch bhi")["reply"]


def test_start_over_forgets_farmer(db):
    _onboard(db, "s1")
    say(db, "s1", "yes")
    assert say(db, "s1", "start over")["actions"] == [{"type": "reset"}]
    A.STATE.clear()
    assert "crops" in say(db, "s1", "")["reply"]  # asked again, not remembered
