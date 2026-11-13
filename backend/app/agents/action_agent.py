"""KRISHI-X voice action agent (ported from Rocket's agent.py). A free-form request -> ONE tool -> executed by deterministic Python:
open views, compare, forecast, explain the verdict, change cost assumptions, start/switch lots, create and track orders.
Speed: fast rules first; the local LLM (llm.pick_tool) is asked only when the rules do not understand, and only argument-free tools
are accepted from it (arguments are always rule-parsed and validated). Anything with consequences asks yes/no first.
Every reply is in the farmer's language (en/hi/mr). shortcut: per-process STATE cache (plans); farmer memory and intake are in the DB."""
import re
from datetime import date

from app.agents import orchestrator
from app.conversation import intake, profile_agent as P
from app.repositories import farmers, market_data as MD
from app.services import gazetteer, llm, orders
from app.services.geo import haversine_km

STATE: dict = {}
R = {
    "en": dict(
        need_plan="Tell me your crops, amount and village first, then I can do that.", confirm="Shall I {what}? Say yes or no.",
        cancelled="Okay, I did not do it.", reset="Starting over.", lang="Switched to English.",
        unknown="I did not understand. Try: \"where should I sell\", \"show the forecast\", \"should I hold\", \"book transport\" or \"create the order\".",
        best="Best option: {label}. You keep about ₹{net}.", tab="Showing {x}.",
        help="I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, "
             "change a cost (\"set commission to 3\"), add a crop, and create and track an order. Say \"start over\" for a new farmer.",
        fc_none="No reliable forecast yet for {dest}: only {n} day(s) of stored prices, about 120 are needed. I will not guess.",
        fc_ok="Forecast for {dest}: {txt}. Not a guarantee.", fc_h="in {d} days about ₹{p} (₹{lo} to ₹{hi})",
        store="Nearest cold storage (demo, availability not confirmed): {name}, about ₹{cost} for 7 days. ", no_store="No suitable storage nearby. ",
        truck="Transport to {dest}: about ₹{cost} by {veh} (estimate).", conf="Confidence is {label}. {why}", no_conf="No confidence available.",
        spoil="Spoilage risk on the best trip: {level} ({p}, about {h} hours).", no_spoil="No spoilage estimate for this crop.",
        price="{mandi}: modal ₹{m} per quintal (₹{lo} to ₹{hi}), {age}", today="today", days_old="{n} days old",
        no_order="There is no order yet. Say \"create the order\" to make one.", order="Order {id} is {status}.",
        made="Done. Order {id} created for {label}, expected net ₹{net}. This is an expectation, not a final sale.",
        transport_sent="Transport request sent. It is an estimate, not a confirmed quote.",
        storage_sent="Storage enquiry sent. Availability is not confirmed until the operator confirms.", event_done="Done. Order is now {status}.",
        could_not="I could not do that now: {e}.", cant_change="I cannot change that setting.",
        updated="Updated and recalculated. {msg}", payer_note=" The buyer pays commission by default, so your net does not change. Say \"seller pays\" to include it.",
        where="Which village or town is the produce in?", not_yet="You have not told me about {crop} yet. Say, for example, \"I have 50 quintal {crop}\".",
        crops="Your crops: {list}. Say a crop name to switch.", none_yet="none yet", no_use="No usable prices for that crop nearby.",
        new_lot="New lot: {lot} near {loc}. {msg}", add_which="Which crop do you want to add, and how much? For example \"20 quintal potato\".",
        need_unit="{n} what: kg, quintal or tonne?", removed="Removed {crop}. {msg}", last_lot="{crop} is your only crop. Say \"start over\" to begin again.",
        qty_set="Changed to {lot}. {msg}", loc_set="Farm place changed to {loc}. {msg}", price_none="I have no {crop} price for that place in today's data.",
        other_crop="{crop} prices: ",
        w_create="create the sale order for the best option", w_request_transport="request transport", w_request_storage="send the storage enquiry",
        w_pickup="mark it picked up", w_deliver="mark it delivered", w_confirm_sale="confirm the final sale", w_cancel="cancel the order",
        t_compare="the mandi comparison", t_forecast="the forecast", t_logistics="storage and transport", t_order="the order"),
    "hi": dict(
        need_plan="पहले अपनी फसल, मात्रा और गाँव बताइए, फिर मैं यह कर दूँगा।", confirm="क्या मैं {what}? हाँ या नहीं बोलिए।",
        cancelled="ठीक है, मैंने नहीं किया।", reset="नए सिरे से शुरू करते हैं।", lang="हिंदी में बदल दिया।",
        unknown="मैं समझा नहीं। कहिए: \"कहाँ बेचूँ\", \"भाव अनुमान दिखाओ\", \"रोकूँ या बेचूँ\", \"ट्रक बुक करो\" या \"ऑर्डर बनाओ\"।",
        best="सबसे अच्छा विकल्प: {label}। आपके हाथ में लगभग ₹{net}।", tab="{x} दिखा रहा हूँ।",
        help="मैं बता सकता हूँ कहाँ बेचें, मंडियों की तुलना, अभी बेचें या रोकें, भाव अनुमान, भंडारण और ढुलाई, किसी मंडी का भाव, खर्च बदलना "
             "(\"कमीशन 3 करो\"), नई फसल जोड़ना, और ऑर्डर बनाना व देखना। नए किसान के लिए \"नए सिरे से\" बोलिए।",
        fc_none="{dest} के लिए अभी भरोसेमंद अनुमान नहीं: सिर्फ़ {n} दिन के भाव हैं, लगभग 120 चाहिए। मैं अंदाज़ा नहीं लगाऊँगा।",
        fc_ok="{dest} का अनुमान: {txt}। पक्का नहीं।", fc_h="{d} दिन में लगभग ₹{p} (₹{lo} से ₹{hi})",
        store="सबसे पास का कोल्ड स्टोरेज (डेमो, उपलब्धता पक्की नहीं): {name}, 7 दिन का लगभग ₹{cost}। ", no_store="पास में उपयुक्त भंडारण नहीं। ",
        truck="{dest} तक ढुलाई: {veh} से लगभग ₹{cost} (अनुमान)।", conf="भरोसा {label} है। {why}", no_conf="भरोसे का अनुमान उपलब्ध नहीं।",
        spoil="सबसे अच्छे रास्ते पर खराब होने का जोखिम: {level} ({p}, लगभग {h} घंटे)।", no_spoil="इस फसल के खराब होने का अनुमान नहीं।",
        price="{mandi}: मॉडल भाव ₹{m} प्रति क्विंटल (₹{lo} से ₹{hi}), {age}", today="आज का", days_old="{n} दिन पुराना",
        no_order="अभी कोई ऑर्डर नहीं है। बनाने के लिए \"ऑर्डर बनाओ\" बोलिए।", order="ऑर्डर {id} की स्थिति: {status}।",
        made="हो गया। {label} के लिए ऑर्डर {id} बना, अपेक्षित कमाई ₹{net}। यह अनुमान है, अंतिम बिक्री नहीं।",
        transport_sent="ढुलाई का अनुरोध भेज दिया। यह अनुमान है, पक्का कोटेशन नहीं।",
        storage_sent="भंडारण की पूछताछ भेज दी। संचालक की पुष्टि तक उपलब्धता पक्की नहीं।", event_done="हो गया। ऑर्डर की स्थिति अब: {status}।",
        could_not="अभी यह नहीं हो सका: {e}।", cant_change="यह सेटिंग नहीं बदल सकता।",
        updated="बदल दिया और फिर से हिसाब किया। {msg}", payer_note=" कमीशन आम तौर पर खरीदार देता है, इसलिए आपकी कमाई नहीं बदली। जोड़ने के लिए \"कमीशन मैं दूँगा\" बोलिए।",
        where="माल किस गाँव या शहर में है?", not_yet="आपने अभी {crop} के बारे में नहीं बताया। जैसे बोलिए: \"मेरे पास 50 क्विंटल {crop} है\"।",
        crops="आपकी फसलें: {list}। बदलने के लिए फसल का नाम बोलिए।", none_yet="अभी कोई नहीं", no_use="पास में इस फसल का उपयोगी भाव नहीं।",
        new_lot="नया माल: {loc} के पास {lot}। {msg}", add_which="कौन सी फसल जोड़नी है और कितनी? जैसे \"20 क्विंटल आलू\"।",
        need_unit="{n} क्या: किलो, क्विंटल या टन?", removed="{crop} हटा दिया। {msg}", last_lot="{crop} आपकी अकेली फसल है। नए सिरे से शुरू करने के लिए \"नए सिरे से\" बोलिए।",
        qty_set="बदल दिया: {lot}। {msg}", loc_set="खेत की जगह बदलकर {loc} कर दी। {msg}", price_none="आज के डेटा में उस जगह का {crop} भाव नहीं है।",
        other_crop="{crop} के भाव: ",
        w_create="सबसे अच्छे विकल्प के लिए बिक्री ऑर्डर बना दूँ", w_request_transport="ढुलाई का अनुरोध भेज दूँ", w_request_storage="भंडारण की पूछताछ भेज दूँ",
        w_pickup="माल उठ गया दर्ज कर दूँ", w_deliver="माल पहुँच गया दर्ज कर दूँ", w_confirm_sale="अंतिम बिक्री पक्की कर दूँ", w_cancel="ऑर्डर रद्द कर दूँ",
        t_compare="मंडियों की तुलना", t_forecast="भाव अनुमान", t_logistics="भंडारण और ढुलाई", t_order="ऑर्डर"),
    "mr": dict(
        need_plan="आधी तुमची पिके, प्रमाण आणि गाव सांगा, मग मी ते करतो.", confirm="मी {what} का? होय किंवा नाही म्हणा.",
        cancelled="ठीक आहे, मी केले नाही.", reset="पुन्हा सुरू करतो.", lang="मराठीत बदलले.",
        unknown="मला समजले नाही. म्हणा: \"कुठे विकू\", \"भाव अंदाज दाखवा\", \"थांबू का विकू\", \"ट्रक बुक करा\" किंवा \"ऑर्डर तयार करा\".",
        best="सर्वोत्तम पर्याय: {label}. तुमच्या हातात सुमारे ₹{net}.", tab="{x} दाखवतो.",
        help="मी सांगू शकतो कुठे विकायचे, मंडईंची तुलना, आता विकायचे की थांबायचे, भाव अंदाज, साठवण व वाहतूक, एखाद्या मंडईचा भाव, खर्च बदलणे "
             "(\"कमिशन 3 करा\"), नवीन पीक जोडणे, आणि ऑर्डर तयार करणे व पाहणे. नवीन शेतकऱ्यासाठी \"पुन्हा सुरू\" म्हणा.",
        fc_none="{dest} साठी अजून विश्वासार्ह अंदाज नाही: फक्त {n} दिवसांचे भाव आहेत, सुमारे 120 लागतात. मी अंदाजाने सांगणार नाही.",
        fc_ok="{dest} चा अंदाज: {txt}. खात्री नाही.", fc_h="{d} दिवसांत सुमारे ₹{p} (₹{lo} ते ₹{hi})",
        store="जवळचे शीतगृह (डेमो, उपलब्धता निश्चित नाही): {name}, 7 दिवसांसाठी सुमारे ₹{cost}. ", no_store="जवळ योग्य साठवण नाही. ",
        truck="{dest} पर्यंत वाहतूक: {veh} ने सुमारे ₹{cost} (अंदाज).", conf="खात्री {label} आहे. {why}", no_conf="खात्रीचा अंदाज उपलब्ध नाही.",
        spoil="सर्वोत्तम प्रवासात माल खराब होण्याचा धोका: {level} ({p}, सुमारे {h} तास).", no_spoil="या पिकाचा खराब होण्याचा अंदाज नाही.",
        price="{mandi}: मॉडल भाव ₹{m} प्रति क्विंटल (₹{lo} ते ₹{hi}), {age}", today="आजचा", days_old="{n} दिवस जुना",
        no_order="अजून ऑर्डर नाही. तयार करण्यासाठी \"ऑर्डर तयार करा\" म्हणा.", order="ऑर्डर {id} ची स्थिती: {status}.",
        made="झाले. {label} साठी ऑर्डर {id} तयार, अपेक्षित कमाई ₹{net}. हा अंदाज आहे, अंतिम विक्री नाही.",
        transport_sent="वाहतुकीची विनंती पाठवली. हा अंदाज आहे, खात्रीचे दरपत्रक नाही.",
        storage_sent="साठवणुकीची चौकशी पाठवली. चालकाच्या खात्रीपर्यंत उपलब्धता निश्चित नाही.", event_done="झाले. ऑर्डरची स्थिती आता: {status}.",
        could_not="आत्ता हे करता आले नाही: {e}.", cant_change="ही सेटिंग बदलता येत नाही.",
        updated="बदलले आणि पुन्हा हिशोब केला. {msg}", payer_note=" कमिशन सहसा खरेदीदार देतो, त्यामुळे तुमची कमाई बदलली नाही. जोडण्यासाठी \"कमिशन मी देतो\" म्हणा.",
        where="माल कोणत्या गावात किंवा शहरात आहे?", not_yet="तुम्ही अजून {crop} बद्दल सांगितले नाही. उदा. म्हणा: \"माझ्याकडे 50 क्विंटल {crop} आहे\".",
        crops="तुमची पिके: {list}. बदलण्यासाठी पिकाचे नाव सांगा.", none_yet="अजून काही नाही", no_use="जवळ या पिकाचा वापरण्याजोगा भाव नाही.",
        new_lot="नवीन माल: {loc} जवळ {lot}. {msg}", add_which="कोणते पीक जोडायचे आणि किती? उदा. \"20 क्विंटल बटाटा\".",
        need_unit="{n} काय: किलो, क्विंटल की टन?", removed="{crop} काढले. {msg}", last_lot="{crop} हे तुमचे एकमेव पीक आहे. पुन्हा सुरू करण्यासाठी \"पुन्हा सुरू\" म्हणा.",
        qty_set="बदलले: {lot}. {msg}", loc_set="शेताचे ठिकाण {loc} केले. {msg}", price_none="आजच्या माहितीत त्या ठिकाणचा {crop} भाव नाही.",
        other_crop="{crop} भाव: ",
        w_create="सर्वोत्तम पर्यायासाठी विक्री ऑर्डर तयार करू", w_request_transport="वाहतुकीची विनंती पाठवू", w_request_storage="साठवणुकीची चौकशी पाठवू",
        w_pickup="माल उचलला अशी नोंद करू", w_deliver="माल पोहोचला अशी नोंद करू", w_confirm_sale="अंतिम विक्री निश्चित करू", w_cancel="ऑर्डर रद्द करू",
        t_compare="मंडईंची तुलना", t_forecast="भाव अंदाज", t_logistics="साठवण आणि वाहतूक", t_order="ऑर्डर"),
}
STATUS = {"hi": {"created": "बना", "transport_requested": "ढुलाई माँगी", "storage_enquiry_sent": "भंडारण पूछताछ भेजी", "transport_accepted": "ढुलाई स्वीकार",
                 "in_transit": "रास्ते में", "delivered": "पहुँच गया", "sale_confirmed": "बिक्री पक्की", "cancelled": "रद्द", "storage_confirmed": "भंडारण पक्का"},
          "mr": {"created": "तयार", "transport_requested": "वाहतूक मागितली", "storage_enquiry_sent": "साठवण चौकशी पाठवली", "transport_accepted": "वाहतूक स्वीकारली",
                 "in_transit": "वाटेत", "delivered": "पोहोचला", "sale_confirmed": "विक्री निश्चित", "cancelled": "रद्द", "storage_confirmed": "साठवण निश्चित"}}
CONF = {"hi": {"low": "कम", "medium": "मध्यम", "high": "ज़्यादा"}, "mr": {"low": "कमी", "medium": "मध्यम", "high": "जास्त"}}
ACTION = {"hi": {"SELL NOW": "अभी बेचें", "HOLD": "रोकें", "INSUFFICIENT INFORMATION": "जानकारी कम है"},
          "mr": {"SELL NOW": "आता विका", "HOLD": "थांबा", "INSUFFICIENT INFORMATION": "माहिती अपुरी"}}
TOOLS = ["show_tab", "compare", "forecast", "explain_decision", "price_of", "logistics", "confidence", "spoilage", "set_assumption", "set_lot", "add_crop",
         "remove_lot", "set_qty", "set_location",
         "create_order", "order_event", "track_order", "read_aloud", "set_language", "start_over", "help", "list_crops"]
CONFIRM_TOOLS = {"create_order", "order_event"}
ARGLESS = {"add_crop", "compare", "forecast", "explain_decision", "logistics", "confidence", "spoilage", "track_order", "read_aloud", "create_order", "start_over", "help", "list_crops"}
ALLOWED_ASSUMPTIONS = {"commission_pct", "hamali_per_qtl", "road_factor", "risk_allowance_pct", "commission_payer", "financing_annual_pct", "ambient_temp_c"}
FARMER_EVENTS = {"request_transport", "request_storage", "pickup", "deliver", "confirm_sale", "cancel"}  # never the transporter's/operator's events


def rt(lang, key, **kw):
    return (R.get(lang) or R["en"]).get(key, R["en"][key]).format(**kw)


def _inr(n) -> str:
    s = str(int(round(abs(n))))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        s = ",".join(([head] if head else []) + parts + [tail])
    return ("-" if n < 0 else "") + s


def _status(s, lang):
    return STATUS.get(lang, {}).get(s, s.replace("_", " "))


# ---------------------------------------------------------------- intent router (rules: fast, offline)
def route(text: str) -> tuple[str, dict]:
    low = text.translate(P.DEV).lower().replace(",", "")
    has = lambda *w: any(x in low for x in w)  # noqa: E731
    if has("start over", "reset", "new farmer", "नए सिरे", "पुन्हा सुरू", "फिर से शुरू"):
        return "start_over", {}
    for words, code in (("hindi हिंदी हिन्दी", "hi"), ("marathi मराठी", "mr"), ("english अंग्रेजी अंग्रेज़ी इंग्रजी", "en")):
        if has(*words.split()) and (has("speak", "switch", "change", "language", "in ", "please", "बोल", "भाषा", "बदल", "मध्ये", "में") or len(low.split()) <= 2):
            return "set_language", {"lang": code}
    if has("what can you do", "help", "मदद", "काय करू शकता", "क्या कर सकते"):
        return "help", {}
    if has("my crops", "what crops", "which crops", "list crops", "मेरी फसल", "माझी पिके", "कौन सी फसल", "कोणती पिके"):
        return "list_crops", {}
    found = P.extract(text)
    if "crop" in found and (re.search(r"\b(remove|delete|drop)\b", low) or has("हटाओ", "हटा दो", "निकालो", "काढा", "काढून")):
        return "remove_lot", {"crop": found["crop"]}
    if "crop" in found and "qty" in found:  # "20 quintal potato", "I also have 20 quintal potato", "मेरे पास 20 क्विंटल आलू भी है"
        return "set_lot", found
    if has("add more", "add crop", "add another", "another crop", "more crop", "one more", "new crop", "और फसल", "दूसरी फसल", "नई फसल", "फसल जोड़",
           "आणखी पीक", "दुसरे पीक", "नवीन पीक", "पीक जोड") and "crop" not in found:
        return "add_crop", {}
    if has("my farm", "farm is", "village is", "my village", "i am in", "i live", "i'm in", "मेरा खेत", "खेत ", "मेरा गाँव", "मेरा गांव", "माझे शेत", "शेत ",
           "माझे गाव"):
        return "set_location", {"text": text}
    for rx, k in ((r"(?:commission|कमीशन|कमिशन)\D{0,14}(\d+(?:\.\d+)?)", "commission_pct"), (r"(?:hamali|हमाली)\D{0,14}(\d+(?:\.\d+)?)", "hamali_per_qtl"),
                  (r"road factor\D{0,8}(\d+(?:\.\d+)?)", "road_factor"), (r"risk(?: allowance)?\D{0,10}(\d+(?:\.\d+)?)", "risk_allowance_pct")):
        m = re.search(rx, low)
        if m:
            return "set_assumption", {k: float(m.group(1))}
    if has("seller pays", "i pay the commission", "कमीशन मैं दूँगा", "कमिशन मी देतो"):
        return "set_assumption", {"commission_payer": "seller"}
    if has("buyer pays"):
        return "set_assumption", {"commission_payer": "buyer"}
    m = re.search(r"(?:sold|sale|price|at|@|₹|rs\.?)\s*(\d{3,6})", low)
    if has("confirm the sale", "confirm sale", "i sold", "sale done", "बेच दिया", "विकले") and m:
        return "order_event", {"event": "confirm_sale", "actual_price": float(m.group(1))}
    for phrase, ev in (("book transport", "request_transport"), ("request transport", "request_transport"), ("book a truck", "request_transport"),
                       ("book truck", "request_transport"), ("ट्रक बुक", "request_transport"), ("गाड़ी बुक", "request_transport"),
                       ("book storage", "request_storage"), ("storage enquiry", "request_storage"), ("book cold storage", "request_storage"),
                       ("भंडारण बुक", "request_storage"), ("साठवण बुक", "request_storage"), ("mark delivered", "deliver"), ("it is delivered", "deliver"),
                       ("पहुँच गया", "deliver"), ("पोहोचला", "deliver"), ("picked up", "pickup"), ("cancel the order", "cancel"), ("cancel order", "cancel"),
                       ("ऑर्डर रद्द", "cancel")):
        if phrase in low:
            return "order_event", {"event": ev}
    if "qty" in found and "crop" not in found and not has("hamali", "हमाली", "commission", "कमीशन", "transport", "truck", "ढुलाई"):
        return "set_qty", {"qty": found["qty"]}  # "actually it is 80 quintal" changes the crop on screen
    if has("create the order", "create order", "place the order", "place order", "sale order", "book it", "ऑर्डर बना", "ऑर्डर तयार", "ऑर्डर कर"):
        return "create_order", {}
    if has("track", "my order", "order status", "where is the order", "order kahan", "order kaha", "order kuthe", "ऑर्डर स्टेटस", "ऑर्डर कहाँ", "ऑर्डर कहां",
           "ऑर्डर कुठे", "ऑर्डर की स्थिति", "ऑर्डरची स्थिती"):
        return "track_order", {}
    if has("forecast", "predict", "next week", "will the price", "price go", "भाव अनुमान", "अनुमान", "अंदाज", "आगे भाव", "भविष्य"):
        return "forecast", {}
    if has("sell now", "hold", "wait", "should i sell", "should i keep", "बेचूँ", "बेचूं", "रोकूँ", "रोकूं", "थांबू", "विकू का", "रोक") \
            and not has("where", "which mandi", "कहाँ", "कहां", "कुठे"):
        return "explain_decision", {}
    if has("how sure", "confident", "reliable", "trust", "भरोसा", "किती खात्री"):
        return "confidence", {}
    if has("spoil", "rot", "fresh", "खराब", "सड़"):
        return "spoilage", {}
    if has("storage", "warehouse", "cold store", "transport", "truck", "भंडारण", "गोदाम", "साठवण", "ट्रक", "ढुलाई", "वाहतूक"):
        return "logistics", {}
    if has("read", "say again", "repeat", "tell me", "सुनाओ", "सुनाइए", "ऐका", "पुन्हा सांगा"):
        return "read_aloud", {}
    if has("net", "how much will i", "how much money", "how much do i", "earn", "kitna milega", "कितना पैसा", "कितनी कमाई", "कितना मिलेगा", "किती पैसे",
           "किती मिळेल", "कमाई"):
        return "compare", {}
    if has("price", "rate", "bhav", "भाव", "दाम", "किंमत"):
        return "price_of", {"text": low}
    if has("best", "which mandi", "where should", "where to sell", "compare", "rank", "सबसे अच्छ", "कहाँ बेच", "कहां बेच", "कुठे विक", "तुलना", "show me"):
        return "compare", {}
    for k in ("order", "compare", "forecast"):
        if has(f"open {k}", f"go to {k}", f"show {k}"):
            return "show_tab", {"tab": k}
    return "unknown", {}


def _tab(t):
    return {"type": "tab", "value": t}


def _best_msg(plan, lang):
    rec = plan.get("recommendation") or {}
    b = rec.get("best")
    return rt(lang, "best", label=b["label"], net=_inr(b["net"])) if b else (rec.get("reason") or rt(lang, "no_use"))


# ---------------------------------------------------------------- tools (deterministic)
def run_tool(tool: str, args: dict, st: dict, lang: str, db) -> dict:
    plan = st.get("plan")
    if tool not in ("help", "start_over", "set_language", "set_lot") and not plan:
        return {"reply": rt(lang, "need_plan"), "actions": []}
    if tool == "help":
        return {"reply": rt(lang, "help"), "actions": []}
    if tool == "start_over":
        STATE.pop(st["sid"], None)
        farmers.clear(db, st["sid"])
        intake.forget(st["sid"], db)
        return {"reply": rt(lang, "reset"), "actions": [{"type": "reset"}]}
    if tool == "set_language":
        L2 = args["lang"]
        if plan and st.get("farmer"):  # re-run so every sentence of the plan is in the new language too
            st["farmer"]["lang"] = L2
            _activate(st, st["active"], L2)
            return {"reply": rt(L2, "lang"), "actions": [{"type": "lang", "value": L2}, {"type": "plan", "plan": st["plan"]}], "lang": L2}
        return {"reply": rt(L2, "lang"), "actions": [{"type": "lang", "value": L2}], "lang": L2}
    if tool == "show_tab":
        return {"reply": rt(lang, "tab", x=rt(lang, "t_" + args["tab"])), "actions": [_tab(args["tab"])]}
    if tool == "set_lot":
        return _set_lot(args, st, lang, db)
    if tool == "add_crop":
        st["await"] = {"crop": None}
        return {"reply": rt(lang, "add_which"), "actions": []}
    if tool == "remove_lot":
        return _remove_lot(args["crop"], st, lang, db)
    if tool == "set_qty":
        return _set_lot({"crop": st["active"], "qty": args["qty"]}, st, lang, db, key="qty_set")
    if tool == "set_location":
        hit = P._geocode(db, args["text"])
        if not hit:
            return {"reply": P.PLACE_HELP[lang], "actions": []}
        st["farmer"]["location"] = hit
        farmers.save(db, st["sid"], st["farmer"])
        new = _activate(st, st["active"], lang)
        return {"reply": rt(lang, "loc_set", loc=hit["name"], msg=_best_msg(new, lang)), "actions": [{"type": "plan", "plan": new}]}

    rec = plan.get("recommendation") or {}
    best = rec.get("best")
    if tool == "list_crops":
        lots = (st.get("farmer") or {}).get("lots", {})
        return {"reply": rt(lang, "crops", list=intake.lots_text(lots, lang) if lots else rt(lang, "none_yet")), "actions": []}
    if tool == "compare":
        return {"reply": _best_msg(plan, lang), "actions": [_tab("compare")]}
    if tool == "explain_decision":
        dec = rec.get("decision") or (plan.get("sell_vs_hold") or {}).get("decision") or {}
        action = ACTION.get(lang, {}).get(dec.get("action"), dec.get("action", ""))
        return {"reply": f"{action}. {dec.get('reason', '')} {'; '.join(dec.get('factors', [])[:3])}".strip(), "actions": [_tab("compare")]}
    if tool == "forecast":
        dest = (plan.get("sell_vs_hold") or {}).get("destination") or (best or {}).get("destination")
        if not dest:
            return {"reply": _best_msg(plan, lang), "actions": []}
        ok = [h for h in (plan.get("forecasts") or {}).get(dest, {}).get("horizons", []) if h["status"] == "ok"]
        name = dest.split(", ")[0]
        if ok:
            txt = "; ".join(rt(lang, "fc_h", d=h["horizon_days"], p=_inr(h["predicted"]), lo=_inr(h["lo"]), hi=_inr(h["hi"])) for h in ok[:3])
            return {"reply": rt(lang, "fc_ok", dest=name, txt=txt), "actions": [_tab("forecast")]}
        return {"reply": rt(lang, "fc_none", dest=name, n=len(MD.series(plan["profile"]["crop"], dest))), "actions": [_tab("forecast")]}
    if tool == "logistics":
        stor, trs = plan.get("storage") or [], plan.get("transport") or []
        s = rt(lang, "store", name=stor[0]["name"], cost=_inr(stor[0]["est_cost_7d"])) if stor else rt(lang, "no_store")
        t = ""
        if trs and trs[0].get("options"):
            o = min(trs[0]["options"], key=lambda v: v["total"])
            t = rt(lang, "truck", dest=trs[0]["destination"].split(", ")[0], cost=_inr(o["total"]), veh=o["vehicle"])
        return {"reply": s + t, "actions": [_tab("logistics")]}
    if tool == "confidence":
        c = rec.get("confidence")
        if not c:
            return {"reply": rt(lang, "no_conf"), "actions": []}
        return {"reply": rt(lang, "conf", label=CONF.get(lang, {}).get(c["label"], c["label"]), why="; ".join(c["detractors"][:2] or c["contributors"][:2])), "actions": []}
    if tool == "spoilage":
        sp = (best or {}).get("spoilage")
        return {"reply": rt(lang, "spoil", level=sp["level"], p=f"{sp['probability']:.0%}", h=sp["transit_hours"]) if sp else rt(lang, "no_spoil"), "actions": []}
    if tool == "price_of":
        return _price_of(args.get("text", ""), plan, lang)
    if tool == "read_aloud":
        return {"reply": _best_msg(plan, lang), "actions": []}
    if tool == "track_order":
        o = orders.get(st["order_id"]) if st.get("order_id") else None
        if not o:
            return {"reply": rt(lang, "no_order"), "actions": []}
        return {"reply": rt(lang, "order", id=o["id"], status=_status(o["status"], lang)), "actions": [{"type": "order", "order": o}, _tab("order")]}
    if tool == "set_assumption":
        bad = [k for k, v in args.items() if k not in ALLOWED_ASSUMPTIONS or (k != "commission_payer" and not (isinstance(v, (int, float)) and 0 <= v <= 1000))]
        if bad or not args or ("road_factor" in args and not 1 <= args["road_factor"] <= 3):
            return {"reply": rt(lang, "cant_change"), "actions": []}
        st["override"] = {**st.get("override", {}), **args}
        new = _activate(st, st["active"], lang)
        note = rt(lang, "payer_note") if "commission_pct" in args and new["assumptions"]["commission_payer"] == "buyer" else ""
        return {"reply": rt(lang, "updated", msg=_best_msg(new, lang)) + note, "actions": [{"type": "plan", "plan": new}]}
    return {"reply": rt(lang, "unknown"), "actions": []}


STOP = {"price", "prices", "rate", "rates", "what", "mandi", "market", "today", "show", "tell", "much", "there", "bhav", "the", "for", "kya", "hai",
        "भाव", "क्या", "है", "में", "का", "की", "मंडी", "आज", "किती", "आहे", "मध्ये", "चा", "ची", "काय", "बताओ", "सांगा", "दाम", "किंमत"}


def _norm_dev(s: str) -> str:
    return re.sub(r"[ँंऺ़]", "", s)


def _price_of(low: str, plan: dict, lang: str) -> dict:
    """Price of the farmer's crop (or another named crop) at a named mandi / town, else the 3 nearest mandis. Latest official row only."""
    f = P.extract(low)
    crop = f.get("crop") or plan["profile"]["crop"]
    rows = MD.mandis_with_prices(crop)
    words = [w for w in re.findall(r"[a-z]{4,}|[ऀ-ॿ]{2,}", low) if w not in STOP and not P._crop(w, w)]
    # Devanagari words are compared both as script and as their romanized spellings ("लासलगाँव" -> lasalgaon)
    latin = {w: ([w] if w.isascii() else [v for x in {w, _norm_dev(w)} for v in gazetteer._latin_variants(x) if len(v) >= 4]) for w in words}
    words = [_norm_dev(w) for w in words]
    hits = []
    for m in rows:
        dv, nm, ds = _norm_dev(gazetteer.dev_name(m["key"])), m["name"].lower(), (m["district"] or "").lower()
        name_hit = any(w in dv.split(",")[0] or any(x in nm for x in lat) for w, lat in zip(words, latin.values()))
        dist_hit = any(w in dv or any(x in ds for x in lat) for w, lat in zip(words, latin.values()))
        if name_hit or dist_hit:
            hits.append((0 if name_hit else 1, m))
    if words and not hits:
        return {"reply": rt(lang, "price_none", crop=intake.crop_label(crop, lang)), "actions": []}
    loc = plan["profile"]["location"]
    near = lambda m: haversine_km((loc["lat"], loc["lon"]), (m["lat"], m["lon"]))  # noqa: E731
    pick = [m for _, m in sorted(hits, key=lambda h: (h[0], near(h[1])))] if hits else sorted(rows, key=near)
    out = []
    for m in pick[:3]:
        df = MD.series(crop, m["key"])
        if df.empty:
            continue
        r = df.iloc[-1]
        age = (date.today() - r["date"].date()).days
        out.append(rt(lang, "price", mandi=_mandi_name(m["key"], lang), m=_inr(r["modal"]), lo=_inr(r["min"]), hi=_inr(r["max"]),
                      age=rt(lang, "today") if age <= 0 else rt(lang, "days_old", n=age)))
    head = rt(lang, "other_crop", crop=intake.crop_label(crop, lang)) if crop != plan["profile"]["crop"] else ""
    return {"reply": head + "; ".join(out) if out else rt(lang, "no_use"), "actions": [_tab("compare")]}


def _mandi_name(key: str, lang: str) -> str:
    """Spoken mandi name: market and district, in Devanagari for hi/mr when known."""
    short = ", ".join(key.split(", ")[:2])
    return gazetteer.dev_name(short) if lang in ("hi", "mr") else short


def _remove_lot(crop, st, lang, db):
    lots = st["farmer"]["lots"]
    if crop not in lots:
        return {"reply": rt(lang, "not_yet", crop=intake.crop_label(crop, lang)), "actions": []}
    if len(lots) == 1:
        return {"reply": rt(lang, "last_lot", crop=intake.crop_label(crop, lang)), "actions": []}
    del lots[crop]
    st["orders"].pop(crop, None)
    farmers.save(db, st["sid"], st["farmer"])
    new = _activate(st, st["active"] if st["active"] in lots else next(iter(lots)), lang)
    return {"reply": rt(lang, "removed", crop=intake.crop_label(crop, lang), msg=_best_msg(new, lang)), "actions": [{"type": "plan", "plan": new}]}


def _set_lot(args, st, lang, db, key="new_lot"):
    crop, q = args["crop"], args["qty"]
    plan = st.get("plan")
    loc = args.get("location") or (plan["profile"]["location"] if plan else None)
    if not loc:
        return {"reply": rt(lang, "where"), "actions": []}
    prev = plan["profile"] if plan else {}
    farmer = st.get("farmer") or {"location": loc, "ready": prev.get("ready", True), "can_store": prev.get("can_store", False), "lang": lang, "lots": {}}
    farmer["lots"][crop] = dict(q)
    farmer["location"] = loc
    st["farmer"] = farmer
    farmers.save(db, st["sid"], farmer)
    new = _activate(st, crop, lang)
    return {"reply": rt(lang, key, lot=intake.lots_text({crop: q}, lang), loc=loc["name"], msg=_best_msg(new, lang)), "actions": [{"type": "plan", "plan": new}]}


def _confirm_text(tool, args, lang):
    return rt(lang, "w_create" if tool == "create_order" else "w_" + args.get("event", "cancel"))


def _execute_confirmed(tool, args, st, lang):
    plan = st["plan"]
    if tool == "create_order":
        best = (plan.get("recommendation") or {}).get("best")
        if not best:
            return {"reply": _best_msg(plan, lang), "actions": []}
        o = orders.create(best, plan["profile"])
        st["order_id"] = st["orders"][st["active"]] = o["id"]
        return {"reply": rt(lang, "made", id=o["id"], label=best["label"], net=_inr(best["net"])), "actions": [{"type": "order", "order": o}, _tab("order")]}
    if not st.get("order_id"):
        return {"reply": rt(lang, "no_order"), "actions": []}
    ev = args["event"]
    data = None
    if ev == "confirm_sale":
        data = {"actual_price": args["actual_price"], "actual_qty_kg": plan["profile"]["qty_kg"],
                "actual_costs": ((plan.get("recommendation") or {}).get("best") or {}).get("total_deductions", 0)}
    try:
        o = orders.event(st["order_id"], ev, data)
    except (ValueError, KeyError) as e:
        return {"reply": rt(lang, "could_not", e=e), "actions": []}
    key = {"request_transport": "transport_sent", "request_storage": "storage_sent"}.get(ev)
    return {"reply": rt(lang, key) if key else rt(lang, "event_done", status=_status(o["status"], lang)), "actions": [{"type": "order", "order": o}, _tab("order")]}


# ---------------------------------------------------------------- lots (memory)
def _profile_for(st, crop, lang):
    f, lot = st["farmer"], st["farmer"]["lots"][crop]
    return {"crop": crop, "qty_kg": lot["qty_kg"], "original_qty": lot["original_qty"], "original_unit": lot["original_unit"], "location": f["location"],
            "ready": f["ready"], "can_store": f["can_store"], "variety": None, "grade": None, "harvest_date": None, "sell_pref": None, "lang": lang}


def _activate(st, crop, lang):
    plan = orchestrator.run(_profile_for(st, crop, lang), st["override"] or None)
    st["plan"], st["active"] = plan, crop
    st["order_id"] = st["orders"].get(crop)
    return plan


# ---------------------------------------------------------------- entry point
def handle(sid: str, text: str, lang: str | None, db) -> dict:
    res = _handle(sid, text, lang, db)
    st, L = STATE.get(sid), res.get("lang", "en")
    if st and st.get("farmer") and st.get("plan"):
        res["crops"] = [{"crop": c, "label": intake.crop_label(c, L), "qty": q["original_qty"], "unit": intake.unit_label(q["original_unit"], L),
                         "active": c == st["active"]} for c, q in st["farmer"]["lots"].items()]
    else:
        s = intake.pending(sid, db)
        res["crops"] = [{"crop": c, "label": intake.crop_label(c, L), "qty": (s["lots"].get(c) or {}).get("original_qty"),
                         "unit": intake.unit_label((s["lots"].get(c) or {}).get("original_unit") or "", L), "active": False} for c in s["crops"]] if s else []
    return res


def _out(res, sid, L, state, trace, **extra):
    return {"actions": [], **res, "trace": trace, "lang": res.get("lang", L), "session_id": sid, "state": state, **extra}


def _handle(sid: str, text: str, lang: str | None, db) -> dict:
    st = STATE.setdefault(sid, {"sid": sid, "plan": None, "pending": None, "order_id": None, "override": {}, "farmer": None, "active": None, "orders": {},
                                "await": None})
    text = (text or "").strip()
    pend_lang = (intake.pending(sid, db) or {}).get("lang")
    L = lang or P.detect_lang(text, ((st["plan"] or {}).get("profile") or {}).get("lang") or pend_lang or (st["farmer"] or {}).get("lang") or "en")

    if st["pending"]:  # a yes/no for an action with consequences
        yn = P.yes_no(text)
        pend, st["pending"] = st["pending"], None
        if yn is True:
            return _out(_execute_confirmed(pend["tool"], pend["args"], st, L), sid, L, "plan", [{"tool": pend["tool"], "confirmed": True}])
        if yn is False:
            return _out({"reply": rt(L, "cancelled")}, sid, L, "plan", [])

    if not text and st["plan"] and st["farmer"]:  # page reload: resume, do not ask again
        if st["plan"]["profile"].get("lang") != L:
            _activate(st, st["active"], L)
        return _out({"reply": intake.welcome_back(st["farmer"], L), "actions": [{"type": "plan", "plan": st["plan"]}]}, sid, L, "plan", [{"tool": "resume"}], done=True)

    if not st["plan"]:
        tool, args = route(text) if text else ("unknown", {})
        if tool in ("start_over", "set_language", "help"):
            return _out(run_tool(tool, args, st, L, db), sid, L, "collecting", [{"tool": tool}])
        if not text and not intake.pending(sid, db):  # returning farmer: remembered crops, no questions
            farmer = farmers.load(db, sid)
            if farmer:
                L = lang or farmer.get("lang") or L
                st["farmer"] = farmer
                plan = _activate(st, next(iter(farmer["lots"])), L)
                return _out({"reply": intake.welcome_back(farmer, L), "actions": [{"type": "plan", "plan": plan}]}, sid, L, "plan", [{"tool": "remembered"}], done=True)
        r = intake.step(sid, text, lang, db=db)
        actions = []
        if r["done"]:
            st["farmer"] = r["farmer"]
            actions.append({"type": "plan", "plan": _activate(st, next(iter(r["farmer"]["lots"])), r["lang"])})
        return _out({"reply": r["reply"], "actions": actions, "lang": r["lang"]}, sid, r["lang"], "plan" if r["done"] else "collecting", [{"tool": "intake"}],
                    done=r["done"], awaiting=r.get("awaiting"))

    trace, pre = [], []
    f = P.extract(text, "qty" if st.get("await") else None)
    lots = (st["farmer"] or {}).get("lots", {})
    aw = st.get("await")
    if aw:  # finishing "add a crop": the crop and/or its amount
        crop = f.get("crop") or aw["crop"]
        if "bare_qty" in f and crop:
            unit = intake.last_unit(lots)
            if not unit:
                return _out({"reply": rt(L, "need_unit", n=f"{f['bare_qty']:g}")}, sid, L, "plan", [{"tool": "add_crop"}])
            f["qty"] = P.qty(f["bare_qty"], unit)
        if crop and "qty" in f:
            st["await"] = None
            return _out(_set_lot({"crop": crop, "qty": f["qty"]}, st, L, db), sid, L, "plan", [{"tool": "set_lot", "args": {"crop": crop}}])
        if f.get("crop") and f["crop"] not in lots:
            st["await"] = {"crop": f["crop"]}
            return _out({"reply": intake._t("qty", L, crop=intake.crop_label(f["crop"], L))}, sid, L, "plan", [{"tool": "add_crop"}])
        st["await"] = None  # something else: answer that instead
    first = route(text)[0]
    if "crop" in f and f["crop"] != st["active"] and f["crop"] in lots and "qty" not in f:  # "show my tomato" switches lots
        pre.append({"type": "plan", "plan": _activate(st, f["crop"], L)})
        trace.append({"tool": "switch_crop", "args": {"crop": f["crop"]}})
        if first in ("unknown", "price_of", "compare"):
            return _out({"reply": f"{intake.crop_label(f['crop'], L)}. {_best_msg(st['plan'], L)}", "actions": pre}, sid, L, "plan", trace)
    elif "crop" in f and "qty" not in f and f["crop"] not in lots and first in ("unknown", "add_crop"):  # "potato", "add tomato": ask how much
        st["await"] = {"crop": f["crop"]}
        return _out({"reply": intake._t("qty", L, crop=intake.crop_label(f["crop"], L))}, sid, L, "plan", [{"tool": "add_crop"}])

    tool, args = route(text)
    if tool == "unknown" and llm.enabled():  # slow path only when the fast rules do not understand
        picked = llm.pick_tool(text, TOOLS, {"crop": st["plan"]["profile"]["crop"]})
        if picked and picked.get("tool") in ARGLESS | {"price_of"}:  # price_of only needs the farmer's own words
            tool, args = picked["tool"], ({"text": text.lower()} if picked["tool"] == "price_of" else {})
            trace.append({"tool": "llm_pick", "args": {"tool": tool}})
    if tool == "order_event" and args.get("event") not in FARMER_EVENTS:
        tool, args = "unknown", {}
    trace.append({"tool": tool, "args": {k: v for k, v in args.items() if k != "text"}})
    if tool == "order_event" and not st.get("order_id"):  # nothing to book against: say so before asking yes/no
        return _out({"reply": rt(L, "no_order")}, sid, L, "plan", trace)
    if tool in CONFIRM_TOOLS:
        st["pending"] = {"tool": tool, "args": args}
        return _out({"reply": rt(L, "confirm", what=_confirm_text(tool, args, L)), "actions": pre}, sid, L, "confirming_action", trace,
                    chips=[{"en": "Yes", "hi": "हाँ", "mr": "होय"}[L], {"en": "No", "hi": "नहीं", "mr": "नाही"}[L]])
    out = run_tool(tool, args, st, L, db)
    return _out({**out, "actions": pre + out.get("actions", [])}, sid, L, "plan", trace)
