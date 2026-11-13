"""Regressions found by the black-box voice QA run (2026-11-13): editing crops after the plan, routing, yes/no words, units,
language stickiness, and the offline gazetteer (villages, pincodes, Devanagari, Marathi oblique forms)."""
import pytest

from app.agents import action_agent as A
from app.conversation import intake, profile_agent as P
from app.services import gazetteer as G


@pytest.fixture(autouse=True)
def _clean():
    A.STATE.clear()
    intake.S.clear()
    G.clear()


def say(db, sid, text, lang=None):
    return A.handle(sid, text, lang, db)


def _plan(db, sid, lang=None):
    for t in ["", "onion", "50 quintal", "Niphad", "yes", "yes", "yes"]:
        r = say(db, sid, t, lang)
    assert r["state"] == "plan"
    return r


def _crops(r):
    return {c["crop"]: c["qty"] for c in r["crops"]}


def test_add_more_crops_after_confirmation(db):
    _plan(db, "a1")
    assert "Which crop" in say(db, "a1", "add more crops")["reply"]
    assert "How much potato" in say(db, "a1", "potato")["reply"]
    r = say(db, "a1", "20")  # bare number: the farmer's last unit (quintal)
    assert _crops(r) == {"onion": 50, "potato": 20} and r["actions"][0]["type"] == "plan"


def test_add_crop_name_then_amount_and_one_sentence_forms(db):
    _plan(db, "a2")
    assert "How much tomato" in say(db, "a2", "add tomato")["reply"]
    assert _crops(say(db, "a2", "10 quintal")) == {"onion": 50, "tomato": 10}
    assert _crops(say(db, "a2", "I also have 20 quintal potato"))["potato"] == 20


def test_remove_lot_and_keep_the_last_one(db):
    _plan(db, "a3")
    say(db, "a3", "I have 20 quintal potato")
    r = say(db, "a3", "remove potato")
    assert _crops(r) == {"onion": 50} and r["crops"][0]["active"]
    assert "only crop" in say(db, "a3", "delete onion")["reply"]


def test_change_quantity_and_place_after_plan(db, monkeypatch):
    _plan(db, "a4")
    r = say(db, "a4", "actually it is 80 quintal")
    assert _crops(r) == {"onion": 80} and r["actions"][0]["plan"]["profile"]["qty_kg"] == 8000
    monkeypatch.setattr(P, "_geocode", lambda db, t: {"name": "Pune", "lat": 18.52, "lon": 73.86, "status": "approximate"})
    r = say(db, "a4", "my farm is near Pune")
    assert "Pune" in r["reply"] and r["actions"][0]["plan"]["profile"]["location"]["name"] == "Pune"


def test_routing_fixes():
    assert A.route("what is my net now?")[0] == "compare"
    assert A.route("कितना पैसा मिलेगा?")[0] == "compare"
    assert A.route("भाव का अनुमान बताओ")[0] == "forecast"
    assert A.route("order kahan hai")[0] == "track_order"
    assert A.route("english please") == ("set_language", {"lang": "en"})
    assert A.route("set hamali to 30") == ("set_assumption", {"hamali_per_qtl": 30.0})


def test_booking_without_an_order_does_not_ask_yes_no(db):
    _plan(db, "a5")
    r = say(db, "a5", "book transport")
    assert r["state"] == "plan" and "no order" in r["reply"]


def test_price_for_an_unknown_place_says_so(db):
    _plan(db, "a6")
    assert "no onion price" in say(db, "a6", "price at Xyzzyville")["reply"]


@pytest.mark.parametrize("word,val", [("ho", True), ("y", True), ("haan ji", True), ("होय", True), ("ok", True),
                                      ("na", False), ("nako", False), ("n", False), ("नहीं", False), ("nope", False)])
def test_yes_no_words(word, val):
    assert P.yes_no(word) is val


def test_units_carry_over_and_bare_number_needs_a_unit(db):
    say(db, "u1", "")
    r = say(db, "u1", "50 quintal onion and 20 potato")
    assert _crops(r) == {"onion": 50, "potato": 20} and r["awaiting"] == "location"
    say(db, "u2", "")
    say(db, "u2", "onion")
    assert say(db, "u2", "50")["awaiting"] == "qty"  # never guess kg for a bare number
    assert P.extract("-5 quintal").get("qty") is None and P.extract("99999999 quintal").get("qty") is None


def test_marathi_session_stays_marathi_for_devanagari():
    assert P.detect_lang("कुठे विकू?", "mr") == "mr"
    assert P.detect_lang("कांदा 50", "mr") == "mr"
    assert P.detect_lang("कहाँ बेचूँ?", "mr") == "hi"


@pytest.fixture
def gaz(db, tmp_path):
    (tmp_path / "postal").mkdir()
    (tmp_path / "admin1CodesASCII.txt").write_text("IN.16\tMaharashtra\tMaharashtra\t1\nIN.33\tGoa\tGoa\t2\n", encoding="utf-8")
    (tmp_path / "admin2Codes.txt").write_text("IN.16.516\tNashik\tNashik\t3\nIN.33.01\tNorth Goa\tNorth Goa\t4\n", encoding="utf-8")

    def row(gid, name, alts, lat, lon, a1, a2, pop):
        return "\t".join([gid, name, name, alts, lat, lon, "P", "PPL", "IN", "", a1, a2, "", "", str(pop), "", "", "Asia/Kolkata", "2020-01-01"])
    (tmp_path / "IN.txt").write_text("\n".join([
        row("1", "Niphad", "निफाड", "20.08", "74.11", "16", "516", 0),
        row("2", "Pune", "Poona,पुणे", "18.52", "73.86", "16", "", 3000000),
        row("3", "Ponda", "पोंडा", "15.40", "74.01", "33", "01", 22664),
        row("4", "Ponda", "", "23.50", "80.03", "35", "451", 0),
        row("5", "Lasalgaon", "", "20.15", "74.23", "16", "516", 17360)]) + "\n", encoding="utf-8")
    (tmp_path / "postal" / "IN.txt").write_text("IN\t422303\tNiphad\tMaharashtra\t16\tNashik\t516\tNA\t\t20.0794\t74.1093\t4\n", encoding="utf-8")
    assert G.load(db, tmp_path) > 5
    return db


def test_gazetteer_villages_pincodes_and_devanagari(gaz):
    assert G.find(gaz, "Niphad")["state"] == "Maharashtra"
    assert G.find(gaz, "422303")["name"] == "Niphad (422303)"
    assert G.find(gaz, "Ponda, North Goa")["state"] == "Goa"  # district hint picks the right namesake
    assert G.find(gaz, "Ponda")["state"] == "Goa"  # else the most populous
    assert G.find(gaz, "निफाड")["district"] == "Nashik"
    assert G.find(gaz, "माझे शेत पुण्याजवळ आहे")["name"] == "पुणे"  # Marathi oblique form + filler words
    assert G.find(gaz, "my farm is near Pune")["name"] == "Pune"
    assert G.find(gaz, "लासलगाव") is None and G.find(gaz, "लासलगाव", fuzzy=True)["district"] == "Nashik"  # romanized fallback
    assert G.find(gaz, "zzqx village") is None


def test_dev_name_translates_known_pieces_only(gaz):
    assert G.dev_name("Pune(Niphad), Pune, Maharashtra") == "पुणे(निफाड), पुणे, महाराष्ट्र"
    assert G.dev_name("APMC Unknownpur, Nashik, Maharashtra") == "APMC Unknownpur, Nashik, महाराष्ट्र"
    assert G.romanize("पिंपळगाव बसवंत") == "pimpalgav basvant"


# ---- reset / cancel: never hold on to a half-done task
def test_cancel_mid_intake_starts_fresh(db):
    say(db, "c1", "")
    say(db, "c1", "onion")
    r = say(db, "c1", "never mind")
    assert "dropped" in r["reply"] and r["awaiting"] == "crops" and r["crops"] == []


def test_cancel_drops_pending_yes_no_and_half_added_crop(db):
    _plan(db, "c2")
    assert say(db, "c2", "create the order")["state"] == "confirming_action"
    assert "dropped" in say(db, "c2", "cancel")["reply"]
    assert "Order" not in say(db, "c2", "yes")["reply"]  # the old question is gone, "yes" creates nothing
    say(db, "c2", "add tomato")
    say(db, "c2", "छोड़ो")
    assert A.STATE["c2"]["await"] is None and "tomato" not in _crops(say(db, "c2", "10 quintal"))


def test_cancel_the_order_is_still_an_order_action():
    assert not P.is_cancel("cancel the order") and A.route("cancel the order") == ("order_event", {"event": "cancel"})


def test_reload_drops_half_done_question_and_stale_intake_expires(db, monkeypatch):
    _plan(db, "c3")
    say(db, "c3", "create the order")
    say(db, "c3", "")  # page reload
    assert A.STATE["c3"]["pending"] is None
    say(db, "c4", "")
    say(db, "c4", "onion")
    intake.S["c4"]["ts"] -= intake.STALE_S + 1  # untouched for over 30 minutes
    r = say(db, "c4", "")
    assert r["awaiting"] == "crops" and r["crops"] == []


def test_start_over_clears_everything(db):
    _plan(db, "c5")
    r = say(db, "c5", "start over")
    assert r["actions"] == [{"type": "reset"}] and "c5" not in A.STATE
    assert say(db, "c5", "")["awaiting"] == "crops"


# ---- bug-hunter regressions (2026-11-14): natural yes/no in full sentences
@pytest.mark.parametrize("text,val", [
    ("Yes, go ahead.", True), ("yes we are ready to sell", True), ("Yes. Everything is correct.", True), ("haan bilkul, maal taiyar hai", True),
    ("हाँ, सब सही है, बेच दो", True), ("हो, सगळं बरोबर आहे", True), ("yes why not", True), ("of course", True), ("chalega", True), ("go for it", True),
    ("हाँ, नाशिक के पास सब सही है", True), ("no problem", True),
    ("Can't do it today, my market's busy.", False), ("don't do it yet", False), ("yes but not today", False), ("nahi abhi mat karo", False),
    ("नहीं, भंडारण नहीं कर सकता", False), ("no thanks", False), ("wait", False), ("नको, आत्ता नाही", False),
    ("yes but first tell me the price", None), ("haan par pehle batao kitna milega?", None)])
def test_yes_no_in_natural_sentences(text, val):
    assert P.yes_no(text) is val


def test_readback_yes_sentence_confirms_and_amount_correction_rereads(db):
    for t in ["", "onion", "50 quintal", "Niphad", "yes", "no"]:
        say(db, "n1", t)
    r = say(db, "n1", "no, it is 60 quintal")
    assert r["state"] == "collecting" and "60" in r["reply"]
    assert say(db, "n1", "Yes, everything is correct, we are ready to sell.")["state"] == "plan"


def test_hedged_yes_answers_first_then_asks_again(db):
    _plan(db, "n2")
    assert say(db, "n2", "sell it")["state"] == "confirming_action"
    r = say(db, "n2", "yes but first tell me how much I will get")
    assert r["state"] == "confirming_action" and not any(a["type"] == "order" for a in r["actions"])
    assert any(a["type"] == "order" for a in say(db, "n2", "ok yes, go ahead")["actions"])


def test_mentioning_the_same_lot_does_not_swallow_the_request(db):
    _plan(db, "n3")
    r = say(db, "n3", "is there cold storage for these 50 quintal onion?")
    assert "storage" in r["reply"].lower() and "New lot" not in r["reply"]


def test_intake_never_repeats_the_same_sentence_and_offers_buttons(db):
    say(db, "m9", "")
    say(db, "m9", "onion")
    r1 = say(db, "m9", "hmm")
    r2 = say(db, "m9", "hmm")
    assert r1["reply"] != r2["reply"] and "50 quintal" in r2["reply"]  # second miss: rephrased with an example
    say(db, "m9", "50 quintal")
    r = say(db, "m9", "Niphad")
    assert r["awaiting"] == "ready" and r.get("chips") == ["Yes, ready now", "Not yet"]


@pytest.mark.parametrize("said,key", [("chawal", "rice"), ("dhaan", "paddy(common)"), ("papita", "papaya"), ("kapas", "cotton"), ("tamatr", "tomato"),
                                      ("mosambi", "mousambi(sweet lime)"), ("shimla mirch", "capsicum")])
def test_any_crop_name_local_names_and_typos(said, key):
    from app.services import crops as CR
    assert P.resolve_crop(said, use_llm=False) == key or CR.EXTRA.get(said) == key


def test_order_uses_the_crop_the_farmer_names(db):
    for t in ["", "onion and tomato", "20 quintal", "10 quintal", "Niphad", "yes", "no", "yes"]:
        say(db, "oc1", t)
    assert say(db, "oc1", "tomato bech do")["state"] == "confirming_action" and A.STATE["oc1"]["active"] == "tomato"
    assert "How much potato" in say(db, "oc1", "sell my potato")["reply"]
    r = say(db, "oc1", "15 quintal")
    assert r["state"] == "confirming_action" and A.STATE["oc1"]["active"] == "potato"
    assert "could not find that crop" in say(db, "oc1", "I have 2 quintal dragon fruit")["reply"]
