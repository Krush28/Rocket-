"""Farmer Profile Agent: multilingual (en/hi/mr) slot-filling conversation. Rules first; optional local LLM can add slots (llm.py).
One question at a time, only missing slots, corrections allowed, read-back + explicit confirmation before any market work."""
import re
from datetime import date, timedelta

from sqlalchemy import select

from app.db import database
from app.models import Commodity, FarmerInventory, FarmerProfile
from app.repositories import market_data as MD
from app.repositories import sessions as SS
from app.services import demo_data, geocoding
from app.services import llm

REQUIRED = ["crop", "qty", "location", "ready", "can_store"]
UNIT_KG = {"kg": 1, "kgs": 1, "kilogram": 1, "kilograms": 1, "किलो": 1, "किग्रा": 1, "quintal": 100, "quintals": 100, "qtl": 100,
           "क्विंटल": 100, "tonne": 1000, "tonnes": 1000, "ton": 1000, "tons": 1000, "टन": 1000}
YES = ["yes", "yeah", "yep", "ready", "haan", "han", "ha ", "हां", "हाँ", "हो", "होय", "आहे", "तयार", "correct", "right", "sahi", "सही", "बरोबर", "ok", "okay", "sure"]
NO = ["no", "not", "nahi", "nahin", "नहीं", "नही", "नाही", "nope", "later", "नको", "नाहीं"]
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
MARATHI_MARKERS = ["आहे", "मला", "माझ", "कांदा", "नाही", "तयार", "आहेत", "बटाटा", "टोमॅटो", "होय", "आहेत"]

NAMES = {"onion": {"en": "onion", "hi": "प्याज", "mr": "कांदा"}, "tomato": {"en": "tomato", "hi": "टमाटर", "mr": "टोमॅटो"},
         "potato": {"en": "potato", "hi": "आलू", "mr": "बटाटा"}}
Q = {
    "crop": {"en": "Which crop do you want to sell? (for example onion, tomato, wheat)", "hi": "आप कौन सी फसल बेचना चाहते हैं? (जैसे प्याज, टमाटर, गेहूं)",
             "mr": "तुम्हाला कोणते पीक विकायचे आहे? (उदा. कांदा, टोमॅटो, गहू)"},
    "qty": {"en": "How much do you have? Say the amount with kg, quintal or tonne.", "hi": "आपके पास कितना माल है? किलो, क्विंटल या टन में बताइए।",
            "mr": "तुमच्याकडे किती माल आहे? किलो, क्विंटल किंवा टनमध्ये सांगा."},
    "location": {"en": "Where is your farm? Tell me your village or nearest town.", "hi": "आपका खेत कहाँ है? गाँव या नज़दीकी शहर बताइए।",
                 "mr": "तुमचे शेत कुठे आहे? गाव किंवा जवळचे शहर सांगा."},
    "ready": {"en": "Is your produce ready for sale now?", "hi": "क्या आपका माल अभी बिक्री के लिए तैयार है?", "mr": "तुमचा माल आता विक्रीसाठी तयार आहे का?"},
    "can_store": {"en": "Can you store the produce for a few days if it pays more? (yes or no)", "hi": "क्या आप ज़्यादा भाव मिलने पर माल कुछ दिन रख सकते हैं? (हाँ या नहीं)",
                  "mr": "जास्त भाव मिळाल्यास तुम्ही माल काही दिवस ठेवू शकता का? (होय किंवा नाही)"},
}
UNKNOWN = {"en": "Sorry, I did not catch that. ", "hi": "माफ़ कीजिए, मैं समझ नहीं पाया। ", "mr": "माफ करा, मला समजले नाही. "}
PLACE_HELP = {"en": "I could not find that place. Please say the village or town with its district, for example 'Ponda, North Goa'.",
              "hi": "यह जगह नहीं मिली। कृपया गाँव या शहर और उसका ज़िला बताइए, जैसे 'पोंडा, उत्तर गोवा'।",
              "mr": "हे ठिकाण सापडले नाही. कृपया गाव किंवा शहर आणि त्याचा जिल्हा सांगा, उदा. 'पोंडा, उत्तर गोवा'."}
NEAR = re.compile(r"\bnear\s+([^\d]+?)\s*[.!?]*$", re.I)
LEAD = re.compile(r"^\s*(?:my\s+farm\s+is|farm\s+is|it\s+is|it's|i\s+am|i'm)?\s*(?:in|at|near)?\s+", re.I)
CONFIRM_TAIL = {"en": "Is this correct?", "hi": "क्या यह सही है?", "mr": "हे बरोबर आहे का?"}
FIX = {"en": "What should I change? You can say the crop, amount, place, readiness or storage again.",
       "hi": "क्या बदलना है? फसल, मात्रा, जगह या भंडारण फिर से बताइए।", "mr": "काय बदलायचे आहे? पीक, प्रमाण, ठिकाण किंवा साठवण पुन्हा सांगा."}
START = {"en": "I will now compare nearby mandi prices, expected future prices, buyer options and transport costs.",
         "hi": "अब मैं पास की मंडियों के भाव, आगे के संभावित भाव, खरीदार और ढुलाई का खर्च देखता हूँ।",
         "mr": "आता मी जवळच्या मंडईंचे भाव, पुढील संभाव्य भाव, खरेदीदार आणि वाहतूक खर्च तपासतो."}
GREET = {"en": "Namaste! I am KRISHI-X. I help you find where you will earn the most after costs. ",
         "hi": "नमस्ते! मैं कृषि-एक्स हूँ। मैं बताता हूँ कि सारे खर्च के बाद कहाँ सबसे ज़्यादा कमाई होगी। ",
         "mr": "नमस्कार! मी कृषि-एक्स. सर्व खर्चानंतर कुठे सर्वाधिक कमाई होईल ते मी सांगतो. "}
YN = {"en": ("yes", "no"), "hi": ("हाँ", "नहीं"), "mr": ("होय", "नाही")}

SESSIONS: dict = {}


def detect_lang(text: str, current: str | None = None) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "mr" if any(m in text for m in MARATHI_MARKERS) else "hi"
    return current or "en"


def _has(text, words):
    t = f" {text.lower()} "
    return any((f" {w.strip()} " in t) or (w.strip() and not w.isascii() and w in t) for w in words)


def yes_no(text: str):
    t = text.lower().translate(DEV)
    if _has(t, NO):
        return False
    if _has(t, YES):
        return True
    return None


def _crop(t: str, low: str) -> str | None:
    """Longest alias wins; ASCII aliases need word boundaries (so 'price' never matches 'rice'), plural -s/-es allowed."""
    pairs = sorted(((a, k) for k, al in MD.crop_catalogue().items() for a in al), key=lambda p: -len(p[0]))
    for a, k in pairs:
        if (a.isascii() and re.search(rf"\b{re.escape(a)}(?:e?s)?\b", low)) or (not a.isascii() and a in t):
            return k
    return None


def _geocode(db, place: str) -> dict | None:
    place = place.strip(" .,!?")
    if not re.search(r"[^\W\d_]", place):
        return None
    if db is not None:
        return geocoding.geocode(db, place)
    with database.SessionLocal() as s:
        return geocoding.geocode(s, place)


def extract(text: str, awaiting: str | None = None, db=None) -> dict:
    t = text.translate(DEV).replace(",", "")
    low = t.lower()
    out = {}
    crop = _crop(t, low)
    if crop:
        out["crop"] = crop
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kilograms?|kgs?|quintals?|qtl|tonnes?|tons?|किलो|किग्रा|क्विंटल|टन)?", low)
    if m and (m.group(2) or awaiting == "qty"):
        unit = m.group(2) or "kg"
        val = float(m.group(1))
        if val > 0:
            out["qty"] = {"original_qty": val, "original_unit": unit, "qty_kg": val * UNIT_KG[unit]}
    for key in sorted(demo_data.PLACES, key=len, reverse=True):
        if (key.isascii() and re.search(rf"\b{re.escape(key)}\b", low)) or (not key.isascii() and key in t):
            out["location"] = {"name": key.title() if key.isascii() else key, "lat": demo_data.PLACES[key][0], "lon": demo_data.PLACES[key][1],
                               "status": "approximate"}
            break
    if "location" not in out:  # any Indian place: "... near <place>", or the whole answer when we asked for the location
        near = NEAR.search(text.translate(DEV))
        place = near.group(1) if near else (LEAD.sub("", " " + text) if awaiting == "location" and not ({"crop", "qty"} & out.keys()) else None)
        hit = _geocode(db, place) if place else None
        if hit:
            out["location"] = hit
    if awaiting in ("ready", "can_store"):
        yn = yes_no(t)
        if yn is not None:
            out[awaiting] = yn
    else:
        if re.search(r"\bnot ready\b|\bnot yet\b", low):
            out["ready"] = False
        elif re.search(r"\bready\b|तयार", low):
            out["ready"] = True
        if re.search(r"can store|storage available|have storage|can keep", low):
            out["can_store"] = True
        elif re.search(r"cannot store|can't store|no storage|cant store", low):
            out["can_store"] = False
    g = re.search(r"grade\s*([abc])\b", low)
    if g:
        out["grade"] = g.group(1).upper()
    v = re.search(r"\b(red|white|yellow|local|hybrid|desi)\b", low)
    if v:
        out["variety"] = v.group(1)
    if "yesterday" in low:
        out["harvest_date"] = str(date.today() - timedelta(days=1))
    elif "today" in low:
        out["harvest_date"] = str(date.today())
    d = re.search(r"(\d+)\s*days? ago", low)
    if d:
        out["harvest_date"] = str(date.today() - timedelta(days=int(d.group(1))))
    if re.search(r"urgent|asap|need cash|quick|jaldi|तुरंत|लगेच", low):
        out["sell_pref"] = "fast_cash"
    elif re.search(r"best price|wait for|can wait|हो सके तो इंतज़ार", low):
        out["sell_pref"] = "best_price"
    return out


def new_session(sid: str, lang: str = "en") -> dict:
    s = {"id": sid, "lang": lang, "slots": {}, "state": "collecting", "awaiting": None, "history": []}
    SESSIONS[sid] = s
    return s


def _missing(s):
    return [k for k in REQUIRED if k not in s["slots"]]


def _readback(s):
    sl, L = s["slots"], s["lang"]
    crop = NAMES.get(sl["crop"], {}).get(L, sl["crop"])
    q = sl["qty"]
    qty = f"{q['original_qty']:g} {q['original_unit']} ({q['qty_kg']:,.0f} kg)"
    yn = YN[L]
    parts = {"en": f"I understood: {qty} of {crop} near {sl['location']['name']}, {'ready now' if sl['ready'] else 'not ready yet'}, "
                   f"{'can store' if sl['can_store'] else 'cannot store'}.",
             "hi": f"मैंने समझा: {sl['location']['name']} के पास {qty} {crop}, {'अभी तैयार' if sl['ready'] else 'अभी तैयार नहीं'}, "
                   f"{'भंडारण संभव' if sl['can_store'] else 'भंडारण नहीं'}।",
             "mr": f"मला समजले: {sl['location']['name']} जवळ {qty} {crop}, {'आता तयार' if sl['ready'] else 'अजून तयार नाही'}, "
                   f"{'साठवण शक्य' if sl['can_store'] else 'साठवण नाही'}."}
    del yn
    return parts[L] + " " + CONFIRM_TAIL[L]


def chat(sid: str, text: str, lang: str | None = None, *, db=None) -> dict:
    """One conversation turn. With `db`, state is loaded from and saved to conversation_sessions (survives restarts)."""
    s = SESSIONS.get(sid) or (SS.load(db, sid) if db is not None else None)
    if s:
        SESSIONS[sid] = s
    else:
        s = new_session(sid, lang or "en")
    r = _turn(s, text, lang, db)
    if db is not None:
        SS.save(db, sid, s, confirmed=s["state"] == "confirmed")
    return r


def _turn(s: dict, text: str, lang: str | None, db) -> dict:
    text = (text or "").strip()
    first = not s["history"] and not text
    s["lang"] = lang or detect_lang(text, s["lang"])
    L = s["lang"]
    s["history"].append(("farmer", text))
    if first or (not text and not s["slots"]):
        s["awaiting"] = "crop"
        return _reply(s, GREET[L] + Q["crop"][L])
    if s["state"] == "confirming":
        yn = yes_no(text)
        found = extract(text, db=db)
        if found:
            s["slots"].update(found)
            s["state"] = "collecting"
        elif yn is True:
            s["state"] = "confirmed"
            return _reply(s, START[L], done=True)
        else:
            s["state"] = "collecting"
            s["awaiting"] = None
            return _reply(s, FIX[L])
    else:
        found = extract(text, s["awaiting"], db=db)
        if llm.enabled():
            for k, v in (llm.extract_slots(text, s["slots"]) or {}).items():
                found.setdefault(k, v)
        s["slots"].update(found)
        if not found:
            if s["awaiting"] == "location":  # unknown place, or geocoder unreachable: ask again, never guess
                return _reply(s, PLACE_HELP[L] + " " + Q["location"][L])
            return _reply(s, UNKNOWN[L] + Q[s["awaiting"] or "crop"][L])
    miss = _missing(s)
    if miss:
        s["awaiting"] = miss[0]
        return _reply(s, Q[miss[0]][L])
    s["state"] = "confirming"
    s["awaiting"] = "confirm"
    return _reply(s, _readback(s))


def _reply(s, text, done=False):
    s["history"].append(("krishimitra", text))
    sl = s["slots"]
    prof = None
    if done:
        q = sl["qty"]
        prof = {"crop": sl["crop"], "qty_kg": q["qty_kg"], "original_qty": q["original_qty"], "original_unit": q["original_unit"],
                "location": sl["location"], "ready": sl["ready"], "can_store": sl["can_store"], "variety": sl.get("variety"),
                "grade": sl.get("grade"), "harvest_date": sl.get("harvest_date"), "sell_pref": sl.get("sell_pref"), "lang": s["lang"]}
    if done:
        s["profile"] = prof  # kept in the session so /api/plan can re-run without re-asking
    return {"reply": text, "lang": s["lang"], "state": s["state"], "awaiting": s["awaiting"], "slots": sl, "done": done, "profile": prof}


def on_confirm(db, sid: str, profile: dict) -> int:
    """Persist a CONFIRMED profile as farmer_profiles + farmer_inventory; returns the inventory id."""
    from datetime import date as _date
    loc = profile["location"]
    fp = db.scalar(select(FarmerProfile).where(FarmerProfile.session_id == sid))
    if not fp:
        fp = FarmerProfile(session_id=sid, location_name=loc["name"])
        db.add(fp)
    fp.location_name, fp.lat, fp.lon = loc["name"], loc.get("lat"), loc.get("lon")
    fp.preferred_language, fp.can_store, fp.sell_pref = profile.get("lang") or "en", bool(profile["can_store"]), profile.get("sell_pref")
    db.flush()
    hd = profile.get("harvest_date")
    inv = FarmerInventory(farmer_profile_id=fp.id, crop_key=profile["crop"],
                          commodity_id=db.scalar(select(Commodity.id).where(Commodity.key == profile["crop"])),
                          variety=profile.get("variety"), grade=profile.get("grade"), qty_kg=profile["qty_kg"],
                          original_qty=profile["original_qty"], original_unit=profile["original_unit"],
                          harvest_date=_date.fromisoformat(hd) if hd else None, ready=bool(profile["ready"]))
    db.add(inv)
    db.commit()
    return inv.id
