"""KrishiMitra action agent. Understands a request (rules now; local LLM via llm.pick_tool when enabled), then EXECUTES tools:
UI actions (open a tab, show an option), plan changes (new lot, cost edits) and orders. The LLM only picks a tool; every tool is
deterministic Python. Anything with consequences (orders, bookings, confirming a sale) asks yes/no first."""
import re

from . import demo_data as D, intake, inventory, llm, orchestrator, orders, profile as P

STATE: dict = {}
TABS = {"compare": "Compare", "forecast": "Forecast", "logistics": "Storage & transport", "order": "Order"}
R = {  # replies; hi/mr for the core ones, English fallback otherwise
    "en": dict(tab="Opened {x}.", need_plan="Tell me your crop, amount and village first, then I can do that.", confirm="Shall I {what}? Say yes or no.",
               cancelled="Okay, I did not do it.", reset="Starting over.", unknown="I did not understand that. Try: \"show the forecast\", \"where should I sell\", \"book transport\", \"set commission to 3\", or \"create the order\".",
               best="Best option: {label}. You keep about Rs {net}.", lang="Switched language."),
    "hi": dict(tab="{x} खोल दिया।", need_plan="पहले अपनी फसल, मात्रा और गाँव बताइए।", confirm="क्या मैं {what}? हाँ या नहीं बोलिए।",
               cancelled="ठीक है, मैंने नहीं किया।", reset="नए सिरे से शुरू करते हैं।", unknown="मैं समझा नहीं। कहिए: \"भाव अनुमान दिखाओ\", \"कहाँ बेचूँ\", \"ट्रक बुक करो\" या \"ऑर्डर बनाओ\"।",
               best="सबसे अच्छा विकल्प: {label}। आपके हाथ में लगभग ₹{net}।", lang="भाषा बदल दी।"),
    "mr": dict(tab="{x} उघडले.", need_plan="आधी तुमचे पीक, प्रमाण आणि गाव सांगा.", confirm="मी {what} का? होय किंवा नाही म्हणा.",
               cancelled="ठीक आहे, मी केले नाही.", reset="पुन्हा सुरू करतो.", unknown="मला समजले नाही. म्हणा: \"भाव अंदाज दाखवा\", \"कुठे विकू\", \"ट्रक बुक करा\" किंवा \"ऑर्डर तयार करा\".",
               best="सर्वोत्तम पर्याय: {label}. तुमच्या हातात सुमारे ₹{net}.", lang="भाषा बदलली."),
}
TOOLS = ["show_tab", "compare", "forecast", "explain_decision", "price_of", "logistics", "confidence", "spoilage", "set_assumption", "set_lot",
         "create_order", "order_event", "track_order", "read_aloud", "set_language", "start_over", "help", "list_crops", "switch_crop"]
CONFIRM_TOOLS = {"create_order", "order_event"}
ARGLESS = {"compare", "forecast", "explain_decision", "logistics", "confidence", "spoilage", "track_order", "read_aloud", "create_order", "start_over", "help", "list_crops"}
ALLOWED_ASSUMPTIONS = {"commission_pct", "hamali_per_qtl", "road_factor", "risk_allowance_pct", "commission_payer", "financing_annual_pct", "ambient_temp_c"}
ORDER_EVENTS = {"request_transport": "request transport", "request_storage": "send the storage enquiry", "pickup": "mark it picked up",
                "deliver": "mark it delivered", "transporter_accepts": "record the transporter accepting", "operator_confirms_storage": "record the operator confirming storage",
                "confirm_sale": "confirm the final sale", "cancel": "cancel the order"}


def _inr(n) -> str:
    s = str(int(round(abs(n))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        s = ",".join(([head] if head else []) + parts + [tail])
    return ("-" if n < 0 else "") + s


def rt(lang, key, **kw):
    return (R.get(lang) or R["en"]).get(key, R["en"][key]).format(**kw)


def _num(m):
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- intent router (rules)
def route(text: str, lang: str, st: dict) -> tuple[str, dict]:
    low = text.translate(P.DEV).lower().replace(",", "")
    has = lambda *w: any(x in low for x in w)  # noqa: E731
    if has("start over", "reset", "new lot", "नए सिरे", "पुन्हा सुरू", "फिर से शुरू"):
        return "start_over", {}
    for words, code in (("hindi हिंदी हिन्दी", "hi"), ("marathi मराठी", "mr"), ("english अंग्रेजी अंग्रेज़ी इंग्रजी", "en")):
        if has(*words.split()) and has("speak", "switch", "language", "in ", "बोल", "भाषा", "बदल", "मध्ये", "में"):
            return "set_language", {"lang": code}
    if has("what can you do", "help", "मदद", "काय करू शकता", "क्या कर सकते"):
        return "help", {}
    if has("my crops", "what crops", "which crops", "list crops", "all my crops", "मेरी फसल", "माझी पिके", "कौन सी फसल", "कोणती पिके"):
        return "list_crops", {}
    found = P.extract(text)
    if "crop" in found and "qty" in found and has("i have", "i've got", "sell", "मेरे पास", "माझ्याकडे", "बेच", "विक"):
        return "set_lot", found
    m = re.search(r"commission\D{0,14}(\d+(?:\.\d+)?)", low) or re.search(r"कमीशन\D{0,10}(\d+(?:\.\d+)?)", low)
    if m:
        return "set_assumption", {"commission_pct": float(m.group(1))}
    m = re.search(r"(?:hamali|हमाली)\D{0,14}(\d+(?:\.\d+)?)", low)
    if m:
        return "set_assumption", {"hamali_per_qtl": float(m.group(1))}
    m = re.search(r"road factor\D{0,8}(\d+(?:\.\d+)?)", low)
    if m:
        return "set_assumption", {"road_factor": float(m.group(1))}
    m = re.search(r"risk(?: allowance)?\D{0,10}(\d+(?:\.\d+)?)", low)
    if m:
        return "set_assumption", {"risk_allowance_pct": float(m.group(1))}
    if has("seller pays", "i pay the commission"):
        return "set_assumption", {"commission_payer": "seller"}
    if has("buyer pays"):
        return "set_assumption", {"commission_payer": "buyer"}
    m = re.search(r"(?:sold|sale|price|at|@|₹|rs\.?)\s*(\d{3,6})", low)
    if has("confirm the sale", "confirm sale", "i sold", "sale done", "बेच दिया", "विकले") and m:
        return "order_event", {"event": "confirm_sale", "actual_price": float(m.group(1))}
    for phrase, ev in (("book transport", "request_transport"), ("request transport", "request_transport"), ("book a truck", "request_transport"), ("book truck", "request_transport"),
                       ("ट्रक बुक", "request_transport"), ("गाड़ी बुक", "request_transport"), ("ट्रक बुक करा", "request_transport"),
                       ("book storage", "request_storage"), ("storage enquiry", "request_storage"), ("book cold storage", "request_storage"), ("भंडारण बुक", "request_storage"),
                       ("साठवण बुक", "request_storage"), ("mark delivered", "deliver"), ("it is delivered", "deliver"), ("picked up", "pickup"), ("cancel the order", "cancel"),
                       ("cancel order", "cancel")):
        if phrase in low:
            return "order_event", {"event": ev}
    if has("create the order", "create order", "place the order", "place order", "sale order", "book it", "ऑर्डर बना", "ऑर्डर तयार", "ऑर्डर कर"):
        return "create_order", {}
    if has("track", "my order", "order status", "ऑर्डर स्टेटस", "ऑर्डर कुठे"):
        return "track_order", {}
    if has("forecast", "predict", "next week", "will the price", "price go", "भाव अनुमान", "अंदाज", "आगे भाव", "भविष्य"):
        return "forecast", {}
    if has("sell now", "hold", "wait", "should i sell", "should i keep", "बेचूँ", "बेचूं", "रोकूँ", "रोकूं", "थांबू", "विकू का", "रोक")             and not has("where", "which mandi", "कहाँ", "कहां", "कुठे"):
        return "explain_decision", {}
    if has("how sure", "confident", "reliable", "trust", "भरोसा", "किती खात्री"):
        return "confidence", {}
    if has("spoil", "rot", "fresh", "खराब", "सड़", "खराब होईल"):
        return "spoilage", {}
    if has("storage", "warehouse", "cold store", "transport", "truck", "भंडारण", "गोदाम", "साठवण", "ट्रक", "ढुलाई", "वाहतूक", "shared"):
        return "logistics", {}
    if has("read", "say again", "repeat", "tell me", "सुनाओ", "सुनाइए", "ऐका", "पुन्हा सांगा"):
        return "read_aloud", {}
    if has("price", "rate", "भाव", "दाम", "किंमत"):
        return "price_of", {"text": low}
    if has("best", "which mandi", "where should", "where to sell", "compare", "ranking", "rank", "सबसे अच्छ", "कहाँ बेच", "कहां बेच", "कुठे विक", "तुलना", "show me"):
        return "compare", {}
    for k, v in (("order", "order"), ("compare", "compare"), ("forecast", "forecast")):
        if has(f"open {k}", f"go to {k}", f"show {k}"):
            return "show_tab", {"tab": v}
    return "unknown", {}


# ---------------------------------------------------------------- tools
def _plan(st):
    return st.get("plan")


def _need_plan(lang):
    return {"reply": rt(lang, "need_plan"), "actions": []}


def _tab(tab, extra=""):
    return {"type": "tab", "value": tab}


def run_tool(tool: str, args: dict, st: dict, lang: str) -> dict:
    plan = _plan(st)
    if tool in ("help", "start_over", "set_language"):
        pass
    elif tool != "set_lot" and not plan:
        return _need_plan(lang)

    if tool == "help":
        return {"reply": "I can: compare mandis and tell you where to sell, show the forecast, explain sell-now vs hold, show storage and transport, check a price, change a cost (e.g. \"set commission to 3\"), "
                         "start a new lot (\"I have 50 quintal tomato near Pune\"), create and track an order, book transport or storage, and switch language.", "actions": []}
    if tool == "start_over":
        STATE.pop(st["sid"], None)
        inventory.clear(st["sid"])
        intake.S.pop(st["sid"], None)
        P.SESSIONS.pop(st["sid"], None)
        return {"reply": rt(lang, "reset"), "actions": [{"type": "reset"}]}
    if tool == "set_language":
        return {"reply": rt(args["lang"], "lang"), "actions": [{"type": "lang", "value": args["lang"]}], "lang": args["lang"]}
    if tool == "show_tab":
        return {"reply": rt(lang, "tab", x=TABS[args["tab"]]), "actions": [_tab(args["tab"])]}

    rec = plan["recommendation"] or {}
    best = rec.get("best")
    if tool == "list_crops":
        lots = (st.get("farmer") or {}).get("lots", {})
        txt = intake.lots_text(lots, lang) if lots else "none yet"
        return {"reply": ("Your crops: " if lang == "en" else "") + txt + (". Say a crop name to switch." if lang == "en" else ""), "actions": []}
    if tool == "switch_crop":
        crop = args["crop"]
        if crop not in (st.get("farmer") or {}).get("lots", {}):
            return {"reply": f"You have not told me about {crop} yet. Say, for example, \"I have 50 quintal {crop} near {plan['profile']['location']['name']}\".", "actions": []}
        new = _activate(st, crop, lang)
        b = (new["recommendation"] or {}).get("best")
        msg = rt(lang, "best", label=b["label"], net=_inr(b["net"])) if b else (new["recommendation"] or {}).get("reason", "No usable prices for that crop nearby.")
        return {"reply": f"{P.NAMES[crop][lang]}. {msg}", "actions": [{"type": "plan", "plan": new}]}
    if tool == "compare":
        if not best:
            return {"reply": rec.get("reason", "No usable prices."), "actions": [_tab("compare")]}
        top = plan["options"][:3]
        lines = "; ".join(f"{o['rank']}) {o['label']}: Rs {_inr(o['net'])}" for o in top)
        return {"reply": rt(lang, "best", label=best["label"], net=_inr(best["net"])) + (" " + lines if lang == "en" else ""), "actions": [_tab("compare"), {"type": "open_option", "index": 0}]}
    if tool == "explain_decision":
        dec = rec.get("decision") or {}
        why = "; ".join(dec.get("factors", [])[:3])
        return {"reply": f"{dec.get('action', 'No decision')}. {dec.get('reason', '')} {why}", "actions": []}
    if tool == "forecast":
        dest = plan["sell_vs_hold"]["destination"]
        fc = (plan.get("forecasts") or {}).get(dest, {})
        ok = [h for h in fc.get("horizons", []) if h["status"] == "ok"]
        if ok:
            txt = "; ".join(f"in {h['horizon_days']} days about Rs {h['predicted']:,.0f} (range {h['lo']:,.0f} to {h['hi']:,.0f})" for h in ok[:3])
            reply = f"Forecast for {dest}: {txt}. Not a guarantee."
        else:
            n = len(D.series(plan["profile"]["crop"], dest))
            reply = f"No reliable forecast yet for {dest}: only {n} day(s) of stored prices, and about 120 are needed. I will not guess."
        return {"reply": reply, "actions": [_tab("forecast")]}
    if tool == "logistics":
        stor = plan.get("storage") or []
        tr = (plan.get("transport") or [{}])[0]
        s = f"Nearest cold storage (demo, availability unconfirmed): {stor[0]['name']}, about Rs {stor[0]['est_cost_7d']:,} for 7 days. " if stor else "No suitable storage nearby. "
        t = f"Transport to {tr.get('destination')}: about Rs {tr.get('total', 0):,.0f} by {tr.get('vehicle')} (estimate)." if tr else ""
        return {"reply": s + t, "actions": [_tab("logistics")]}
    if tool == "confidence":
        c = rec.get("confidence")
        if not c:
            return {"reply": "No confidence available.", "actions": []}
        return {"reply": f"Confidence is {c['label']}. " + "; ".join(c["detractors"][:2] or c["contributors"][:2]), "actions": []}
    if tool == "spoilage":
        sp = (best or {}).get("spoilage")
        return {"reply": f"Spoilage risk on the best trip: {sp['level']} ({sp['probability']:.0%}, about {sp['transit_hours']} hours)." if sp else "No spoilage estimate.", "actions": []}
    if tool == "price_of":
        low = args.get("text", "")
        names = [m["name"] for m in plan["mandis"]]
        hit = next((n for n in names if n.split()[0].lower() in low), None)
        ps = [plan["prices"][hit]] if hit else [plan["prices"][n] for n in names[:3]]
        txt = "; ".join(f"{p['mandi']}: modal Rs {p['modal']:,.0f} per quintal (range {p['min']:,.0f} to {p['max']:,.0f}), {'today' if p['age_days'] == 0 else str(p['age_days']) + ' days old'}" for p in ps)
        return {"reply": txt, "actions": [_tab("compare")]}
    if tool == "read_aloud":
        return {"reply": rec.get("explanation", "Nothing to read yet."), "actions": []}
    if tool == "track_order":
        o = orders.get(st["order_id"]) if st.get("order_id") else None
        if not o:
            return {"reply": "There is no order yet. Say \"create the order\" to make one.", "actions": []}
        return {"reply": f"Order {o['id']} is {o['status'].replace('_', ' ')}. Next: {', '.join(o['next_events']) or 'nothing'}.", "actions": [{"type": "order", "order": o}, _tab("order")]}
    if tool == "set_assumption":
        bad = [k for k, v in args.items() if k not in ALLOWED_ASSUMPTIONS or (k != "commission_payer" and not (isinstance(v, (int, float)) and 0 <= v <= 1000))]
        if bad or not args:
            return {"reply": "I cannot change that setting.", "actions": []}
        st["override"] = {**st.get("override", {}), **args}
        new = orchestrator.run(plan["profile"], st["override"])
        st["plan"] = new
        st["plans"][st["active"]] = new
        b = (new["recommendation"] or {}).get("best")
        return {"reply": f"Updated {', '.join(f'{k} = {v}' for k, v in args.items())} and recalculated. " + (f"Best option now keeps about Rs {_inr(b['net'])}." if b else "No usable option.")
                + (" Note: the buyer pays commission by default, so this does not change your net. Say \"seller pays\" to include it." if "commission_pct" in args and new["assumptions"]["commission_payer"] == "buyer" else ""),
                "actions": [{"type": "plan", "plan": new}]}
    if tool == "set_lot":
        crop = args["crop"]
        q = args["qty"]
        loc = args.get("location") or (plan["profile"]["location"] if plan else None)
        if not loc:
            return {"reply": "Which village or town is the produce in?", "actions": []}
        prev = plan["profile"] if plan else {}
        prof = {"crop": crop, "qty_kg": q["qty_kg"], "original_qty": q["original_qty"], "original_unit": q["original_unit"], "location": loc, "ready": prev.get("ready", True),
                "can_store": prev.get("can_store", False), "variety": None, "grade": None, "harvest_date": None, "sell_pref": None, "lang": lang}
        farmer = st.setdefault("farmer", None) or {"location": loc, "ready": prof["ready"], "can_store": prof["can_store"], "lang": lang, "lots": {}}
        farmer["lots"][crop] = dict(q)
        farmer["location"] = loc
        st["farmer"] = farmer
        inventory.save(st["sid"], farmer)
        new = orchestrator.run(prof, st.get("override"))
        st["plan"], st["active"] = new, crop
        st["plans"][crop] = new
        b = (new["recommendation"] or {}).get("best")
        msg = rt(lang, "best", label=b["label"], net=_inr(b["net"])) if b else (new["recommendation"] or {}).get("reason", "No usable prices for that crop nearby.")
        return {"reply": f"New lot: {q['original_qty']:g} {q['original_unit']} {crop} near {loc['name']}. {msg}", "actions": [{"type": "plan", "plan": new}]}
    if tool in CONFIRM_TOOLS:
        return {"reply": "internal: confirmation required", "actions": []}
    return {"reply": rt(lang, "unknown"), "actions": []}


def _confirm_text(tool, args):
    return "create the sale order for the best option" if tool == "create_order" else ORDER_EVENTS.get(args.get("event"), "do that")


def _execute_confirmed(tool, args, st, lang):
    plan = st["plan"]
    if tool == "create_order":
        best = plan["recommendation"]["best"]
        o = orders.create(best, plan["profile"])
        st["order_id"] = o["id"]
        st["orders"][st["active"]] = o["id"]
        return {"reply": f"Done. Order {o['id']} created for {best['label']}, expected net Rs {_inr(best['net'])}. This is an expectation, not a final sale.", "actions": [{"type": "order", "order": o}, _tab("order")]}
    if tool == "order_event":
        if not st.get("order_id"):
            return {"reply": "There is no order yet. Say \"create the order\" first.", "actions": []}
        ev = args["event"]
        data = None
        if ev == "confirm_sale":
            data = {"actual_price": args["actual_price"], "actual_qty_kg": plan["profile"]["qty_kg"], "actual_costs": (plan["recommendation"]["best"] or {}).get("total_deductions", 0)}
        try:
            o = orders.event(st["order_id"], ev, data)
        except ValueError as e:
            return {"reply": f"I could not do that now: {e}.", "actions": []}
        notes = {"request_transport": "Transport request sent. It is an estimate, not a confirmed quote.", "request_storage": "Storage enquiry sent. Availability is not confirmed until the operator confirms."}
        return {"reply": notes.get(ev, f"Done: {ORDER_EVENTS.get(ev, ev)}. Order is now {o['status'].replace('_', ' ')}."), "actions": [{"type": "order", "order": o}, _tab("order")]}
    return {"reply": rt(lang, "unknown"), "actions": []}


# ---------------------------------------------------------------- crops (memory) helpers
def _profile_for(st, crop, lang):
    f = st["farmer"]
    lot = f["lots"][crop]
    return {"crop": crop, "qty_kg": lot["qty_kg"], "original_qty": lot["original_qty"], "original_unit": lot["original_unit"], "location": f["location"],
            "ready": f["ready"], "can_store": f["can_store"], "variety": None, "grade": None, "harvest_date": None, "sell_pref": None, "lang": lang}


def _activate(st, crop, lang):
    plan = orchestrator.run(_profile_for(st, crop, lang), st["override"])
    st["plans"][crop] = plan
    st["plan"], st["active"] = plan, crop
    st["order_id"] = st["orders"].get(crop)
    return plan


def _start_from_farmer(st, farmer, lang):
    st["farmer"] = farmer
    first = next(iter(farmer["lots"]))
    return _activate(st, first, lang)


# ---------------------------------------------------------------- entry point
def handle(sid: str, text: str, lang: str | None = None) -> dict:
    res = _handle(sid, text, lang)
    st, L = STATE.get(sid), res.get("lang", "en")
    names = P.NAMES
    if st and st.get("farmer") and st.get("plan"):
        res["crops"] = [{"crop": c, "label": names[c][L], "qty": q["original_qty"], "unit": q["original_unit"], "active": c == st["active"]} for c, q in st["farmer"]["lots"].items()]
    elif sid in intake.S:
        s = intake.S[sid]
        res["crops"] = [{"crop": c, "label": names[c][L], "qty": (s["lots"].get(c) or {}).get("original_qty"), "unit": (s["lots"].get(c) or {}).get("original_unit"), "active": False} for c in s["crops"]]
    else:
        res["crops"] = []
    return res


def _handle(sid: str, text: str, lang: str | None = None) -> dict:
    st = STATE.setdefault(sid, {"sid": sid, "plan": None, "pending": None, "order_id": None, "override": {}, "farmer": None, "plans": {}, "active": None, "orders": {}})
    text = (text or "").strip()
    L = lang or P.detect_lang(text, intake.S.get(sid, {}).get("lang") or (st["farmer"] or {}).get("lang") or "en")
    trace = []

    # pending confirmation
    if st["pending"]:
        yn = P.yes_no(text)
        pend, st["pending"] = st["pending"], None
        if yn is True:
            out = _execute_confirmed(pend["tool"], pend["args"], st, L)
            trace.append({"tool": pend["tool"], "args": pend["args"], "confirmed": True})
            return {**out, "trace": trace, "lang": L, "session_id": sid, "chips": []}
        if yn is False:
            return {"reply": rt(L, "cancelled"), "actions": [], "trace": trace, "lang": L, "session_id": sid, "chips": []}

    # page reload on a live session: resume where the farmer was instead of treating silence as a request
    if not text and st["plan"] and st["farmer"]:
        return {"reply": intake.welcome_back(st["farmer"], L), "actions": [{"type": "plan", "plan": st["plan"]}], "trace": [{"tool": "resume", "args": {}}],
                "lang": L, "session_id": sid, "state": "plan", "chips": [], "done": True}

    # no plan yet: multi-crop intake (confirm-before-work stays enforced), plus a few global commands
    if not st["plan"]:
        tool, args = route(text, L, st) if text else ("unknown", {})
        if tool in ("start_over", "set_language", "help"):
            out = run_tool(tool, args, st, L)
            return {**out, "trace": [{"tool": tool, "args": args}], "lang": out.get("lang", L), "session_id": sid, "chips": [], "state": "collecting"}
        if not text and sid not in intake.S:  # returning farmer: remembered crops, no questions
            farmer = inventory.load(sid)
            if farmer:
                L = lang or farmer.get("lang", L)
                plan = _start_from_farmer(st, farmer, L)
                return {"reply": intake.welcome_back(farmer, L), "actions": [{"type": "plan", "plan": plan}], "trace": [{"tool": "run_plan", "args": {"remembered": True}}],
                        "lang": L, "session_id": sid, "state": "plan", "chips": [], "done": True}
        r = intake.step(sid, text, lang)
        actions = []
        if r["done"]:
            plan = _start_from_farmer(st, r["farmer"], r["lang"])
            actions.append({"type": "plan", "plan": plan})
            trace.append({"tool": "run_plan", "args": {"crop": st["active"], "crops": list(r["farmer"]["lots"])}})
        return {"reply": r["reply"], "actions": actions, "trace": trace, "lang": r["lang"], "session_id": sid, "state": "plan" if r["done"] else "collecting", "chips": [], "done": r["done"], "awaiting": r.get("awaiting")}

    # a mention of another saved crop switches to it first ("tomato forecast", "show my onion")
    f = P.extract(text)
    pre_actions = []
    lots = (st["farmer"] or {}).get("lots", {})
    if "crop" in f and f["crop"] != st["active"] and f["crop"] in lots and "qty" not in f:
        plan = _activate(st, f["crop"], L)
        pre_actions.append({"type": "plan", "plan": plan})
        trace.append({"tool": "switch_crop", "args": {"crop": f["crop"]}})
        if P.extract(text).keys() <= {"crop"} and route(text, L, st)[0] == "unknown":
            b = (plan["recommendation"] or {}).get("best")
            msg = rt(L, "best", label=b["label"], net=_inr(b["net"])) if b else (plan["recommendation"] or {}).get("reason", "No usable prices for that crop nearby.")
            return {"reply": f"{P.NAMES[f['crop']][L]}. {msg}", "actions": pre_actions, "trace": trace, "lang": L, "session_id": sid, "chips": [], "state": "plan"}

    # plan exists: act on the request
    tool, args = "unknown", {}
    if llm.enabled():
        picked = llm.pick_tool(text, TOOLS, {"crop": st["plan"]["profile"]["crop"]})
        if picked and picked.get("tool") in TOOLS:
            r_tool, r_args = route(text, L, st)
            if picked["tool"] in ARGLESS:
                tool, args = picked["tool"], {}
            elif r_tool == picked["tool"]:
                tool, args = r_tool, r_args  # tools needing arguments: only rule-parsed, validated arguments are accepted
    if tool == "unknown":
        tool, args = route(text, L, st)
    trace.append({"tool": tool, "args": {k: v for k, v in args.items() if k != "text"}})
    if tool in CONFIRM_TOOLS:
        st["pending"] = {"tool": tool, "args": args}
        return {"reply": rt(L, "confirm", what=_confirm_text(tool, args)), "actions": pre_actions, "trace": trace, "lang": L, "session_id": sid, "chips": ["Yes", "No"], "state": "confirming_action"}
    out = run_tool(tool, args, st, L)
    return {**out, "actions": pre_actions + out.get("actions", []), "trace": trace, "lang": out.get("lang", L), "session_id": sid, "chips": [], "state": "plan"}
