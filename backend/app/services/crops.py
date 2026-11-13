"""Every crop, not just onion/tomato/potato: Hindi/Marathi names, spoken aliases, perishability and price seasonality.
Keys are the Agmarknet / Mandi-API commodity names lowercased (as stored in commodities.key).
Parameters are category defaults (leafy, soft vegetables, gourds, roots/bulbs, fruit, grain, pulses, oilseeds, fibre, flowers, spices) with
calibrated overrides for onion/tomato/potato. They are planning estimates for hold decisions, not lab values."""
import re
import zlib

# category: shelf life hours (min,max), max hold days, weight loss %/week, cold storage after N days, seasonal amplitude, daily volatility
CATEGORY = {
    "leafy":   dict(shelf=(12, 48), max_hold_days=2, shrink_wk=20.0, cold_after_days=1, amp=0.30, vol=0.040),
    "soft":    dict(shelf=(48, 120), max_hold_days=5, shrink_wk=8.0, cold_after_days=2, amp=0.30, vol=0.035),
    "gourd":   dict(shelf=(72, 168), max_hold_days=7, shrink_wk=6.0, cold_after_days=3, amp=0.25, vol=0.030),
    "root":    dict(shelf=(168, 720), max_hold_days=30, shrink_wk=1.5, cold_after_days=999, amp=0.25, vol=0.015),
    "fruit":   dict(shelf=(72, 240), max_hold_days=10, shrink_wk=5.0, cold_after_days=3, amp=0.20, vol=0.020),
    "grain":   dict(shelf=(2000, 8000), max_hold_days=120, shrink_wk=0.2, cold_after_days=999, amp=0.08, vol=0.006),
    "pulse":   dict(shelf=(2000, 8000), max_hold_days=120, shrink_wk=0.2, cold_after_days=999, amp=0.10, vol=0.008),
    "oilseed": dict(shelf=(2000, 6000), max_hold_days=90, shrink_wk=0.3, cold_after_days=999, amp=0.10, vol=0.008),
    "fibre":   dict(shelf=(4000, 9000), max_hold_days=120, shrink_wk=0.1, cold_after_days=999, amp=0.08, vol=0.006),
    "flower":  dict(shelf=(12, 36), max_hold_days=1, shrink_wk=30.0, cold_after_days=1, amp=0.35, vol=0.050),
    "spice":   dict(shelf=(2000, 6000), max_hold_days=90, shrink_wk=0.3, cold_after_days=999, amp=0.12, vol=0.010),
}
OVERRIDE = {  # calibrated (Rocket)
    "onion": dict(shelf=(120, 240), max_hold_days=30, shrink_wk=1.5, cold_after_days=999, amp=0.30, vol=0.014, phase=300),
    "tomato": dict(shelf=(48, 96), max_hold_days=7, shrink_wk=9.0, cold_after_days=2, amp=0.35, vol=0.035, phase=120),
    "potato": dict(shelf=(168, 504), max_hold_days=30, shrink_wk=1.0, cold_after_days=999, amp=0.18, vol=0.009, phase=30),
}
# key: (category, hindi, marathi, extra spoken aliases separated by spaces; multi-word Devanagari aliases joined with _)
C = {
    "onion": ("root", "प्याज", "कांदा", "pyaz pyaj kanda प्याज़"), "tomato": ("soft", "टमाटर", "टोमॅटो", "tamatar tomatoes टोमाटो"),
    "potato": ("root", "आलू", "बटाटा", "aloo batata potatoes"), "brinjal": ("soft", "बैंगन", "वांगी", "baingan vangi eggplant वांगे"),
    "green chilli": ("soft", "हरी मिर्च", "हिरवी मिरची", "mirchi chilli chili हरी_मिर्ची मिरची"),
    "paddy(common)": ("grain", "धान", "भात", "dhan paddy"), "banana": ("fruit", "केला", "केळी", "kela keli bananas"),
    "bhindi(ladies finger)": ("soft", "भिंडी", "भेंडी", "bhindi bhendi okra ladyfinger"), "cauliflower": ("soft", "फूलगोभी", "फ्लॉवर", "gobi फूल_गोभी"),
    "cabbage": ("soft", "पत्तागोभी", "कोबी", "kobi पत्ता_गोभी बंद_गोभी"), "maize": ("grain", "मक्का", "मका", "makka corn"),
    "bitter gourd": ("gourd", "करेला", "कारले", "karela karle"), "bottle gourd": ("gourd", "लौकी", "दुधी भोपळा", "lauki dudhi ghiya दुधी"),
    "pumpkin": ("gourd", "कद्दू", "लाल भोपळा", "kaddu bhopla"), "wheat": ("grain", "गेहूं", "गहू", "gehu gehun gahu गेहूँ"),
    "raddish": ("root", "मूली", "मुळा", "mooli radish"), "carrot": ("root", "गाजर", "गाजर", "gajar carrots"),
    "cucumbar(kheera)": ("gourd", "खीरा", "काकडी", "kheera kakdi cucumber"), "soyabean": ("oilseed", "सोयाबीन", "सोयाबीन", "soybean soya"),
    "ginger(green)": ("root", "अदरक", "आलं", "adrak ginger"), "banana - green": ("fruit", "कच्चा केला", "कच्ची केळी", "raw_banana"),
    "ridgeguard(tori)": ("gourd", "तोरई", "दोडका", "tori turai dodka"), "coriander(leaves)": ("leafy", "धनिया", "कोथिंबीर", "dhaniya kothimbir coriander"),
    "snakeguard": ("gourd", "चिचिंडा", "पडवळ", "padwal"), "lemon": ("fruit", "नींबू", "लिंबू", "nimbu limbu"),
    "beetroot": ("root", "चुकंदर", "बीट", "chukandar beet"), "papaya": ("fruit", "पपीता", "पपई", "papita papai"),
    "amaranthus": ("leafy", "चौलाई", "राजगिरा", "chaulai rajgira"), "ashgourd": ("gourd", "पेठा", "कोहळा", "petha kohla"),
    "cluster beans": ("soft", "ग्वार फली", "गवार", "gawar guar gavar"), "drumstick": ("soft", "सहजन", "शेवगा", "shevga sahjan moringa"),
    "coconut": ("fruit", "नारियल", "नारळ", "nariyal naral"), "garlic": ("root", "लहसुन", "लसूण", "lahsun lasun"),
    "onion green": ("leafy", "हरा प्याज", "कांद्याची पात", "spring_onion"), "capsicum": ("soft", "शिमला मिर्च", "ढोबळी मिरची", "shimla dhobli"),
    "guava": ("fruit", "अमरूद", "पेरू", "amrood peru"), "mint(pudina)": ("leafy", "पुदीना", "पुदिना", "pudina mint"),
    "beans": ("soft", "बीन्स", "घेवडा", "ghevda"), "apple": ("fruit", "सेब", "सफरचंद", "seb apples"),
    "bengal gram(gram)(whole)": ("pulse", "चना", "हरभरा", "chana harbhara"), "groundnut": ("oilseed", "मूंगफली", "शेंगदाणा", "moongphali shengdana peanut"),
    "mango(raw-ripe)": ("fruit", "आम का फल", "आंबा", "aam amba mango mangoes"), "sweet potato": ("root", "शकरकंद", "रताळे", "shakarkand ratale"),
    "cotton": ("fibre", "कपास", "कापूस", "kapas kapus"), "colacasia": ("root", "अरबी", "अळू", "arbi colocasia"),
    "cowpea(veg)": ("soft", "लोबिया", "चवळी", "lobia chavli"), "black gram(urd beans)(whole)": ("pulse", "उड़द", "उडीद", "urad udid"),
    "tapioca": ("root", "कसावा", "टॅपिओका", "cassava"), "mousambi(sweet lime)": ("fruit", "मौसंबी", "मोसंबी", "mosambi"),
    "pomegranate": ("fruit", "अनार", "डाळिंब", "anar dalimb"), "bajra(pearl millet/cumbu)": ("grain", "बाजरा", "बाजरी", "bajra bajri"),
    "amla(nelli kai)": ("fruit", "आंवला", "आवळा", "amla awla"), "spinach": ("leafy", "पालक", "पालक", "palak"),
    "green gram(moong)(whole)": ("pulse", "मूंग", "मूग", "moong mung"), "orange": ("fruit", "संतरा", "संत्री", "santra santri oranges"),
    "mustard": ("oilseed", "सरसों", "मोहरी", "sarson mohri"), "chikoos(sapota)": ("fruit", "चीकू", "चिकू", "chiku sapota"),
    "red gram/arhar/tur(whole)": ("pulse", "अरहर", "तूर", "arhar tur toor"), "rice": ("grain", "चावल", "तांदूळ", "chawal tandul"),
    "jowar(sorghum)": ("grain", "ज्वार", "ज्वारी", "jowar jwari sorghum"), "pineapple": ("fruit", "अनानास", "अननस", "ananas"),
    "green peas": ("soft", "हरी मटर", "हिरवा वाटाणा", "matar vatana peas मटर वाटाणा"), "methi(leaves)": ("leafy", "मेथी", "मेथी", "methi fenugreek"),
    "grapes": ("fruit", "अंगूर", "द्राक्षे", "angoor draksha grape"), "water melon": ("fruit", "तरबूज", "कलिंगड", "tarbooj kalingad watermelon"),
    "turnip": ("root", "शलजम", "सलगम", "shalgam"), "mushroom": ("soft", "मशरूम", "अळंबी", "mushrooms"),
    "lentil(masur)(whole)": ("pulse", "मसूर", "मसूर", "masoor masur lentil"), "custard apple(sharifa)": ("fruit", "सीताफल", "सीताफळ", "sitaphal sharifa"),
    "pointed gourd(parval)": ("gourd", "परवल", "परवल", "parwal parval"), "tinda": ("gourd", "टिंडा", "टिंडा", "tinda"),
    "sweet corn": ("soft", "स्वीट कॉर्न", "स्वीट कॉर्न", "sweetcorn"), "french beans(frasbean)": ("soft", "फ्रेंच बीन्स", "फरसबी", "farasbi"),
    "ragi(finger millet)": ("grain", "रागी", "नाचणी", "ragi nachni"), "dry chillies": ("spice", "सूखी मिर्च", "सुकी मिरची", "lal_mirch"),
    "elephant yam(suran)/amorphophallus": ("root", "जिमीकंद", "सुरण", "suran jimikand yam"), "knool khol": ("soft", "गांठ गोभी", "नवलकोल", "kohlrabi"),
    "sponge gourd": ("gourd", "गिलकी", "घोसाळे", "gilki ghosale"), "lime": ("fruit", "कागज़ी नींबू", "कागदी लिंबू", "lime"),
    "kinnow": ("fruit", "किन्नू", "किन्नू", "kinnow"), "sesamum(sesame,gingelly,til)": ("oilseed", "तिल", "तीळ", "sesame"),
    "marigold(calcutta)": ("flower", "गेंदा", "झेंडू", "genda zendu marigold"), "rose(local)": ("flower", "गुलाब", "गुलाब", "gulab rose"),
}
NAMES = {k: {"en": re.sub(r"\s*\(.*?\)\s*", " ", k).strip(), "hi": v[1], "mr": v[2]} for k, v in C.items()}


def _guess_category(key: str) -> str:
    k = key.lower()
    for words, cat in ((("leaves", "leafy", "spinach", "mint"), "leafy"), (("gourd", "guard", "kheera", "tinda", "parval"), "gourd"),
                       (("gram", "dal", "lentil", "masur", "moong", "urd", "arhar", "tur", "rajma"), "pulse"),
                       (("paddy", "rice", "wheat", "maize", "jowar", "bajra", "ragi", "barley", "millet"), "grain"),
                       (("seed", "nut", "mustard", "soya", "sesam", "castor", "sunflower"), "oilseed"), (("cotton", "jute"), "fibre"),
                       (("rose", "marigold", "jasmine", "flower", "lilly", "tube rose"), "flower"),
                       (("chilli", "pepper", "turmeric", "cumin", "jeera", "cardamom", "clove"), "spice"),
                       (("apple", "mango", "banana", "grape", "orange", "melon", "papaya", "guava", "fruit", "lime", "lemon", "berry", "chikoo", "pomegranate"), "fruit"),
                       (("potato", "onion", "garlic", "ginger", "carrot", "radish", "raddish", "beet", "yam", "root", "tapioca", "turnip"), "root")):
        if any(w in k for w in words):
            return cat
    return "soft"


def params(crop: str) -> dict:
    """Perishability + seasonality for any crop key (category default, calibrated overrides)."""
    cat = C[crop][0] if crop in C else _guess_category(crop)
    p = {**CATEGORY[cat], "category": cat, "phase": zlib.crc32(crop.encode()) % 365}
    return {**p, **OVERRIDE.get(crop, {})}


def aliases(crop: str) -> list[str]:
    """Spoken/written names a farmer may use (English, Hinglish, Hindi, Marathi)."""
    if crop not in C:
        return []
    _, hi, mr, extra = C[crop]
    return list(dict.fromkeys([hi, mr, NAMES[crop]["en"]] + [a.replace("_", " ") for a in extra.split() if a]))


def name(crop: str, lang: str) -> str:
    n = NAMES.get(crop)
    if n:
        return n.get(lang, n["en"])
    return re.sub(r"\s*\(.*?\)\s*", " ", crop).strip()


# ---- smart crop resolution: local names, groups, typos (the LLM fallback lives in llm.map_crop)
EXTRA = {  # spoken name -> commodity key (used only when that key exists in the catalogue)
    "chawal": "rice", "chaawal": "rice", "chaval": "rice", "chawl": "rice", "चावल": "rice", "तांदूळ": "rice",
    "dhaan": "paddy(common)", "dhan": "paddy(common)", "bhaat": "paddy(common)", "धान": "paddy(common)", "भात": "paddy(common)",
    "basmati": "paddy(basmati)", "बासमती": "paddy(basmati)",
    "kaju": "cashewnuts", "cashew": "cashewnuts", "काजू": "cashewnuts", "akhrot": "walnut", "walnuts": "walnut", "अखरोट": "walnut", "अक्रोड": "walnut",
    "khajoor": "dates", "khajur": "dates", "date": "dates", "खजूर": "dates", "anjeer": "fig(anjura/anjeer)", "anjir": "fig(anjura/anjeer)",
    "fig": "fig(anjura/anjeer)", "अंजीर": "fig(anjura/anjeer)", "badam": "almond(badam)", "almond": "almond(badam)", "almonds": "almond(badam)",
    "बादाम": "almond(badam)", "बदाम": "almond(badam)", "kishmish": "raisins", "kishmis": "raisins", "raisin": "raisins", "munakka": "raisins",
    "किशमिश": "raisins", "मनुका": "raisins", "alu": "potato", "papita": "papaya", "पपीता": "papaya",
}
GROUPS = {  # a whole family named: ask which one (members that have prices are offered)
    "dry fruits": ["almond(badam)", "cashewnuts", "walnut", "raisins", "dates", "fig(anjura/anjeer)"],
    "dry fruit": "dry fruits", "dryfruits": "dry fruits", "mewa": "dry fruits", "meva": "dry fruits", "मेवा": "dry fruits", "सुका मेवा": "dry fruits",
    "सुकामेवा": "dry fruits", "ड्राय फ्रूट": "dry fruits",
    "pulses": ["bengal gram(gram)(whole)", "red gram/arhar/tur(whole)", "green gram(moong)(whole)", "black gram(urd beans)(whole)", "lentil(masur)(whole)"],
    "dal": "pulses", "daal": "pulses", "दाल": "pulses", "डाळ": "pulses",
    "millets": ["bajra(pearl millet/cumbu)", "jowar(sorghum)", "ragi(finger millet)"], "millet": "millets",
}
GENERIC_INNER = {"whole", "common", "fine", "superfine", "grade a", "f&v", "raw", "ripe", "raw-ripe", "green", "dry", "local", "other", "loose",
                 "split", "cumbu", "veg", "leaves", "anjura", "fine/superfine/grade a", "calcutta", "seam", "chickpeas-white"}
NOT_CROPS = {"price", "prices", "rate", "rates", "sell", "selling", "want", "have", "where", "what", "today", "mandi", "market", "quintal", "quintals",
             "tonne", "kilo", "please", "hello", "there", "should", "which", "about", "store", "storage", "order", "transport", "truck", "scheme",
             "schemes", "weather", "thanks", "thank", "forecast", "best", "near", "much", "money", "help", "tell", "show", "more", "also", "other",
             "some", "many", "crop", "crops", "farm", "farmer", "village", "ready", "hold", "wait", "bhai", "bhaiya", "kahan", "kitna", "mera",
             "mere", "paas", "abhi", "aaj", "chahiye", "bechna", "becho", "bech", "good", "fresh", "they", "them", "this", "that", "with", "from"}


def group_of(text: str) -> tuple[str, list[str]] | None:
    """'I have dry fruits' -> ('dry fruits', [member keys])."""
    low = text.lower()
    for g in sorted(GROUPS, key=len, reverse=True):
        if (g.isascii() and re.search(rf"\b{re.escape(g)}\b", low)) or (not g.isascii() and g in text):
            name = GROUPS[g] if isinstance(GROUPS[g], str) else g
            return name, GROUPS[name]
    return None


def fuzzy(text: str, aliases: dict[str, str]) -> str | None:
    """Typo-tolerant match of one spoken word to a known crop ('papya' -> papaya, 'tamatr' -> tomato). Common words are never crops."""
    import difflib
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in NOT_CROPS]
    keys = [a for a in aliases if a.isascii() and len(a) >= 4]
    for w in words:
        hit = difflib.get_close_matches(w, keys, n=1, cutoff=0.82)
        if hit:
            return aliases[hit[0]]
    return None
