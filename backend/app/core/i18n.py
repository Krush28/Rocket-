"""Hindi / Marathi for every farmer-facing sentence the agents produce.
Agents keep writing English templates; `localize(plan, lang)` translates the finished plan once, by exact template match,
so names, mandi keys and codes (SELL NOW, mandi_now ...) are never altered. Placeholders are translated recursively
(e.g. "about 30%"), crop keys via the profile agent's crop names.
First-draft translations: review farming vocabulary with a native speaker (Rocket docs/HANDOFF.md, next step 1)."""
import re

TEMPLATES: list[tuple[str, str, str]] = [  # (English template, Hindi, Marathi)
    ("Sell at {dest} today", "आज {dest} में बेचें", "आज {dest} येथे विका"),
    ("Sell at {dest} with shared truck", "साझा ट्रक से {dest} में बेचें", "सामायिक ट्रकने {dest} येथे विका"),
    ("Direct sale to {name}", "{name} को सीधी बिक्री", "{name} ला थेट विक्री"),
    ("Hold {days} days ({storage}), sell at {dest}", "{days} दिन रोकें ({storage}), फिर {dest} में बेचें", "{days} दिवस थांबा ({storage}), नंतर {dest} येथे विका"),
    ("in {days} days", "{days} दिन में", "{days} दिवसांत"),
    ("today / next market day", "आज / अगले बाज़ार दिन", "आज / पुढच्या बाजार दिवशी"),
    ("n/a (current price)", "लागू नहीं (आज का भाव)", "लागू नाही (आजचा भाव)"),
    ("Modal price is not a guaranteed price for your lot", "मॉडल भाव आपके माल का पक्का भाव नहीं है", "मॉडल भाव हा तुमच्या मालाचा खात्रीचा भाव नाही"),
    ("Transport is an ESTIMATE", "ढुलाई का खर्च अनुमान है", "वाहतूक खर्च अंदाजित आहे"),
    ("Forecast is not a guarantee", "पूर्वानुमान पक्का नहीं है", "अंदाज खात्रीशीर नाही"),
    ("Storage availability must be confirmed", "भंडारण की उपलब्धता की पुष्टि ज़रूरी है", "साठवणुकीची उपलब्धता निश्चित करावी लागेल"),
    ("Quality grading may change the price", "गुणवत्ता जाँच से भाव बदल सकता है", "प्रतवारीनुसार भाव बदलू शकतो"),
    ("{pct} chance price ends below today's", "{pct} संभावना कि भाव आज से नीचे जाएगा", "{pct} शक्यता की भाव आजपेक्षा खाली जाईल"),
    ("about {n}%", "लगभग {n}%", "सुमारे {n}%"),
    ("under 5%", "5% से कम", "5% पेक्षा कमी"),
    ("Pool members are SIMULATED; needs real coordination", "साझा ट्रक के साथी नकली (डेमो) हैं; असली तालमेल चाहिए", "सामायिक ट्रकचे साथीदार नकली (डेमो) आहेत; खरा समन्वय लागेल"),
    ("DEMO OFFER: not a real buyer", "डेमो ऑफ़र: असली खरीदार नहीं", "डेमो ऑफर: खरा खरेदीदार नाही"),
    ("Offer valid until {date}", "ऑफ़र {date} तक", "ऑफर {date} पर्यंत"),
    ("LIVE PRICE / ESTIMATED COSTS", "असली भाव / अनुमानित खर्च", "खरा भाव / अंदाजित खर्च"),
    ("DEMO DATA / ESTIMATE", "डेमो डेटा / अनुमान", "डेमो डेटा / अंदाज"),
    ("ESTIMATE", "अनुमान", "अंदाज"),
    ("ESTIMATE (straight-line x road factor)", "अनुमान (सीधी दूरी × सड़क गुणक)", "अंदाज (सरळ अंतर × रस्ता गुणक)"),
    ("ESTIMATE - no quote requested", "अनुमान - भाड़े का कोटेशन नहीं लिया", "अंदाज - भाड्याचे दरपत्रक घेतलेले नाही"),
    ("unverified (demo)", "असत्यापित (डेमो)", "पडताळणी नाही (डेमो)"),
    ("UNCONFIRMED - send an enquiry; operator must confirm", "पुष्टि नहीं - पूछताछ भेजें; संचालक की पुष्टि ज़रूरी", "निश्चित नाही - चौकशी पाठवा; चालकाची खात्री आवश्यक"),
    ("Demo Cold Store - {place}", "डेमो कोल्ड स्टोरेज - {place}", "डेमो शीतगृह - {place}"),
    ("Demo Ventilated Onion Store - {place}", "डेमो हवादार प्याज़ गोदाम - {place}", "डेमो हवेशीर कांदा चाळ - {place}"),
    ("tempo", "टेम्पो", "टेम्पो"),
    ("truck", "ट्रक", "ट्रक"),
    ("reefer truck", "ठंडा (रीफ़र) ट्रक", "शीत (रीफर) ट्रक"),
    ("insufficient data", "पर्याप्त डेटा नहीं", "पुरेसा डेटा नाही"),
    ("no reliable forecast for this horizon", "इस अवधि का भरोसेमंद पूर्वानुमान नहीं", "या कालावधीचा विश्वासार्ह अंदाज नाही"),
    ("no suitable storage", "उपयुक्त भंडारण नहीं", "योग्य साठवण नाही"),
    ("{crop} shelf life is about {n} days", "{crop} लगभग {n} दिन ही टिकता है", "{crop} सुमारे {n} दिवसच टिकतो"),
    ("no shelf-life data for {crop}; hold not evaluated", "{crop} कितने दिन टिकता है, इसका डेटा नहीं; रोकने का हिसाब नहीं किया",
     "{crop} किती दिवस टिकतो याचा डेटा नाही; थांबण्याचा हिशोब केला नाही"),
    ("no mandi with {crop} prices within 450 km of the farm", "खेत से 450 किमी के भीतर {crop} के भाव वाली कोई मंडी नहीं",
     "शेतापासून 450 किमीच्या आत {crop} चे भाव असलेली मंडई नाही"),
    ("No reliable forecast or feasible storage for any hold window, so holding is not supported.",
     "किसी भी अवधि के लिए भरोसेमंद पूर्वानुमान या उपयुक्त भंडारण नहीं है, इसलिए माल रोकना उचित नहीं।",
     "कोणत्याही कालावधीसाठी विश्वासार्ह अंदाज किंवा योग्य साठवण नाही, म्हणून माल थांबवणे योग्य नाही."),
    ("No hold option clears the extra costs, loss and risk.", "रोकने का कोई भी विकल्प अतिरिक्त खर्च, नुकसान और जोखिम से ज़्यादा फ़ायदा नहीं देता।",
     "थांबण्याचा कोणताही पर्याय जादा खर्च, नुकसान आणि जोखीम भरून काढत नाही."),
    ("No current price available for the chosen crop.", "चुनी गई फसल का आज का भाव उपलब्ध नहीं है।", "निवडलेल्या पिकाचा आजचा भाव उपलब्ध नाही."),
    ("Expected net after storage, transport, loss and financing is higher by about Rs {gain} with {pct} chance the price ends below today's. Not guaranteed.",
     "भंडारण, ढुलाई, नुकसान और ब्याज के बाद अपेक्षित कमाई लगभग ₹{gain} ज़्यादा है; {pct} संभावना कि भाव आज से नीचे जाए। पक्का नहीं।",
     "साठवण, वाहतूक, नुकसान आणि व्याजानंतर अपेक्षित कमाई सुमारे ₹{gain} जास्त आहे; {pct} शक्यता की भाव आजपेक्षा खाली जाईल. खात्री नाही."),
    ("All nearby prices are older than {n} days (latest {date}). Import today's prices before deciding.",
     "पास के सभी भाव {n} दिन से पुराने हैं (आख़िरी {date})। फ़ैसले से पहले आज के भाव लोड करें।",
     "जवळचे सर्व भाव {n} दिवसांपेक्षा जुने आहेत (शेवटचा {date}). निर्णयापूर्वी आजचे भाव भरा."),
    ("No feasible selling option with fresh prices was found.", "ताज़ा भाव वाला कोई बिक्री विकल्प नहीं मिला।", "ताज्या भावासह विक्रीचा कोणताही पर्याय सापडला नाही."),
    ("LIVE prices from data.gov.in (Agmarknet). Buyers, warehouses, transporters and the shared-load pool are still DEMO. Costs are ESTIMATES unless marked otherwise.",
     "भाव data.gov.in (एगमार्कनेट) से असली हैं। खरीदार, गोदाम, ढुलाई वाले और साझा ट्रक अभी डेमो हैं। जब तक अलग न लिखा हो, खर्च अनुमान हैं।",
     "भाव data.gov.in (ॲगमार्कनेट) वरून खरे आहेत. खरेदीदार, गोदामे, वाहतूकदार आणि सामायिक ट्रक अजून डेमो आहेत. वेगळे नमूद नसल्यास खर्च अंदाजित आहेत."),
    ("DEMO DATA: prices, arrivals, buyers, warehouses, transporters are synthetic. Costs are ESTIMATES unless marked otherwise.",
     "डेमो डेटा: भाव, आवक, खरीदार, गोदाम और ढुलाई वाले नकली हैं। जब तक अलग न लिखा हो, खर्च अनुमान हैं।",
     "डेमो डेटा: भाव, आवक, खरेदीदार, गोदामे आणि वाहतूकदार नकली आहेत. वेगळे नमूद नसल्यास खर्च अंदाजित आहेत."),
]

SKIP_KEYS = {"destination", "action", "type", "crop", "key"}  # codes and lookup keys, never translated
_RX = [(re.compile("^" + re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>.+?)", re.escape(en)) + "$"), hi, mr) for en, hi, mr in TEMPLATES]


def _crop(v: str, lang: str) -> str:
    from app.conversation.profile_agent import NAMES  # lazy: avoid an import cycle
    return NAMES.get(v, {}).get(lang, v)


def tr(s: str, lang: str | None) -> str:
    if lang not in ("hi", "mr") or not s:
        return s
    for rx, hi, mr in _RX:
        m = rx.match(s)
        if m:
            params = {k: (_crop(v, lang) if k == "crop" else tr(v, lang)) for k, v in m.groupdict().items()}
            return (hi if lang == "hi" else mr).format(**params)
    return s


def localize(obj, lang: str | None):
    """Translate every string value in a plan (in place for dicts/lists); English and unknown text pass through."""
    if lang not in ("hi", "mr"):
        return obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in SKIP_KEYS:
                obj[k] = localize(v, lang)
        return obj
    if isinstance(obj, list):
        return [localize(v, lang) for v in obj]
    return tr(obj, lang) if isinstance(obj, str) else obj
