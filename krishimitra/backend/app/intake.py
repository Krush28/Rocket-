"""Multi-crop voice intake: 'I grow onion and tomato' -> asks quantity for each, then village, readiness, storage; reads everything back
and waits for a yes before anything is stored or any market work starts. English / Hindi / Marathi. Rules only (works offline, no LLM needed)."""
import re

from . import inventory, profile as P

SEP = re.compile(r"\s*[,;&]\s*|\s+(?:and|और|आणि|तथा|व)\s+", re.I)  # whole words only: \b is unreliable around Devanagari marks
S: dict = {}

T = {
    "greet": {"en": "Namaste! I am KrishiMitra. Tell me which crops you grow. You can name several.",
              "hi": "नमस्ते! मैं कृषिमित्र हूँ। बताइए आप कौन सी फसलें उगाते हैं। आप कई नाम बता सकते हैं।",
              "mr": "नमस्कार! मी कृषिमित्र. तुम्ही कोणती पिके घेता ते सांगा. तुम्ही अनेक नावे सांगू शकता."},
    "qty": {"en": "How much {crop} do you have? Say the amount with kg, quintal or tonne.", "hi": "आपके पास कितना {crop} है? किलो, क्विंटल या टन में बताइए।",
            "mr": "तुमच्याकडे किती {crop} आहे? किलो, क्विंटल किंवा टनमध्ये सांगा."},
    "crops_again": {"en": "I know onion, tomato and potato. Which of these do you grow?", "hi": "मुझे प्याज, टमाटर और आलू पता हैं। इनमें से आप कौन सी उगाते हैं?",
                    "mr": "मला कांदा, टोमॅटो आणि बटाटा माहीत आहेत. यापैकी तुम्ही कोणते घेता?"},
    "ok": {"en": "Got it: {list}.", "hi": "ठीक है: {list}।", "mr": "समजले: {list}."},
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


def _t(key, lang, **kw):
    return T[key][lang if lang in T[key] else "en"].format(**kw)


def lots_text(s_or_lots, lang, order=None):
    lots = s_or_lots
    out = []
    for c in order or list(lots):
        q = lots[c]
        kg_unit = q["original_unit"].lower() in ("kg", "kgs", "kilogram", "kilograms", "किलो", "किग्रा")
        out.append(f"{P.NAMES[c][lang]} {q['original_qty']:g} {q['original_unit']}" + ("" if kg_unit else f" ({q['qty_kg']:,.0f} kg)"))
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


def _apply(s, text, aw):
    found = False
    for seg in [x for x in SEP.split(text) if x.strip()]:
        f = P.extract(seg, "qty" if aw == "qty" else None)
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


def _reply(s, text, **extra):
    return {"reply": text, "lang": s["lang"], "awaiting": s["awaiting"], "done": False, **extra}


def step(sid: str, text: str, lang: str | None = None) -> dict:
    s = S.get(sid) or new(sid, lang or "en")
    text = (text or "").strip()
    s["lang"] = lang or P.detect_lang(text, s["lang"])
    L = s["lang"]
    if not s["started"]:
        s["started"] = True
        if not text:
            return _reply(s, _t("greet", L))
    aw = s["awaiting"]
    if aw == "confirm":
        found = _apply(s, text, None)
        yn = P.yes_no(text)
        if not found and yn is True:
            data = {"location": s["location"], "ready": s["ready"], "can_store": s["can_store"], "lang": L,
                    "lots": {c: s["lots"][c] for c in s["crops"]}}
            inventory.save(sid, data)
            S.pop(sid, None)
            return {"reply": P.START[L], "lang": L, "awaiting": None, "done": True, "farmer": data}
        if not found:
            s["awaiting"] = None
            return _reply(s, P.FIX[L])
    else:
        if not _apply(s, text, aw):
            hint = _t("crops_again", L) if aw == "crops" else ""
            q = _question(s, aw, L)
            return _reply(s, P.UNKNOWN[L] + (hint or q))
    aw, crop = _missing(s)
    s["awaiting"], s["await_crop"] = aw, crop
    if aw == "confirm":
        yn = (lambda b, k: _t(k + ("_y" if b else "_n"), L))
        body = _t("read", L, lots=lots_text(s["lots"], L, s["crops"]), loc=s["location"]["name"], ready=yn(s["ready"], "ready"), store=yn(s["can_store"], "store"))
        return _reply(s, body + " " + P.CONFIRM_TAIL[L])
    return _reply(s, _question(s, aw, L))


def _question(s, aw, L):
    if aw == "qty":
        return _t("qty", L, crop=P.NAMES[s["await_crop"] or s["crops"][0]][L])
    if aw == "crops" or aw is None:
        return _t("crops_again", L)
    return P.Q[aw][L]


def welcome_back(farmer, L):
    crops = list(farmer["lots"])
    return _t("back", L, list=lots_text(farmer["lots"], L), first=P.NAMES[crops[0]][L])
