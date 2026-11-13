"""Multi-crop voice intake (ported from Rocket): 'I grow onion and tomato' -> quantity per crop -> village -> ready -> can store ->
read-back -> yes. Nothing is stored and no market work starts before the yes. English / Hindi / Marathi, rules only (fast, offline).
Any crop in the price feed is accepted; any Indian place is geocoded. State is saved per session (survives restarts)."""
import re
import time

from app.conversation import profile_agent as P
from app.repositories import farmers, sessions as SS

SEP = re.compile(r"\s*[,;&]\s*|\s+(?:and|aur|ani|plus|और|आणि|तथा|व)\s+", re.I)  # whole words only: \b is unreliable around Devanagari marks
S: dict = {}  # hot cache of intake state; the DB copy is the source of truth
STALE_S = 30 * 60  # an unfinished intake untouched this long is dropped: the farmer starts fresh instead of resuming a half-done task

T = {
    "greet": {"en": "Namaste! I am KRISHI-X. Tell me which crops you want to sell. You can name several.",
              "hi": "नमस्ते! मैं कृषि-एक्स हूँ। बताइए आप कौन सी फसलें बेचना चाहते हैं। आप कई नाम बता सकते हैं।",
              "mr": "नमस्कार! मी कृषि-एक्स. तुम्हाला कोणती पिके विकायची आहेत ते सांगा. तुम्ही अनेक नावे सांगू शकता."},
    "qty": {"en": "How much {crop} do you have? Say the amount with kg, quintal or tonne.", "hi": "आपके पास कितना {crop} है? किलो, क्विंटल या टन में बताइए।",
            "mr": "तुमच्याकडे किती {crop} आहे? किलो, क्विंटल किंवा टनमध्ये सांगा."},
    "crops_again": {"en": "Which crops do you want to sell? For example onion, tomato or wheat.", "hi": "आप कौन सी फसलें बेचना चाहते हैं? जैसे प्याज, टमाटर या गेहूं।",
                    "mr": "तुम्हाला कोणती पिके विकायची आहेत? उदा. कांदा, टोमॅटो किंवा गहू."},
    "read": {"en": "I understood: {lots}. Farm near {loc}. {ready}. {store}.", "hi": "मैंने समझा: {lots}। खेत {loc} के पास। {ready}। {store}।",
             "mr": "मला समजले: {lots}. शेत {loc} जवळ. {ready}. {store}."},
    "ready_y": {"en": "Ready to sell now", "hi": "अभी बिक्री के लिए तैयार", "mr": "आता विक्रीसाठी तयार"},
    "ready_n": {"en": "Not ready yet", "hi": "अभी तैयार नहीं", "mr": "अजून तयार नाही"},
    "store_y": {"en": "You can store it", "hi": "आप भंडारण कर सकते हैं", "mr": "तुम्ही साठवू शकता"},
    "store_n": {"en": "You cannot store it", "hi": "भंडारण संभव नहीं", "mr": "साठवण शक्य नाही"},
    "back": {"en": "Welcome back! I remember {list}. Showing {first} first. Say another crop's name to switch.",
             "hi": "वापसी पर स्वागत है! मुझे याद है: {list}। पहले {first} दिखा रहा हूँ। दूसरी फसल का नाम बोलकर बदलिए।",
             "mr": "पुन्हा स्वागत! मला आठवते: {list}. आधी {first} दाखवतो. दुसरे पीक बदलण्यासाठी त्याचे नाव सांगा."},
}
UNIT = {"hi": {"kg": "किलो", "quintal": "क्विंटल", "tonne": "टन"}, "mr": {"kg": "किलो", "quintal": "क्विंटल", "tonne": "टन"}}


def _t(key, lang, **kw):
    return T[key][lang if lang in T[key] else "en"].format(**kw)


def crop_label(c: str, lang: str) -> str:
    return P.NAMES.get(c, {}).get(lang, c)


def unit_label(u: str, lang: str) -> str:
    base = {"kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg", "किलो": "kg", "किग्रा": "kg", "quintals": "quintal", "qtl": "quintal",
            "qtls": "quintal", "क्विंटल": "quintal", "tonnes": "tonne", "ton": "tonne", "tons": "tonne", "टन": "tonne"}.get(u.lower(), u.lower())
    return UNIT.get(lang, {}).get(base, u)


def lots_text(lots: dict, lang: str, order=None) -> str:
    out = []
    for c in order or list(lots):
        q = lots[c]
        kg = P.UNIT_KG.get(q["original_unit"].lower()) == 1
        out.append(f"{crop_label(c, lang)} {q['original_qty']:g} {unit_label(q['original_unit'], lang)}"
                   + ("" if kg else f" ({q['qty_kg']:,.0f} {unit_label('kg', lang)})"))
    return ", ".join(out)


def new(sid, lang="en"):
    S[sid] = {"lang": lang, "crops": [], "lots": {}, "location": None, "ready": None, "can_store": None, "awaiting": "crops", "await_crop": None, "started": False}
    return S[sid]


def _missing(s):
    if not s["crops"]:
        return "crops", None
    for c in s["crops"]:
        if c not in s["lots"]:
            return "qty", c
    if not s["location"]:
        return "location", None
    if s["ready"] is None:
        return "ready", None
    if s["can_store"] is None:
        return "can_store", None
    return "confirm", None


def _apply(s, text, aw, db):
    found = False
    segs = [text] if aw == "location" else [x for x in SEP.split(text) if x.strip()]  # "Ponda, Goa" is one place
    unit = last_unit(s["lots"])
    for seg in segs:
        f = P.extract(seg, "qty" if aw in ("qty", "crops") else ("location" if aw == "location" else None), db=db)
        if "qty" in f:
            unit = f["qty"]["original_unit"]
        elif "bare_qty" in f and unit:  # "50 quintal onion and 20 potato": the 20 is quintal too
            f["qty"] = P.qty(f["bare_qty"], unit)
        if "crop" in f:
            if f["crop"] not in s["crops"]:
                s["crops"].append(f["crop"])
            found = True
            if "qty" in f:
                s["lots"][f["crop"]] = f["qty"]
        elif "qty" in f and aw == "qty" and s["await_crop"]:
            s["lots"][s["await_crop"]] = f["qty"]
            found = True
        if "location" in f:
            s["location"] = f["location"]
            found = True
    if text and (not found or len(text.split()) >= 6) and aw not in ("ready", "can_store"):
        found = _apply_llm(s, text, aw, db) or found  # free speech: "do ton baingan hai Satara ke paas, abhi taiyar"
    if aw in ("ready", "can_store"):
        yn = P.yes_no(text)
        if yn is not None:
            s[aw] = yn
            found = True
    else:
        f = P.extract(text)
        for k in ("ready", "can_store"):
            if k in f:
                s[k] = f[k]
                found = True
    return found


def _apply_llm(s, text, aw, db) -> bool:
    """Local LLM extraction (only when enabled, sentences of 4+ words): crops, amounts and place the rules missed.
    Guards against invention: a crop is kept only if one of its names is in the text, an amount only if that number is in the text,
    a place only if it is in the text. Ready / storage come from rules only. Never overwrites rule results."""
    from app.services import llm
    from app.repositories import market_data as MD
    if len(text.split()) < 4:
        return False
    d = llm.extract_intake(text, aw)
    if not d:
        return False
    norm = P.NUMW_RX.sub(lambda m: f"{P.NUMW[m.group(1).lower()]} {m.group(2)}", text.translate(P.DEV)).lower()
    nums = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", norm)}
    cat = MD.crop_catalogue()
    found = False
    for c in d.get("crops") or []:
        name = str(c.get("crop", ""))
        key = P._crop(name.translate(P.DEV), name.lower())
        if not key or not any(a.lower() in norm for a in cat.get(key, []) + [key] if len(a) >= 3):
            continue
        if key not in s["crops"]:
            s["crops"].append(key)
        found = True
        q = c.get("qty")
        if key not in s["lots"] and isinstance(q, (int, float)) and float(q) in nums and 0 < q <= 100000:
            unit = c.get("unit") if c.get("unit") and c["unit"][:3] in norm.replace("क्विंटल", "quintal").replace("टन", "ton").replace("किलो", "kg") else None
            s["lots"][key] = P.qty(float(q), unit or last_unit(s["lots"]) or "quintal")
    place = (d.get("place") or "").strip()
    if place and not s["location"] and place.lower() in text.lower():
        hit = P._geocode(db, place)
        if hit:
            s["location"], found = hit, True
    return found


def last_unit(lots: dict) -> str | None:
    return next((q["original_unit"] for q in reversed(list(lots.values()))), None)


def _reply(s, text, **extra):
    return {"reply": text, "lang": s["lang"], "awaiting": s["awaiting"], "done": False, **extra}


def step(sid: str, text: str, lang: str | None = None, *, db) -> dict:
    key = f"intake:{sid}"
    s = S.get(sid) or SS.load(db, key)
    if not s or s.get("done") or time.time() - s.get("ts", 0) > STALE_S:
        s = new(sid, lang or (s or {}).get("lang") or "en")
    S[sid] = s
    r = _step(s, text, lang, db, sid)
    s["ts"] = time.time()
    if r["done"]:
        S.pop(sid, None)
        SS.save(db, key, {"done": True}, confirmed=True)
    else:
        SS.save(db, key, s, confirmed=False)
    return r


def pending(sid: str, db) -> dict | None:
    s = S.get(sid) or SS.load(db, f"intake:{sid}")
    return None if not s or s.get("done") or time.time() - s.get("ts", 0) > STALE_S else s


def forget(sid: str, db) -> None:
    S.pop(sid, None)
    SS.save(db, f"intake:{sid}", {"done": True}, confirmed=False)


def _step(s, text, lang, db, sid) -> dict:
    text = (text or "").strip()
    s["lang"] = lang or P.detect_lang(text, s["lang"])
    L = s["lang"]
    if not s["started"]:
        s["started"] = True
        if not text:
            return _reply(s, _t("greet", L))
    aw = s["awaiting"]
    if not text:  # page reload mid-intake: repeat the current question, no "sorry"
        pass
    elif aw == "confirm":
        found = _apply(s, text, None, db)
        yn = P.yes_no(text)
        if not found and yn is True:
            data = {"location": s["location"], "ready": s["ready"], "can_store": s["can_store"], "lang": L, "lots": {c: s["lots"][c] for c in s["crops"]}}
            farmers.save(db, sid, data)
            return {"reply": P.START[L], "lang": L, "awaiting": None, "done": True, "farmer": data}
        if not found:
            s["awaiting"] = None
            return _reply(s, P.FIX[L])
    elif not _apply(s, text, aw, db):
        if aw == "location":
            return _reply(s, P.PLACE_HELP[L] + " " + P.Q["location"][L])
        return _reply(s, P.UNKNOWN[L] + (_t("crops_again", L) if aw == "crops" else _question(s, aw, L)))
    aw, crop = _missing(s)
    s["awaiting"], s["await_crop"] = aw, crop
    if aw == "confirm":
        yn = (lambda b, k: _t(k + ("_y" if b else "_n"), L))
        body = _t("read", L, lots=lots_text(s["lots"], L, s["crops"]), loc=s["location"]["name"], ready=yn(s["ready"], "ready"), store=yn(s["can_store"], "store"))
        return _reply(s, body + " " + P.CONFIRM_TAIL[L])
    return _reply(s, _question(s, aw, L))


def prompt(s, L) -> str:
    """The question the farmer is currently answering (or the read-back), to repeat after an interruption."""
    aw = s.get("awaiting")
    if aw == "confirm":
        yn = (lambda b, k: _t(k + ("_y" if b else "_n"), L))
        return _t("read", L, lots=lots_text(s["lots"], L, s["crops"]), loc=s["location"]["name"], ready=yn(s["ready"], "ready"),
                  store=yn(s["can_store"], "store")) + " " + P.CONFIRM_TAIL[L]
    return _question(s, aw, L) if s.get("started") else _t("greet", L)


def _question(s, aw, L):
    if aw == "qty":
        return _t("qty", L, crop=crop_label(s["await_crop"] or s["crops"][0], L))
    if aw == "crops" or aw is None:
        return _t("crops_again", L)
    return P.Q[aw][L]


def welcome_back(farmer, L):
    return _t("back", L, list=lots_text(farmer["lots"], L), first=crop_label(next(iter(farmer["lots"])), L))
