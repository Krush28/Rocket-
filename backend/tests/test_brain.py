"""Agentic brain: the LLM only plans; Python validates arguments, runs tools, keeps yes/no gates, and rejects invented numbers."""
import pytest

from app.agents import action_agent as A
from app.conversation import intake
from app.services import llm


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    A.STATE.clear()
    intake.S.clear()
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "extract_intake", lambda *a, **k: None)


def say(db, sid, text):
    return A.handle(sid, text, None, db)


def _plan(db, sid, monkeypatch):
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: None)
    for t in ["", "onion", "50 quintal", "Niphad", "yes", "yes", "yes"]:
        r = say(db, sid, t)
    assert r["state"] == "plan"


def test_multi_intent_sentence_runs_several_tools(db, monkeypatch):
    _plan(db, "b1", monkeypatch)
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "add_crop", "args": {"crop": "brinjal", "qty": 2, "unit": "tonne"}},
                                                            {"tool": "best_mandi", "args": {}}])
    r = say(db, "b1", "bhai do ton baingan bhi hai aur batao kahan bechu")
    crops = {c["crop"]: c["qty"] for c in r["crops"]}
    assert crops.get("brinjal") == 2 and r["state"] == "plan" and any(a["type"] == "plan" for a in r["actions"])


def test_order_from_llm_still_needs_yes(db, monkeypatch):
    _plan(db, "b2", monkeypatch)
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "create_order", "args": {}}])
    r = say(db, "b2", "theek hai bech do sab")
    assert r["state"] == "confirming_action" and A.STATE["b2"]["pending"]["tool"] == "create_order"


def test_retail_needs_shop_words_and_schemes_navigate(db, monkeypatch):
    _plan(db, "b3", monkeypatch)
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "retail_price", "args": {"crop": "onion", "city": "Pune"}}])
    assert "shops" not in say(db, "b3", "pune me pyaz ka rate kya hai")["reply"]  # mandi rate, not retail
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: [{"tool": "show_schemes", "args": {}}])
    r = say(db, "b3", "sarkari yojana dikhao please abhi")
    assert {"type": "nav", "value": "schemes"}.items() <= r["actions"][-1].items()


def test_grounded_answer_rejects_invented_numbers(monkeypatch):
    monkeypatch.setattr(llm, "_gen", lambda *a, **k: '{"answer": "You will get Rs 99999 at Chandwad."}')
    assert llm.grounded_answer("how much?", "best option Chandwad net Rs 212872", "en") is None
    monkeypatch.setattr(llm, "_gen", lambda *a, **k: '{"answer": "You keep about Rs 212872 at Chandwad."}')
    assert "212872" in llm.grounded_answer("how much?", "best option Chandwad net Rs 212872", "en")


def test_free_speech_intake_fills_several_slots(db, monkeypatch):
    monkeypatch.setattr(llm, "plan_tools", lambda *a, **k: None)
    monkeypatch.setattr(llm, "extract_intake", lambda *a, **k: {"crops": [{"crop": "brinjal", "qty": 2, "unit": "tonne"}], "place": "Niphad", "ready": True})
    say(db, "b4", "")
    r = say(db, "b4", "do ton baingan hai Niphad ke paas abhi taiyar hai")
    assert {c["crop"]: c["qty"] for c in r["crops"]} == {"brinjal": 2} and r["awaiting"] == "can_store"


def test_end_to_end_sell_and_hold_with_portals(db, monkeypatch):
    """Farmer yes -> order + truck token -> transporter accepts/picks up/delivers -> farmer confirms sale; storage -> operator confirms."""
    from app.services import ops
    from app.models import Mandi, Warehouse
    _plan(db, "e1", monkeypatch)
    r = say(db, "e1", "sell it")
    assert r["state"] == "confirming_action"
    r = say(db, "e1", "yes")
    o = r["actions"][0]["order"]
    assert o["status"] == "transport_requested" and o["transport"]["id"].startswith("TR-")
    tr = ops.login(db, "9000000001", "transporter", "Sharma", None)
    u = ops.by_token(db, tr["token"])
    assert any(j["id"] == o["transport"]["id"] for j in ops.jobs_for(db, u, "open"))
    for a in ("accept", "pickup", "deliver"):
        ops.job_action(db, o["transport"]["id"], u, a)
    assert [n["title"] for n in ops.notifications(db, ["device:e1"])][:3] == ["Delivered", "Picked up", "Truck accepted"]
    say(db, "e1", "I sold it at 4100")
    r = say(db, "e1", "yes")
    assert {"type": "done"} in r["actions"] and ops.get_order(db, o["id"])["payload"]["final"]["actual_price"] == 4100
    db.add(Mandi(name="X", district="Nashik", state="Maharashtra", lat=20.0, lon=73.8))
    db.commit()
    assert ops.seed_warehouses(db) >= 2 and ops.seed_warehouses(db) == 0  # idempotent per district
    w = db.query(Warehouse).filter(Warehouse.kind == "cold").first()
    b = ops.book_storage(db, "e1", w.code, "tomato", 2000, 2)
    assert b["status"] == "requested" and b["days"] == w.min_days
    assert ops.booking_action(db, b["id"], "confirm", "op")["status"] == "confirmed"
    assert ops.notifications(db, ["device:e1"])[0]["title"] == "Storage confirmed"
