from app import agent, intake, inventory


def _say(sid, *texts):
    r = None
    for t in texts:
        r = agent.handle(sid, t)
    return r


def test_lists_several_crops_asks_each_quantity_and_stores_after_confirmation():
    r = _say("m1", "", "I grow onion and tomato")
    assert [c["crop"] for c in r["crops"]] == ["onion", "tomato"] and "onion" in r["reply"].lower()  # asks quantity of the first
    r = _say("m1", "200 quintal")
    assert "tomato" in r["reply"].lower()
    r = _say("m1", "1000 kg")
    assert r["awaiting"] == "location"
    r = _say("m1", "near Niphad")
    r = _say("m1", "yes")  # ready
    r = _say("m1", "no")  # can store
    assert r["awaiting"] == "confirm" and "onion" in r["reply"].lower() and "tomato" in r["reply"].lower()
    assert inventory.load("m1") is None  # nothing stored before the farmer confirms
    r = _say("m1", "yes")
    assert r["done"] and set(inventory.load("m1")["lots"]) == {"onion", "tomato"}
    assert [c["active"] for c in r["crops"]] == [True, False]


def test_crops_and_quantities_in_one_sentence_and_hindi():
    r = _say("m2", "", "मेरे पास २०० क्विंटल प्याज और 500 किलो टमाटर है")
    assert [c["crop"] for c in r["crops"]] == ["onion", "tomato"]
    assert r["awaiting"] == "location"  # both quantities captured, so it moves on
    assert r["lang"] == "hi"


def test_returning_farmer_is_remembered_and_can_switch_crops():
    _say("m3", "", "I grow onion and potato", "100 quintal", "50 quintal", "near Niphad", "yes", "yes", "yes")
    agent.STATE.clear()
    intake.S.clear()  # new server run / new visit, same device
    r = agent.handle("m3", "")
    assert r["done"] and "remember" in r["reply"].lower() and any(a["type"] == "plan" for a in r["actions"])
    assert agent.STATE["m3"]["active"] == "onion"
    r = agent.handle("m3", "show potato")
    assert agent.STATE["m3"]["active"] == "potato" and any(a["type"] == "plan" for a in r["actions"])
    r = agent.handle("m3", "potato forecast")  # already active: just answers
    assert "forecast" in r["reply"].lower()
    r = agent.handle("m3", "which crops do I have")
    assert "onion" in r["reply"].lower() and "potato" in r["reply"].lower()


def test_adding_a_crop_later_is_saved():
    _say("m4", "", "I grow onion", "100 quintal", "near Niphad", "yes", "yes", "yes")
    agent.handle("m4", "I have 30 quintal tomato near Niphad")
    assert set(inventory.load("m4")["lots"]) == {"onion", "tomato"}


def test_start_over_forgets_the_farmer():
    _say("m5", "", "I grow onion", "100 quintal", "near Niphad", "yes", "yes", "yes")
    agent.handle("m5", "start over")
    assert inventory.load("m5") is None
    r = agent.handle("m5", "")
    assert not r.get("done")  # greets afresh


def test_unclear_answer_gets_a_gentle_reprompt_not_a_crash():
    r = _say("m6", "", "banana")
    assert not r["done"] and r["awaiting"] == "crops" and not r["crops"]


def test_reload_on_live_session_resumes_instead_of_confusing():
    _say("m7", "", "I grow onion", "100 quintal", "near Niphad", "yes", "yes", "yes")
    r = agent.handle("m7", "")  # same server, page reloaded
    assert r["done"] and any(a["type"] == "plan" for a in r["actions"]) and "did not understand" not in r["reply"]
