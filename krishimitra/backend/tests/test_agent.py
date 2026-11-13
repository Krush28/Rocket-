import pytest

from app import agent, orders, profile as P


def _agent_with_plan(sid="a1"):
    agent.STATE.clear()
    P.SESSIONS.clear()
    for t in ("", "I have 200 quintals of onion near Niphad", "yes", "yes", "yes"):
        r = agent.handle(sid, t)
    assert r["done"] and any(a["type"] == "plan" for a in r["actions"])
    return agent


def test_agent_routes_free_form_requests_to_tools():
    a = _agent_with_plan()
    st = a.STATE["a1"]
    cases = {"show me the forecast": "forecast", "where should I sell": "compare", "should I hold or sell now": "explain_decision",
             "what about storage": "logistics", "how sure are you": "confidence", "सबसे अच्छा कहाँ बेचूँ": "compare", "भाव अनुमान दिखाओ": "forecast",
             "book transport": "order_event", "create the order": "create_order", "gibberish xyz": "unknown"}
    for text, tool in cases.items():
        assert a.route(text, "en", st)[0] == tool, text


def test_agent_acts_and_confirms_before_consequences(tmp_path, monkeypatch):
    monkeypatch.setattr(orders, "DB", tmp_path / "o.db")
    a = _agent_with_plan()
    r = a.handle("a1", "show me the forecast")
    assert {"type": "tab", "value": "forecast"} in r["actions"] and "forecast" in r["reply"].lower()
    r = a.handle("a1", "create the order")  # must ask first, not act
    assert r["chips"] == ["Yes", "No"] and not r["actions"] and orders.list_all() == []
    a.handle("a1", "no")
    assert orders.list_all() == []
    a.handle("a1", "create the order")
    r = a.handle("a1", "yes")
    assert len(orders.list_all()) == 1 and any(x["type"] == "order" for x in r["actions"])
    a.handle("a1", "book transport")
    a.handle("a1", "yes")
    assert orders.list_all()[0]["status"] == "transport_requested"


def test_agent_changes_costs_and_rejects_unsafe_settings():
    a = _agent_with_plan()
    before = a.STATE["a1"]["plan"]["recommendation"]["best"]["net"]
    r = a.handle("a1", "set hamali to 40")
    assert any(x["type"] == "plan" for x in r["actions"]) and a.STATE["a1"]["plan"]["recommendation"]["best"]["net"] < before
    assert "cannot" in a.run_tool("set_assumption", {"__class__": 1}, a.STATE["a1"], "en")["reply"]
    assert "cannot" in a.run_tool("set_assumption", {"commission_pct": -5}, a.STATE["a1"], "en")["reply"]


def test_agent_new_lot_midway_and_language_switch():
    a = _agent_with_plan()
    a.handle("a1", "I have 50 quintal potato near Pune")
    plan = a.STATE["a1"]["plan"]
    assert plan["profile"]["crop"] == "potato" and plan["profile"]["qty_kg"] == 5000
    r = a.handle("a1", "speak in Hindi")
    assert {"type": "lang", "value": "hi"} in r["actions"]


def test_agent_needs_a_lot_before_acting():
    agent.STATE.clear()
    P.SESSIONS.clear()
    r = agent.handle("fresh", "show me the forecast")  # no plan yet -> intake, never a crash, never an action
    assert not r["actions"] and r.get("state") == "collecting"
