from app.agents import action_agent as A
from app.services import dashboard as D, ops


def _farmer(db, sid):
    for t in ["", "I have 50 quintal onion and 20 quintal tomato near Niphad", "yes", "no", "yes"]:
        r = A.handle(sid, t, None, db)
    assert r["state"] == "plan"


def test_dashboard_has_crops_forecast_tickets_chat_and_no_invented_phone(db):
    _farmer(db, "dash1")
    A.handle("dash1", "create the order", None, db)
    A.handle("dash1", "yes", None, db)
    d = D.build(db, "dash1", "en", A.STATE["dash1"])
    assert [c["crop"] for c in d["crops"]] == ["onion", "tomato"] and d["totals"]["expected_net"] > 0
    assert all(c["best"]["net"] > 0 and c["decision"]["action"] for c in d["crops"])
    assert d["orders"] and d["orders"][0]["contact"] is None  # nobody accepted yet: no phone number shown
    assert all(o["phone"] is None for c in d["crops"] for o in c["transport"]["options"])  # listed fleets never get a made-up number
    assert d["chat"][-1]["u"] == "yes" and len(d["chat"]) >= 6


def test_transporter_phone_appears_only_after_they_accept(db):
    _farmer(db, "dash2")
    A.handle("dash2", "create the order", None, db)
    A.handle("dash2", "yes", None, db)
    o = D.build(db, "dash2", "en", A.STATE["dash2"])["orders"][0]
    if not o["transport"]:
        A.handle("dash2", "book transport", None, db)
        A.handle("dash2", "yes", None, db)
        o = D.build(db, "dash2", "en", A.STATE["dash2"])["orders"][0]
    u = ops.by_token(db, ops.login(db, "9800000001", "transporter", "Sai Transport", "Maharashtra")["token"])
    ops.job_action(db, o["transport"]["id"], u, "accept")
    c = D.build(db, "dash2", "en", A.STATE["dash2"])["orders"][0]["contact"]
    assert c["phone"] == "9800000001" and c["name"] == "Sai Transport" and "not verified" in c["note"].lower()


def test_agent_opens_dashboard_sections_by_voice(db):
    _farmer(db, "dash3")
    for text, sec in [("show my tickets", "tickets"), ("मेरा हिसाब दिखाओ", "home"), ("transporter ka phone number dikhao", "transport"),
                      ("माझी साठवण बुकिंग दाखवा", "storage")]:
        nav = [a for a in A.handle("dash3", text, None, db)["actions"] if a["type"] == "nav"]
        assert nav and nav[0]["value"] == "dashboard" and nav[0]["section"] == sec, (text, nav)
    assert A.route("book transport")[0] == "order_event"  # commands still act; only "show" phrases open the dashboard


def test_dashboard_for_a_new_device_is_empty_not_an_error(db):
    d = D.build(db, "nobody", "hi")
    assert d["farmer"] is None and d["crops"] == [] and d["orders"] == []
