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
UNIT_KG = {"kg": 1, "kgs": 1, "kilo": 1, "kilos": 1, "kilogram": 1, "kilograms": 1, "qtls": 100, "किलो": 1, "किग्रा": 1, "quintal": 100, "quintals": 100, "qtl": 100,
           "क्विंटल": 100, "tonne": 1000, "tonnes": 1000, "ton": 1000, "tons": 1000, "टन": 1000}
YES = ["yes", "yeah", "yep", "y", "ready", "haan", "han", "ha", "haa", "ho", "hoy", "ji", "हां", "हाँ", "हा", "जी", "हो", "होय", "आहे", "तयार", "correct", "right",
       "sahi", "सही", "बरोबर", "ok", "okay", "sure", "theek", "ठीक"]
NO = ["no", "n", "na", "not", "nahi", "nahin", "nako", "nai", "नहीं", "नही", "ना", "नाही", "nope", "later", "नको", "नाहीं", "cannot", "can't"]
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
MARATHI_MARKERS = ["आहे", "मला", "माझ", "कांदा", "नाही", "आहेत", "बटाटा", "टोमॅटो", "होय", "कुठे", "विकू", "काय", "किती", "करा", "दाखवा", "सांगा",
                   "शेत", "जवळ", "आणि", "मध्ये", "नको", "पण", "तुम्ही", "आम्ही", "मराठी"]
HINDI_MARKERS = ["है", "हैं", "में", "क्या", "कहाँ", "कहां", "मेरे", "मेरा", "मुझे", "बेचूँ", "बेचूं", "कितना", "और", "नहीं", "हाँ", "करो", "बताओ", "हिंदी"]

from app.services import crops as CR  # noqa: E402
from app.services.crops import NAMES  # noqa: E402  every crop's Hindi/Marathi name
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
CANCEL = ["cancel", "never mind", "nevermind", "forget it", "leave it", "stop that", "skip it", "रहने दो", "छोड़ो", "छोड़ दो", "रद्द करो", "रद्द कर दो",
          "जाने दो", "राहू द्या", "सोडा", "सोडून द्या", "रद्द करा", "जाऊ द्या"]


def is_cancel(text: str) -> bool:
    """'cancel' / 'never mind' drops a half-done step; 'cancel the order' is an order action and is NOT this."""
    low = text.lower()
    return any(w in low for w in CANCEL) and not re.search(r"order|ऑर्डर", low)


YN = {"en": ("yes", "no"), "hi": ("हाँ", "नहीं"), "mr": ("होय", "नाही")}

SESSIONS: dict = {}


def detect_lang(text: str, current: str | None = None) -> str:
    """Devanagari is Hindi or Marathi: count marker words; a tie keeps the farmer's current language (so 'कांदा 50' stays Marathi)."""
    if re.search(r"[ऀ-ॿ]", text):
        mr, hi = sum(m in text for m in MARATHI_MARKERS), sum(m in text for m in HINDI_MARKERS)
        return "mr" if mr > hi or (mr == hi and current == "mr") else "hi"
    return current or "en"


def _has(text, words):
    t = f" {text.lower()} "
    return any((f" {w.strip()} " in t) or (w.strip() and not w.isascii() and w in t) for w in words)


_PUNCT = re.compile(r"[\s.,!?;:।॥|\"'“”‘’()\[\]\-–—/]+")
YES_PH = ["yes", "yeah", "yea", "yep", "yup", "ya", "y", "yess", "haan", "han", "haa", "ha", "hm", "hmm", "ho", "hoy", "ji", "haanji", "ok", "okay", "okk",
          "sure", "right", "correct", "perfect", "fine", "good", "great", "done", "sahi", "theek", "thik", "bilkul", "zaroor", "jaroor", "chalega",
          "chalo", "kar do", "kardo", "karo", "proceed", "confirm", "confirmed", "go ahead", "go on", "do it", "please do", "of course", "absolutely",
          "definitely", "ready", "sell it", "book it", "agreed", "go for it", "bana do", "bana dijiye", "kar dijiye", "kar dena", "order kar do", "बना दो", "बना दीजिए", "carry on", "lets do it", "let s do it", "sounds good", "alright", "all right", "fair enough", "हाँ", "हां", "हा", "जी", "हो", "होय", "ठीक", "सही", "बरोबर", "बिल्कुल", "बिलकुल",
          "ज़रूर", "जरूर", "चलेगा", "चालेल", "कर दो", "कर दीजिए", "करो", "करा", "करून टाका", "तयार", "तैयार", "हाँजी", "ओके", "हम्म"]
NO_PH = ["no", "nope", "nah", "n", "na", "nahi", "nahin", "nai", "nako", "not", "dont", "don't", "do not", "never", "cancel", "stop", "wait", "later",
         "ruko", "ruk", "mat", "rehne do", "rahne do", "cannot", "can't", "cant", "नहीं", "नही", "ना", "नाही", "नको", "मत", "रुको", "थांबा", "नंतर",
         "बाद", "रद्द", "नाहीं"]
POS_IDIOM = ["why not", "no problem", "not a problem", "no issue", "no doubt", "not bad", "कोई बात नहीं", "हरकत नाही", "काही हरकत नाही"]
HARD_NO = ["not now", "not today", "not yet", "later", "wait", "ruko", "mat", "dont", "don't", "do not", "cancel", "stop", "cannot", "can't", "cant",
           "not ready", "nahi ho sakta", "nahi rakh", "rakh nahi", "mushkil", "difficult", "नहीं रख", "रख नहीं", "नहीं हो सकता", "कठीण",
           "can not", "do not", "will not", "wo not", "nahi kar sakta", "nahi kar sakte", "नहीं कर सकता", "नहीं कर सकते", "शक्य नाही", "taiyar nahi", "nahi taiyar", "तैयार नहीं", "तयार नाही", "अभी नहीं", "बाद में", "नंतर", "थांबा", "रुको", "मत", "रद्द"]


CHANGE = ["change", "modify", "edit", "update", "wrong", "galat", "badlo", "badal", "badla", "badlna", "बदल", "बदलो", "बदला", "बदलना", "बदलायचे",
          "गलत", "चुकीचे", "चूक", "चुकीचं"]
HEDGE = ["but", "first", "before", "pehle", "pahle", "lekin", "magar", "par pehle", "tell me", "batao", "bataiye", "how much", "kitna", "kitne", "what",
         "पहले", "लेकिन", "मगर", "बताओ", "बताइए", "कितना", "आधी", "पण आधी", "सांगा", "किती"]


_BASE_YES, _BASE_NO = list(YES_PH), list(NO_PH)


def reload_learned() -> None:
    """Phrases the bug hunter confirmed twice with the local LLM (app/qa/learned_phrases.json) extend the yes/no word lists."""
    import json
    from pathlib import Path
    f = Path(__file__).resolve().parents[1] / "qa" / "learned_phrases.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        d = {}
    YES_PH[:] = _BASE_YES + [p for p in d.get("yes", []) if p not in _BASE_YES]
    NO_PH[:] = _BASE_NO + [p for p in d.get("no", []) if p not in _BASE_NO]


def _norm(text: str) -> str:
    """Lowercase, Devanagari digits, punctuation -> spaces ("Yes, go ahead." == "yes go ahead"), padded for whole-phrase matching."""
    t = text.lower().translate(DEV).replace("’", "'")
    t = re.sub(r"\bcan't\b|\bcannot\b", "can not", t)
    t = re.sub(r"n't\b", " not", t)  # don't -> do not, won't -> wo not: the apostrophe must not hide a refusal
    return " " + " ".join(p for p in _PUNCT.split(t) if p) + " "


def hedged(text: str) -> bool:
    """A condition or a question inside the answer ("yes, but first ...", "kitna milega?"): never execute on it."""
    t = _norm(text)
    return "?" in text or any(f" {w} " in t for w in HEDGE)


reload_learned()


def yes_no(text: str):
    """Yes / no / None (unclear) for an answer to a yes-no question, in English, Hinglish, Hindi or Marathi, punctuation-proof.
    Whole words/phrases only (so नाशिक never reads as ना). Mixed answers: a hard refusal wins ("yes but not today" -> no),
    anything else mixed is unclear (the caller may ask the local LLM with the question as context)."""
    t = _norm(text)
    for p in POS_IDIOM:
        t = t.replace(f" {p} ", " yes ")
    has = lambda ws: any(f" {w} " in t for w in ws)  # noqa: E731
    if has(CHANGE):  # "quantity change karo", "galat hai", "बदला": a correction, never a yes
        return False
    pos, neg = has(YES_PH), has(NO_PH)
    if pos and not neg and ("?" in text or has(HEDGE)):
        return None  # "yes, but first tell me the price": a condition or question, not a plain yes
    if pos and not neg:
        return True
    if neg and not pos:
        return False
    if pos and neg:
        return False if has(HARD_NO) else None
    return None


def _dev_hit(a: str, t: str) -> bool:
    """Devanagari alias match. Short aliases (<=3 letters, e.g. मका, धान) must stand alone so मकान or धानोरा never match."""
    if len(a) > 3:
        return a in t
    return re.search(rf"(?<![ऀ-ॿ]){re.escape(a)}(?![ऀ-ॿ])", t) is not None


def alias_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for k, al in MD.crop_catalogue().items():  # first (curated) owner of an alias wins: "papaya" -> papaya, not papaya(raw)
        for a in al:
            m.setdefault(a, k)
    return m


def resolve_crop(text: str, use_llm: bool = True) -> str | None:
    """Any crop a farmer names: catalogue names and local names, then typos, then the local LLM picks the closest crop that has
    market data ("dragon fruit" -> none, "paddy basmati" -> paddy(basmati)). None if nothing fits."""
    t = text.translate(DEV)
    k = _crop(t, t.lower()) or CR.fuzzy(t.lower(), alias_map())
    if k or not use_llm or CR.group_of(t):
        return k
    import difflib
    from app.services import llm
    amap = alias_map()  # shortlist: crops whose names resemble a word the farmer said; the model only chooses among these
    words = [w for w in re.findall(r"[a-z]{3,}|[ऀ-ॿ]{2,}", t.lower()) if w not in CR.NOT_CROPS]
    short = list(dict.fromkeys(amap[a] for w in words for a in difflib.get_close_matches(w, list(amap), n=6, cutoff=0.55)))[:15]
    pick = llm.map_crop(text, short)
    return pick if pick and llm.same_crop(text, pick) else None  # second, independent check: never a wrong crop


def _crop(t: str, low: str) -> str | None:
    """Longest alias wins; ASCII aliases need word boundaries (so 'price' never matches 'rice'), plural -s/-es allowed."""
    pairs = sorted(((a, k) for k, al in MD.crop_catalogue().items() for a in al), key=lambda p: -len(p[0]))
    for a, k in pairs:
        if (a.isascii() and re.search(rf"\b{re.escape(a)}(?:e?s)?\b", low)) or (not a.isascii() and _dev_hit(a, t)):
            return k
    return None


def _geocode(db, place: str) -> dict | None:
    place = place.strip(" .,!?")
    if not re.search(r"[^\W\d_]", place) and not re.fullmatch(r"\d{6}", place):  # a name or a pincode
        return None
    if db is not None:
        return geocoding.geocode(db, place)
    with database.SessionLocal() as s:
        return geocoding.geocode(s, place)


NUMW = {w: n for n, ws in {
    1: "one ek एक", 2: "two do दो दोन", 3: "three teen tin तीन", 4: "four char chaar चार", 5: "five paanch panch पांच पाँच पाच",
    6: "six chhe che छह सहा", 7: "seven saat सात", 8: "eight aath आठ", 9: "nine nau नौ नऊ", 10: "ten das दस दहा", 15: "fifteen pandrah पंद्रह पंधरा",
    20: "twenty bees बीस वीस", 25: "pachees पच्चीस पंचवीस", 30: "thirty tees तीस", 40: "forty chalees चालीस चाळीस", 50: "fifty pachas pachaas पचास पन्नास",
    100: "hundred sau सौ शंभर"}.items() for w in ws.split()}
NUMW.update({  # hundreds / thousands / halves said as words ("दोनशे किलो", "दो सौ किलो", "dedh ton", "हज़ार किलो")
    "दोनशे": 200, "तीनशे": 300, "चारशे": 400, "पाचशे": 500, "सहाशे": 600, "सातशे": 700, "आठशे": 800, "नऊशे": 900, "दीडशे": 150, "अडीचशे": 250,
    "हजार": 1000, "हज़ार": 1000, "hazar": 1000, "hajar": 1000, "thousand": 1000, "दीड": 1.5, "अडीच": 2.5, "डेढ़": 1.5, "डेढ": 1.5, "ढाई": 2.5,
    "dedh": 1.5, "dhai": 2.5, "do sau": 200, "teen sau": 300, "char sau": 400, "paanch sau": 500, "panch sau": 500, "दो सौ": 200, "तीन सौ": 300,
    "चार सौ": 400, "पांच सौ": 500, "पाँच सौ": 500, "two hundred": 200, "three hundred": 300, "five hundred": 500})
NUMW_RX = re.compile(r"(?<![\wऀ-ॿ])(" + "|".join(sorted(map(re.escape, NUMW), key=len, reverse=True)) +
                     r")\s+(kilograms?|kgs?|kilos?|quintals?|qtls?|tonnes?|tons?|किलो|क्विंटल|टन)", re.I)


def extract(text: str, awaiting: str | None = None, db=None) -> dict:
    t = NUMW_RX.sub(lambda m: f"{NUMW[m.group(1).lower()]} {m.group(2)}", text.translate(DEV).replace(",", ""))  # "do ton" -> "2 ton"
    low = t.lower()
    out = {}
    crop = _crop(t, low)
    if not crop and awaiting in ("crops", "qty"):  # we asked for a crop: tolerate typos ("papya", "tamatr")
        crop = CR.fuzzy(low, alias_map())
    if crop:
        out["crop"] = crop
    else:
        g = CR.group_of(t)  # "dry fruits", "dal": the farmer named a family, not one crop
        if g:
            out["group"] = g
    m = re.search(r"(?<![\w-])(\d+(?:\.\d+)?)\s*(kilograms?|kgs?|kilos?|quintals?|qtls?|tonnes?|tons?|किलो|किग्रा|क्विंटल|टन)?(?!\w)", low)
    if m:
        val, unit = float(m.group(1)), m.group(2)
        if unit and 0 < val <= 10_000_000 / UNIT_KG[unit]:  # 10,000 t cap: larger is a mishearing
            out["qty"] = qty(val, unit)
        elif not unit and val > 0 and awaiting == "qty":
            out["bare_qty"] = val  # a number without a unit: the caller reuses the farmer's last unit or asks
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
        if re.search(r"\bnot ready\b|\bnot yet\b|(taiyar|tayyar|tayar|तैयार|तयार)\s*(nahi|nahin|नहीं|नाही)", low):
            out["ready"] = False
        elif re.search(r"\bready\b|\btaiyar\b|\btayyar\b|\btayar\b|तयार|तैयार", low):
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


def qty(val: float, unit: str) -> dict:
    return {"original_qty": val, "original_unit": unit, "qty_kg": val * UNIT_KG[unit]}


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
    if s["state"] == "confirmed":  # already confirmed (e.g. a client retry): no new market run; start a new lot for that
        return _reply(s, START[L])
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
            s["state"], s["awaiting"] = "confirmed", None
            return _reply(s, START[L], done=True)
        else:
            s["state"] = "collecting"
            s["awaiting"] = None
            return _reply(s, FIX[L])
    else:
        found = extract(text, s["awaiting"], db=db)
        if llm.enabled() and not found:  # slow path only when the rules found nothing
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
