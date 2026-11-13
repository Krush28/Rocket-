import pytest
from app.services import costs
from app.ml import forecast
from app.services import logistics
from app.agents import orchestrator
from app.services import orders
from app.conversation import profile_agent as P
from app.services import demo_data as D

A = costs.assumptions()


def test_transport_multi_trip_and_rejects_zero():
    t = costs.transport(250, 100)  # 250 qtl -> trips needed
    assert t["trips"] >= 3 and t["label"] == "ESTIMATE"
    with pytest.raises(ValueError):
        costs.transport(0, 10)


def test_sell_net_formula():
    o = costs.sell_option(2000, 100, 50, A)
    t = costs.transport(100, 50)["total"]
    rev = 100 * (1 - 0.005) * 2000
    assert o["net"] == round(rev - t - 15 * 100)  # buyer pays commission by default


def test_spoilage_not_double_counted():
    h = costs.hold_option(7, 2000, 2000, 100, 40, None, 0, 0, A, shrink_wk=10)
    # only quantity shrinks; no separate rupee spoilage deduction exists
    assert "spoilage" not in h["deductions"] and h["expected_loss_qty"] > 9


def test_decide_rules():
    sell = {"net": 100000}
    assert costs.decide(None, [])["action"] == "INSUFFICIENT INFORMATION"
    assert costs.decide(sell, [])["action"] == "SELL NOW"
    assert costs.decide(sell, [{"days": 7, "net": 101000, "p_decline": 0.1}])["action"] == "SELL NOW"  # gain below 2% margin
    assert costs.decide(sell, [{"days": 7, "net": 110000, "p_decline": 0.6}])["action"] == "SELL NOW"  # too risky
    assert costs.decide(sell, [{"days": 7, "net": 110000, "p_decline": 0.1}])["action"] == "HOLD"


def test_forecast_chronological_and_gate_fields():
    f = forecast.forecast("onion", "Nashik APMC")
    assert f["status"] == "ok" and len(f["horizons"]) == 5
    for h in f["horizons"]:
        assert h["lo"] <= h["predicted"] <= h["hi"]
        assert h["status"] in ("ok", "no_reliable_forecast", "insufficient_data")
        assert "gate" in h and "eval" in h


def test_insufficient_data(monkeypatch):
    import pandas as pd
    monkeypatch.setattr(D, "series", lambda c, m: pd.DataFrame({"date": pd.date_range("2026-01-01", periods=30), "modal": 1000.0, "min": 900.0, "max": 1100.0, "arrivals_t": 10.0}))
    forecast.forecast.cache_clear()
    assert forecast.forecast("onion", "Pune APMC")["status"] == "insufficient_data"
    forecast.forecast.cache_clear()


def test_profile_conversation_flow_and_confirmation():
    P.SESSIONS.clear()
    r = P.chat("s1", "")
    assert "crop" in r["awaiting"]
    r = P.chat("s1", "I have 1,000 kg of tomatoes")
    assert r["slots"]["qty"]["qty_kg"] == 1000 and r["awaiting"] == "location"
    r = P.chat("s1", "Near Ponda, Goa")
    assert r["awaiting"] == "ready"
    r = P.chat("s1", "Yes")
    assert r["awaiting"] == "can_store"
    r = P.chat("s1", "no")
    assert r["state"] == "confirming" and not r["done"]  # no market work before confirm
    r = P.chat("s1", "yes")
    assert r["done"] and r["profile"]["qty_kg"] == 1000 and r["profile"]["can_store"] is False


def test_profile_hindi_numerals_and_units_and_correction():
    P.SESSIONS.clear()
    P.chat("h", "")
    r = P.chat("h", "मेरे पास २०० क्विंटल प्याज है")
    assert r["slots"]["qty"]["qty_kg"] == 20000 and r["slots"]["crop"] == "onion" and r["lang"] == "hi"
    P.chat("h", "निफाड")
    P.chat("h", "हाँ")
    r = P.chat("h", "नहीं")
    r = P.chat("h", "actually 150 quintal")  # correction while confirming
    assert r["slots"]["qty"]["qty_kg"] == 15000


def test_profile_garbage_gets_reprompt():
    P.SESSIONS.clear()
    P.chat("g", "")
    r = P.chat("g", "asdf qwer")
    assert r["awaiting"] == "crop" and "crop" not in r["slots"]


def test_shared_load_saves_money_and_respects_capacity():
    pool = logistics.simulated_pool("onion", "Lasalgaon APMC", (20.14, 74.24), (20.08, 74.11))
    r = logistics.match(30, 20, pool)
    assert r["status"] == "ok" and r["total_pooled"] <= r["total_solo"]
    for v in r["vehicles"]:
        assert v["load_qtl"] <= v["capacity_qtl"]
    assert all(m["name"].startswith("[Simulated]") or m["id"] == "YOU" for m in r["members"])


def test_orchestrator_end_to_end_ranked_and_labelled():
    prof = {"crop": "onion", "qty_kg": 20000, "original_qty": 200, "original_unit": "quintal",
            "location": {"name": "Niphad", "lat": 20.08, "lon": 74.11}, "ready": True, "can_store": True, "lang": "en"}
    p = orchestrator.run(prof)
    assert all(t["status"] == "ok" for t in p["trace"])
    scores = [o["score"] for o in p["options"]]
    assert scores == sorted(scores, reverse=True)
    assert "DEMO DATA" in p["labels"]
    assert p["recommendation"]["decision"]["action"] in ("SELL NOW", "HOLD")
    assert all(b["phone"] is None for b in p["buyers"]) and all(w["available_capacity_qtl"] is None for w in p["storage"])


def test_tomato_hold_limited_by_shelf_life():
    prof = {"crop": "tomato", "qty_kg": 1000, "original_qty": 1000, "original_unit": "kg",
            "location": {"name": "Ponda", "lat": 15.40, "lon": 74.02}, "ready": True, "can_store": False, "lang": "en"}
    p = orchestrator.run(prof)
    assert all(h["days"] <= 7 for h in p["sell_vs_hold"]["holds"])


def test_orders_flow_and_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(orders, "DB", tmp_path / "t.db")
    o = orders.create({"net": 1000, "label": "x"}, {"crop": "onion"})
    with pytest.raises(ValueError):
        orders.event(o["id"], "deliver")  # illegal jump
    for ev in ("request_transport", "request_storage"):
        o = orders.event(o["id"], ev)
    assert o["status"] == "storage_enquiry_sent"  # enquiry, not confirmed
    for ev in ("transporter_accepts", "pickup", "deliver"):
        o = orders.event(o["id"], ev)
    with pytest.raises(ValueError):
        orders.event(o["id"], "confirm_sale", {"actual_price": 0, "actual_qty_kg": 10})
    o = orders.event(o["id"], "confirm_sale", {"actual_price": 2000, "actual_qty_kg": 10000, "actual_costs": 5000})
    assert o["payload"]["final"]["net_earnings"] == 195000


def test_live_adapter_parse_and_live_mode(tmp_path, monkeypatch):
    from app.services.adapters import agmarknet_datagov as adapters
    assert not adapters.live_mode()
    good = {"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon", "commodity": "Onion", "variety": "Other", "grade": "FAQ",
            "arrival_date": "12/11/2026", "min_price": "1500", "max_price": "2100", "modal_price": "1900"}
    assert adapters.parse_record({**good, "modal_price": "NA"}) is None
    assert adapters.parse_record({**good, "arrival_date": "bad"}) is None
    assert adapters.parse_record({**good, "modal_price": "0"}) is None
    adapters.upsert([adapters.parse_record(good), adapters.parse_record({**good, "variety": "Red", "modal_price": "2100"})])
    assert adapters.live_mode()
    df = adapters.live_df("onion", "Lasalgaon APMC")
    assert len(df) == 1 and df["modal"].iloc[0] == 2000  # median across varieties
    assert adapters.live_df("onion", "Pune APMC").empty
    # live mode never fills other mandis with demo values; short history -> explicit insufficient_data
    forecast.forecast.cache_clear()
    assert forecast.forecast("onion", "Lasalgaon APMC")["status"] == "insufficient_data"
    prof = {"crop": "onion", "qty_kg": 5000, "original_qty": 50, "original_unit": "quintal", "location": {"name": "Niphad", "lat": 20.08, "lon": 74.11},
            "ready": True, "can_store": False, "lang": "en"}
    p = orchestrator.run(prof)
    assert p["data_mode"] == "LIVE" and [m["name"] for m in p["mandis"]] == ["Lasalgaon APMC"]
    assert p["recommendation"]["decision"]["action"] == "SELL NOW"  # no reliable forecast -> holding unsupported
    forecast.forecast.cache_clear()


def test_import_csv_backfill(tmp_path, monkeypatch):
    from app.services.adapters import agmarknet_datagov as adapters
    f = tmp_path / "x.csv"
    f.write_text("Market,State,Commodity,Arrival_Date,Min Price,Max Price,Modal Price\nPune,Maharashtra,Onion,10/11/2026,1500,2000,1800\nPune,Maharashtra,Onion,11/11/2026,1500,2000,0\n")
    assert adapters.import_csv(str(f))["rows_upserted"] == 1  # zero-price row dropped
    (tmp_path / "bad.csv").write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        adapters.import_csv(str(tmp_path / "bad.csv"))


def test_import_csv_agmarknet_style_headers(tmp_path, monkeypatch):
    from app.services.adapters import agmarknet_datagov as adapters
    f = tmp_path / "a.csv"
    f.write_text("State Name,District Name,Market Name,Variety,Group,Commodity,Grade,Min Price (Rs./Quintal),Max Price (Rs./Quintal),Modal Price (Rs./Quintal),Price Date\n"
                 "Maharashtra,Nashik,Lasalgaon,Red,Vegetables,Onion,FAQ,1500,2100,1900,13 Nov 2026\n")
    assert adapters.import_csv(str(f))["rows_upserted"] == 1
    assert adapters.live_df("onion", "Lasalgaon APMC")["modal"].iloc[0] == 1900


def test_csv_watcher_imports_once_then_again_on_new_file(tmp_path, monkeypatch):
    import os
    from app.services.adapters import agmarknet_datagov as adapters
    d = tmp_path / "dl"; d.mkdir()
    f = d / "9ef84268-d588-465a-a308-a864a43d0070.csv"
    f.write_text("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_x0020_Price,Max_x0020_Price,Modal_x0020_Price\nMaharashtra,Nashik,Lasalgaon APMC,Onion,Red,FAQ,13/11/2026,1500,2100,1900\n")
    (d / "other.csv").write_text("junk")
    assert [x.get("rows") for x in adapters.scan_and_import([d])] == [1]
    assert adapters.scan_and_import([d]) == []  # same file, not re-imported
    os.utime(f, (f.stat().st_atime, f.stat().st_mtime + 10))  # re-downloaded -> new mtime
    assert len(adapters.scan_and_import([d])) == 1
    assert adapters.last_import()["rows"] == 1
    f.write_text("not,a,price,file\n1,2,3,4\n")
    os.utime(f, (f.stat().st_atime, f.stat().st_mtime + 20))
    assert "error" in adapters.scan_and_import([d])[0]  # bad file reported, not crashed
