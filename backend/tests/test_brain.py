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


def test_restart_mid_conversation_restores_farmer_and_open_order(db, monkeypatch):
    _plan(db, "r1", monkeypatch)
    say(db, "r1", "sell it")
    oid = say(db, "r1", "yes")["actions"][0]["order"]["id"]
    A.STATE.clear()  # backend restart: in-memory plans are gone
    r = say(db, "r1", "track my order")
    assert oid in r["reply"] and r["state"] == "plan"


# ---------------------------------------------------------------- cloud brain, memory, scheme filters
def test_schemes_by_state_kind_and_name():
    from app.services import schemes as SC
    assert SC.parse("show me bima yojana of punjab") == {"state": "Punjab", "category": "insurance"}
    assert SC.parse("तेलंगाना की बीमा योजना दिखाओ") == {"state": "Telangana", "category": "insurance"}
    assert SC.parse("solar pump subsidy")["q"] == "pm-kusum" and "state" not in SC.parse("solar pump subsidy")  # "pump" is not "MP"
    ins = SC.for_state("Telangana", "en", "insurance")["schemes"]
    assert {s["id"] for s in ins} == {"pmfby", "rwbcis", "tg-rythu-bima"} and all(s["category"] == "insurance" for s in ins)
    assert [s["id"] for s in SC.for_state("Punjab", "en", None, "pm-kisan")["schemes"]] == ["pm-kisan"]
    reply, flt = SC.say("Goa", "en", "storage")  # no state-specific scheme: central ones still answer, nothing invented
    assert "Operation Greens" in reply and flt["category"] == "storage"
    assert all(s[4].startswith("https://") and set(s[5]) == {"en", "hi", "mr"} for s in SC.S)


def test_agent_opens_exactly_the_scheme_asked_for_without_any_llm(db):
    from app.agents import action_agent as A
    r = A.handle("sch1", "punjab ki bima yojana dikhao", None, db)
    nav = r["actions"][-1]
    assert (nav["type"], nav["state"], nav["cat"]) == ("nav", "Punjab", "insurance") and "Fasal Bima" in r["reply"] and r["ai"] == "rules"
    r = A.handle("sch1", "PM kisan dikhao", None, db)
    assert r["actions"][-1]["q"] == "pm-kisan" and "6,000" in r["reply"]


def test_cloud_model_is_used_first_then_paused_after_a_failure(monkeypatch):
    from app.services import llm
    monkeypatch.setenv("KRISHIMITRA_LLM", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_cloud_down_until", 0.0)
    seen = {}

    class Ok:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"calls": [{"tool": "forecast", "args": {}}]}'}]}}]}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers)
        return Ok()
    monkeypatch.setattr(llm.httpx, "post", post)
    assert llm.provider() == "cloud" and llm.plan_tools("bhav badhega kya", {}) == [{"tool": "forecast", "args": {}}]
    assert "test-key" not in seen["url"] and seen["headers"]["x-goog-api-key"] == "test-key"  # the key never goes in the URL

    def boom(*a, **k):
        raise llm.httpx.ConnectError("down")
    monkeypatch.setattr(llm.httpx, "post", boom)
    assert llm.plan_tools("bhav badhega kya", {}) is None and llm.provider() == "rules"  # paused: the rules answer at once


def test_recent_turns_reach_the_model_and_long_sentences_go_to_the_cloud_brain(db, monkeypatch):
    from app.agents import action_agent as A, brain
    from app.services import llm
    for t in ["", "I have 50 quintal onion near Niphad", "yes", "no", "yes"]:
        r = A.handle("mem1", t, None, db)
    assert r["state"] == "plan"
    monkeypatch.setattr(llm, "provider", lambda: "cloud")
    monkeypatch.setattr(llm, "enabled", lambda: True)
    got = {}

    def plan(text, ctx):
        got.update(ctx)
        return [{"tool": "best_mandi", "args": {}}]
    monkeypatch.setattr(llm, "plan_tools", plan)
    assert brain.wants_brain("which mandi gives me the most money", "compare") and not brain.wants_brain("commission 3 percent please now", "set_assumption")
    A.handle("mem1", "which mandi gives me the most money", None, db)
    A.handle("mem1", "and what about the second one there", None, db)
    assert "which mandi gives me the most money" in got["recent"]
