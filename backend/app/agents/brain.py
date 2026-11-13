"""Agentic brain for the voice agent: local LLM (llm.plan_tools) decides WHICH tools to run for a free-form request (up to 3, in order);
this module validates every argument and executes deterministic tools from action_agent. Replies are the tools' own translated
sentences; free questions get llm.grounded_answer over plan facts (numbers checked). Orders/bookings still stop at a yes/no."""
import re

from app.agents import action_agent as A
from app.conversation import intake, profile_agent as P
from app.services import crops as CR
from app.services import llm
from app.services import schemes as SC

MULTI = re.compile(r"\b(and|then|aur|phir|plus)\b|और|आणि|फिर|नंतर|तसेच", re.I)  # "also"/"bhi" mean "too", not a second request
SHOP = re.compile(r"shop|retail|dukan|dukaan|consumer|दुकान|खुदरा|किरकोळ", re.I)
LANGWORD = re.compile(r"english|hindi|marathi|angrezi|इंग्रजी|अंग्रेज|हिंदी|हिन्दी|मराठी", re.I)
WEAK = {"help", "read_aloud", "list_crops", "spoilage", "show_tab", "set_qty", "confidence", "explain_decision", "forecast", "price_of"}
COST = {"commission": "commission_pct", "hamali": "hamali_per_qtl", "risk": "risk_allowance_pct", "road_factor": "road_factor"}


def wants_brain(text: str, rule_tool: str) -> bool:
    """LLM only when the rules do not understand, or one sentence carries several requests."""
    if not llm.enabled() or not text:
        return False
    if rule_tool in ("unknown", "explain"):
        return True
    if rule_tool in WEAK and len(text.split()) >= 7:  # "can you help me find cold storage": a generic word must not beat the real intent
        return True
    if llm.provider() == "cloud" and rule_tool not in RULES_ONLY and len(text.split()) >= 4:
        return True  # a strong cloud model reads the whole sentence; exact commands and anything with typed numbers stay on the rules
    if llm.provider() == "cloud" and rule_tool == "order_event" and MULTI.search(text) and not re.search(r"\d", text):
        return True  # "what will Lasalgaon pay and should I book a truck": two requests, not one booking command
    # a second request joined to a question ("price at Pune and should I hold?"); clear single actions stay on the fast rules
    return rule_tool in ("compare", "price_of", "explain_decision", "forecast", "logistics", "retail") and len(text.split()) >= 6 and bool(MULTI.search(text))


RULES_ONLY = {"start_over", "set_language", "set_lot", "set_qty", "set_assumption", "order_event", "remove_lot", "help",
              "list_crops", "thanks", "show_tab", "read_aloud"}


def recent(st: dict) -> str:
    """The last few turns, so the model can resolve 'it', 'that mandi', 'wahan'."""
    return " / ".join(f"farmer: {h['u']} -> assistant: {h['a']}" for h in (st.get("history") or [])[-4:])


def _crop_key(name: str | None, text: str) -> str | None:
    for cand in (name or "", text):
        if cand:
            k = P._crop(cand.translate(P.DEV), cand.lower())
            if k:
                return k
    return None


def facts(st: dict) -> str:
    """Compact, checkable facts the LLM may use to answer questions (all numbers come from the deterministic plan)."""
    p = st["plan"]
    prof, rec = p["profile"], p.get("recommendation") or {}
    out = [f"crop {CR.name(prof['crop'], 'en')}, {prof['original_qty']:g} {prof['original_unit']} ({prof['qty_kg']:.0f} kg), farm near {prof['location']['name']}"]
    b = rec.get("best")
    if b:
        out.append(f"best option: {b['label']}, net in hand Rs {b['net']:.0f}, price Rs {b.get('price', 0):.0f}/quintal, {b.get('distance_km', 0):.0f} km")
    for o in (p.get("options") or [])[:4]:
        out.append(f"option {o['label']}: net Rs {o['net']:.0f}, price Rs {o.get('price', 0):.0f}/quintal, distance {o.get('distance_km', 0):.0f} km")
    d = rec.get("decision") or (p.get("sell_vs_hold") or {}).get("decision") or {}
    if d:
        out.append(f"decision {d.get('action')}: {d.get('reason', '')}; " + "; ".join(d.get("factors", [])[:3]))
    a = p.get("assumptions") or {}
    out.append(f"costs: commission {a.get('commission_pct')}% paid by {a.get('commission_payer')}, hamali Rs {a.get('hamali_per_qtl')}/quintal")
    c = rec.get("confidence")
    if c:
        out.append(f"confidence {c.get('label')}")
    out.append(f"data: {p.get('data_mode')} prices")
    return " | ".join(out)


def _exec(tool: str, a: dict, text: str, st: dict, L: str, db) -> dict | None:
    """One planned call -> action_agent result dict ({reply, actions} or {confirm}), or None to skip an invalid call."""
    low = text.lower()
    lots = st["farmer"]["lots"]
    if tool == "retail_price" and not SHOP.search(text):
        tool = "price_at"  # the small model mixes "rate" with retail: shop words decide
    if tool == "best_mandi":
        return A.run_tool("compare", {}, st, L, db)
    if tool == "price_at":
        return A._price_of(low, st["plan"], L, crop=_crop_key(a.get("crop"), text))
    if tool in ("forecast", "track_order"):
        return A.run_tool(tool, {}, st, L, db)
    if tool == "sell_or_hold":
        return A.run_tool("explain_decision", {}, st, L, db)
    if tool in ("storage", "transport"):
        return A.run_tool("logistics", {}, st, L, db)
    if tool == "add_crop":
        crop = _crop_key(a.get("crop"), text)
        if not crop:
            return None
        q = P.extract(text).get("qty") or (P.qty(float(a["qty"]), a.get("unit") or intake.last_unit(lots) or "quintal")
                                          if isinstance(a.get("qty"), (int, float)) and 0 < a["qty"] <= 100000 else None)
        if not q:
            st["await"] = {"crop": crop}
            return {"reply": intake._t("qty", L, crop=intake.crop_label(crop, L)), "actions": []}
        return A._set_lot({"crop": crop, "qty": q}, st, L, db)
    if tool == "remove_crop":
        crop = _crop_key(a.get("crop"), text)
        return A._remove_lot(crop, st, L, db) if crop else None
    if tool == "change_quantity":
        q = P.extract(text).get("qty") or (P.qty(float(a["qty"]), a.get("unit") or "quintal") if isinstance(a.get("qty"), (int, float)) and a["qty"] > 0 else None)
        return A._set_lot({"crop": st["active"], "qty": q}, st, L, db, key="qty_set") if q else None
    if tool == "change_place":
        return A.run_tool("set_location", {"text": a.get("place") or text}, st, L, db)
    if tool == "set_cost":
        k = COST.get(str(a.get("name", "")).lower())
        return A.run_tool("set_assumption", {k: float(a["value"])}, st, L, db) if k and isinstance(a.get("value"), (int, float)) else None
    if tool == "create_order":
        return {"confirm": ("create_order", {})}
    if tool in ("book_transport", "book_storage"):
        ev = "request_transport" if tool == "book_transport" else "request_storage"
        return {"confirm": ("order_event", {"event": ev})} if st.get("order_id") or ev == "request_storage" else {"reply": A.rt(L, "no_order"), "actions": []}
    if tool == "retail_price":
        return A.run_tool("retail", {"crop": _crop_key(a.get("crop"), text), "city": a.get("city") or ""}, st, L, db)
    if tool == "show_schemes":  # the farmer's own words win; the model's args only fill what the words did not say
        said = SC.parse(text)
        m_state = SC.parse(str(a.get("state") or "")).get("state")
        m_q = SC.parse(str(a.get("scheme") or "")).get("q")
        return A.run_tool("schemes", {"state": said.get("state") or m_state, "category": said.get("category") or a.get("category"),
                                      "q": said.get("q") or m_q}, st, L, db)
    if tool == "switch_language" and a.get("lang") in ("en", "hi", "mr") and LANGWORD.search(text):  # only when a language is named
        return A.run_tool("set_language", {"lang": a["lang"]}, st, L, db)
    if tool in ("explain", "chat"):
        sp = SC.parse(text)
        extra = (" | " + SC.facts_text(sp.get("state") or A._farm_state(st), sp.get("category"), sp.get("q"))) if sp or A.SCHEME_RX.search(text.lower()) else ""
        ans = llm.grounded_answer(text, facts(st) + extra, L, recent(st))
        return {"reply": ans or A._best_msg(st["plan"], L), "actions": []}
    return None


def run(text: str, st: dict, L: str, db, pre: list, trace: list, force: str | None = None) -> dict | None:
    """-> {"reply", "actions", "state", ...} or None when the model gave nothing usable (caller falls back to rules)."""
    f = P.extract(text)
    ctx = {"current_crop": CR.name(st["active"], "en"), "my_crops": [CR.name(c, "en") for c in st["farmer"]["lots"]],
           "farm": st["farmer"]["location"]["name"], "crop_words": f.get("crop"), "has_order": bool(st.get("order_id")), "recent": recent(st)}
    calls = [{"tool": force, "args": {}}] if force else llm.plan_tools(text, ctx)
    if not calls:
        return None
    replies, actions = [], list(pre)
    for c in calls:
        res = _exec(c["tool"], c["args"], text, st, L, db)
        trace.append({"tool": "llm:" + c["tool"], "args": {k: v for k, v in c["args"].items() if k in ("crop", "place", "city", "state", "name", "value", "lang", "qty", "unit")}})
        if res is None:
            continue
        if res.get("confirm"):
            tool, args = res["confirm"]
            st["pending"] = {"tool": tool, "args": args}
            replies.append(A.rt(L, "confirm", what=A._confirm_text(tool, args, L)))
            return {"reply": " ".join(replies), "actions": actions, "state": "confirming_action",
                    "chips": [{"en": "Yes", "hi": "हाँ", "mr": "होय"}[L], {"en": "No", "hi": "नहीं", "mr": "नाही"}[L]]}
        if res.get("lang"):
            L = res["lang"]
        if res.get("reply") and not any(res["reply"] in r or r in res["reply"] for r in replies):
            replies.append(res["reply"])
        actions += res.get("actions", [])
    if not replies:
        return None
    return {"reply": " ".join(replies), "actions": actions, "state": "plan", "lang": L}
