"""Government schemes for farmers that relate to selling, storing, insuring and income (central + state), with official portals.
Curated, short and conservative: amounts and rules change, so every card links to the official site. Credit / loan products are
intentionally not listed (out of scope for this platform). Reviewed 2026-11."""

REVIEWED = "2026-11"
# (id, level, state, category, url, {lang: (name, benefit, who/how)})
S = [
    ("pm-kisan", "central", None, "income", "https://pmkisan.gov.in", {
        "en": ("PM-KISAN", "Income support of Rs 6,000 a year, paid in three instalments to the bank account.", "Landholding farmer families. Register on the portal or at a CSC with land records and bank details; complete e-KYC."),
        "hi": ("पीएम-किसान", "साल में ₹6,000 की आय सहायता, तीन किस्तों में बैंक खाते में।", "ज़मीन वाले किसान परिवार। पोर्टल या CSC पर भूमि रिकॉर्ड और बैंक विवरण से पंजीकरण; e-KYC पूरा करें।"),
        "mr": ("पीएम-किसान", "वर्षाला ₹6,000 उत्पन्न सहाय्य, तीन हप्त्यांत बँक खात्यात.", "जमीनधारक शेतकरी कुटुंबे. पोर्टल किंवा CSC वर जमीन नोंदी व बँक तपशीलासह नोंदणी; e-KYC पूर्ण करा.")}),
    ("pmfby", "central", None, "insurance", "https://pmfby.gov.in", {
        "en": ("Pradhan Mantri Fasal Bima Yojana", "Crop insurance against weather, pests and post-harvest losses at a low farmer premium (about 2% kharif, 1.5% rabi, 5% horticulture).", "All farmers growing notified crops. Enrol through your bank, CSC or the portal before the season's cut-off date."),
        "hi": ("प्रधानमंत्री फसल बीमा योजना", "मौसम, कीट और कटाई के बाद के नुकसान पर कम प्रीमियम में फसल बीमा (खरीफ लगभग 2%, रबी 1.5%, बागवानी 5%)।", "अधिसूचित फसल उगाने वाले सभी किसान। मौसम की अंतिम तिथि से पहले बैंक, CSC या पोर्टल से नामांकन।"),
        "mr": ("प्रधानमंत्री पीक विमा योजना", "हवामान, कीड व काढणीनंतरच्या नुकसानीसाठी कमी हप्त्यात पीक विमा (खरीप सुमारे 2%, रब्बी 1.5%, फळबाग 5%).", "अधिसूचित पिके घेणारे सर्व शेतकरी. हंगामाच्या अंतिम तारखेपूर्वी बँक, CSC किंवा पोर्टलवर नोंदणी.")}),
    ("enam", "central", None, "market", "https://enam.gov.in", {
        "en": ("e-NAM (National Agriculture Market)", "Sell through online bidding across connected mandis, with transparent price discovery and direct payment.", "Farmers and FPOs. Register on the portal or at an e-NAM mandi with ID and bank details."),
        "hi": ("ई-नाम (राष्ट्रीय कृषि बाज़ार)", "जुड़ी मंडियों में ऑनलाइन बोली से बिक्री, पारदर्शी भाव और सीधा भुगतान।", "किसान और FPO। पोर्टल या ई-नाम मंडी में पहचान और बैंक विवरण से पंजीकरण।"),
        "mr": ("ई-नाम (राष्ट्रीय कृषी बाजार)", "जोडलेल्या मंडईंत ऑनलाइन बोलीने विक्री, पारदर्शक भाव व थेट पेमेंट.", "शेतकरी व FPO. पोर्टल किंवा ई-नाम मंडईत ओळखपत्र व बँक तपशीलासह नोंदणी.")}),
    ("pm-aasha", "central", None, "market", "https://agriwelfare.gov.in", {
        "en": ("PM-AASHA (MSP procurement)", "Assured minimum support price for notified pulses, oilseeds and copra through government procurement when market prices fall.", "Farmers of notified crops. Register with the state procurement agency for the season."),
        "hi": ("पीएम-आशा (MSP खरीद)", "बाज़ार भाव गिरने पर अधिसूचित दालों, तिलहन और खोपरे की सरकारी खरीद से न्यूनतम समर्थन मूल्य।", "अधिसूचित फसलों के किसान। मौसम के लिए राज्य खरीद एजेंसी में पंजीकरण।"),
        "mr": ("पीएम-आशा (MSP खरेदी)", "बाजारभाव घसरल्यास अधिसूचित डाळी, तेलबिया व खोबऱ्याची शासकीय खरेदी हमीभावाने.", "अधिसूचित पिकांचे शेतकरी. हंगामासाठी राज्य खरेदी संस्थेकडे नोंदणी.")}),
    ("op-greens", "central", None, "storage", "https://www.mofpi.gov.in", {
        "en": ("Operation Greens", "Support for transport and storage of fruits and vegetables (including tomato, onion, potato) during gluts, and for value-chain projects.", "Farmers' groups, FPOs, processors and traders. Check the Ministry of Food Processing Industries portal for open windows."),
        "hi": ("ऑपरेशन ग्रीन्स", "भरमार के समय फल-सब्ज़ियों (टमाटर, प्याज, आलू सहित) की ढुलाई और भंडारण पर सहायता, और मूल्य-श्रृंखला परियोजनाएँ।", "किसान समूह, FPO, प्रसंस्करणकर्ता। खुली योजनाओं के लिए खाद्य प्रसंस्करण मंत्रालय का पोर्टल देखें।"),
        "mr": ("ऑपरेशन ग्रीन्स", "आवक जास्त असताना फळे-भाज्यांच्या (टोमॅटो, कांदा, बटाटा) वाहतूक व साठवणुकीसाठी सहाय्य, मूल्यसाखळी प्रकल्प.", "शेतकरी गट, FPO, प्रक्रियादार. खुल्या योजनांसाठी अन्न प्रक्रिया मंत्रालयाचे पोर्टल पाहा.")}),
    ("ami", "central", None, "storage", "https://agmarknet.gov.in", {
        "en": ("Agricultural Marketing Infrastructure (storage)", "Capital subsidy for building godowns, warehouses and other post-harvest marketing infrastructure.", "Farmers, FPOs, cooperatives and agri-entrepreneurs. Apply through NABARD / the state marketing department."),
        "hi": ("कृषि विपणन अवसंरचना (भंडारण)", "गोदाम, वेयरहाउस और कटाई-बाद विपणन ढाँचा बनाने पर पूंजी सब्सिडी।", "किसान, FPO, सहकारी समितियाँ। NABARD / राज्य विपणन विभाग से आवेदन।"),
        "mr": ("कृषी पणन पायाभूत सुविधा (साठवण)", "गोदाम, वखार व काढणीनंतरच्या पणन सुविधा उभारण्यासाठी भांडवली अनुदान.", "शेतकरी, FPO, सहकारी संस्था. NABARD / राज्य पणन विभागाकडे अर्ज.")}),
    ("pm-kmy", "central", None, "income", "https://maandhan.in", {
        "en": ("PM Kisan Maan-Dhan", "Pension of Rs 3,000 a month after age 60 for small and marginal farmers, with a small monthly contribution.", "Small and marginal farmers aged 18 to 40. Enrol at a CSC."),
        "hi": ("पीएम किसान मान-धन", "छोटे और सीमांत किसानों को 60 वर्ष के बाद ₹3,000 मासिक पेंशन, छोटे मासिक योगदान के साथ।", "18 से 40 वर्ष के छोटे और सीमांत किसान। CSC पर नामांकन।"),
        "mr": ("पीएम किसान मान-धन", "लहान व अल्पभूधारक शेतकऱ्यांना 60 वर्षांनंतर ₹3,000 मासिक पेन्शन, लहान मासिक योगदानासह.", "18 ते 40 वयोगटातील लहान व अल्पभूधारक शेतकरी. CSC वर नोंदणी.")}),
    ("shc", "central", None, "farming", "https://soilhealth.dac.gov.in", {
        "en": ("Soil Health Card", "Free soil test with crop-wise fertiliser advice for your field.", "All farmers. Ask the agriculture office or apply on the portal."),
        "hi": ("मृदा स्वास्थ्य कार्ड", "खेत की मुफ़्त मिट्टी जाँच और फसल अनुसार खाद सलाह।", "सभी किसान। कृषि कार्यालय या पोर्टल पर आवेदन।"),
        "mr": ("मृदा आरोग्य पत्रिका", "शेताची मोफत माती तपासणी व पिकनिहाय खत शिफारस.", "सर्व शेतकरी. कृषी कार्यालय किंवा पोर्टलवर अर्ज.")}),
    ("pm-kusum", "central", None, "farming", "https://pmkusum.mnre.gov.in", {
        "en": ("PM-KUSUM (solar pumps)", "Subsidy for solar irrigation pumps and solarising existing pumps.", "Individual farmers, groups and FPOs. Apply through the state nodal agency."),
        "hi": ("पीएम-कुसुम (सौर पंप)", "सौर सिंचाई पंप और मौजूदा पंपों को सौर बनाने पर सब्सिडी।", "किसान, समूह और FPO। राज्य नोडल एजेंसी से आवेदन।"),
        "mr": ("पीएम-कुसुम (सौर पंप)", "सौर सिंचन पंप व विद्यमान पंप सौर करण्यासाठी अनुदान.", "शेतकरी, गट व FPO. राज्य नोडल संस्थेमार्फत अर्ज.")}),
    ("mh-nsmny", "state", "Maharashtra", "income", "https://nsmny.mahait.org", {
        "en": ("Namo Shetkari Mahasanman Nidhi", "Additional state income support for PM-KISAN beneficiary farmers in Maharashtra.", "PM-KISAN beneficiaries in Maharashtra; paid automatically after e-KYC."),
        "hi": ("नमो शेतकरी महासन्मान निधि", "महाराष्ट्र में पीएम-किसान लाभार्थी किसानों को अतिरिक्त राज्य आय सहायता।", "महाराष्ट्र के पीएम-किसान लाभार्थी; e-KYC के बाद अपने आप भुगतान।"),
        "mr": ("नमो शेतकरी महासन्मान निधी", "महाराष्ट्रातील पीएम-किसान लाभार्थी शेतकऱ्यांना अतिरिक्त राज्य उत्पन्न सहाय्य.", "महाराष्ट्रातील पीएम-किसान लाभार्थी; e-KYC नंतर आपोआप जमा.")}),
    ("mh-mahadbt", "state", "Maharashtra", "farming", "https://mahadbt.maharashtra.gov.in", {
        "en": ("MahaDBT farmer schemes", "One portal to apply for state agriculture subsidies such as farm machinery, drip and sprinkler irrigation.", "Farmers in Maharashtra. Register once on MahaDBT and apply for open components."),
        "hi": ("महाडीबीटी किसान योजनाएँ", "कृषि यंत्र, ड्रिप-स्प्रिंकलर जैसी राज्य सब्सिडी के लिए एक पोर्टल।", "महाराष्ट्र के किसान। महाडीबीटी पर एक बार पंजीकरण करके आवेदन।"),
        "mr": ("महाडीबीटी शेतकरी योजना", "कृषी यंत्रे, ठिबक-तुषार सिंचन यांसारख्या राज्य अनुदानांसाठी एकच पोर्टल.", "महाराष्ट्रातील शेतकरी. महाडीबीटीवर एकदा नोंदणी करून अर्ज.")}),
    ("mh-shettale", "state", "Maharashtra", "farming", "https://mahadbt.maharashtra.gov.in", {
        "en": ("Magel Tyala Shettale (farm ponds)", "Assistance to dig a farm pond for protective irrigation.", "Farmers in Maharashtra; apply through MahaDBT / the taluka agriculture office."),
        "hi": ("मागेल त्याला शेततळे (खेत तालाब)", "सुरक्षात्मक सिंचाई के लिए खेत तालाब खुदाई में सहायता।", "महाराष्ट्र के किसान; महाडीबीटी / तालुका कृषि कार्यालय से आवेदन।"),
        "mr": ("मागेल त्याला शेततळे", "संरक्षित सिंचनासाठी शेततळे खोदण्यास सहाय्य.", "महाराष्ट्रातील शेतकरी; महाडीबीटी / तालुका कृषी कार्यालयामार्फत अर्ज.")}),
    ("up-dbt", "state", "Uttar Pradesh", "farming", "https://upagriculture.com", {
        "en": ("UP Agriculture DBT portal", "Register once for state subsidies on seed, equipment and other agriculture schemes.", "Farmers in Uttar Pradesh. Register with land and bank details."),
        "hi": ("उत्तर प्रदेश कृषि डीबीटी पोर्टल", "बीज, यंत्र और अन्य कृषि योजनाओं की राज्य सब्सिडी के लिए एक बार पंजीकरण।", "उत्तर प्रदेश के किसान। भूमि और बैंक विवरण से पंजीकरण।"),
        "mr": ("उत्तर प्रदेश कृषी डीबीटी पोर्टल", "बियाणे, यंत्रे व इतर योजनांच्या राज्य अनुदानांसाठी एकदा नोंदणी.", "उत्तर प्रदेशातील शेतकरी. जमीन व बँक तपशीलासह नोंदणी.")}),
    ("up-durghatna", "state", "Uttar Pradesh", "insurance", "https://upagriculture.com", {
        "en": ("Mukhyamantri Krishak Durghatna Kalyan Yojana", "Financial help to the family if a farmer dies or is disabled in an accident.", "Farmers and family members in Uttar Pradesh. Apply at the tehsil within the time limit."),
        "hi": ("मुख्यमंत्री कृषक दुर्घटना कल्याण योजना", "दुर्घटना में किसान की मृत्यु या विकलांगता पर परिवार को आर्थिक सहायता।", "उत्तर प्रदेश के किसान और परिवार। समय सीमा में तहसील पर आवेदन।"),
        "mr": ("मुख्यमंत्री कृषक अपघात कल्याण योजना", "अपघातात शेतकऱ्याचा मृत्यू किंवा अपंगत्व आल्यास कुटुंबाला आर्थिक मदत.", "उत्तर प्रदेशातील शेतकरी व कुटुंबीय. मुदतीत तहसीलमध्ये अर्ज.")}),
    ("pb-anaaj", "state", "Punjab", "market", "https://anaajkharid.in", {
        "en": ("Anaaj Kharid (procurement payments)", "Online gate passes, procurement at MSP and direct payment for wheat and paddy sold in Punjab mandis.", "Farmers selling wheat / paddy in Punjab. Keep land and bank details updated with the arhtiya / portal."),
        "hi": ("अनाज खरीद (खरीद भुगतान)", "पंजाब मंडियों में गेहूँ-धान की MSP पर खरीद, ऑनलाइन गेट पास और सीधा भुगतान।", "पंजाब में गेहूँ / धान बेचने वाले किसान। भूमि और बैंक विवरण अपडेट रखें।"),
        "mr": ("अनाज खरीद (खरेदी पेमेंट)", "पंजाबमधील मंडईत गहू-भाताची हमीभावाने खरेदी, ऑनलाइन गेट पास व थेट पेमेंट.", "पंजाबमध्ये गहू / भात विकणारे शेतकरी. जमीन व बँक तपशील अद्ययावत ठेवा.")}),
    ("pb-crm", "state", "Punjab", "farming", "https://agrimachinerypb.com", {
        "en": ("Crop Residue Management machinery", "Subsidy on machines for in-field straw management instead of burning (higher for custom hiring centres).", "Farmers, cooperatives and groups in Punjab. Apply on the portal in the notified window."),
        "hi": ("फसल अवशेष प्रबंधन मशीनरी", "पराली जलाने के बजाय खेत में प्रबंधन वाली मशीनों पर सब्सिडी (कस्टम हायरिंग केंद्रों को अधिक)।", "पंजाब के किसान, सहकारी समितियाँ, समूह। अधिसूचित अवधि में पोर्टल पर आवेदन।"),
        "mr": ("पीक अवशेष व्यवस्थापन यंत्रे", "पाचट जाळण्याऐवजी शेतात व्यवस्थापनासाठी यंत्रांवर अनुदान.", "पंजाबमधील शेतकरी, सहकारी संस्था, गट. अधिसूचित कालावधीत पोर्टलवर अर्ज.")}),
    ("mp-kkky", "state", "Madhya Pradesh", "income", "https://saara.mp.gov.in", {
        "en": ("Mukhyamantri Kisan Kalyan Yojana", "Additional state income support for PM-KISAN beneficiary farmers in Madhya Pradesh.", "PM-KISAN beneficiaries in Madhya Pradesh; paid automatically."),
        "hi": ("मुख्यमंत्री किसान कल्याण योजना", "मध्य प्रदेश में पीएम-किसान लाभार्थी किसानों को अतिरिक्त राज्य आय सहायता।", "मध्य प्रदेश के पीएम-किसान लाभार्थी; अपने आप भुगतान।"),
        "mr": ("मुख्यमंत्री किसान कल्याण योजना", "मध्य प्रदेशातील पीएम-किसान लाभार्थी शेतकऱ्यांना अतिरिक्त राज्य उत्पन्न सहाय्य.", "मध्य प्रदेशातील पीएम-किसान लाभार्थी; आपोआप जमा.")}),
    ("mp-euparjan", "state", "Madhya Pradesh", "market", "https://mpeuparjan.nic.in", {
        "en": ("e-Uparjan (MSP procurement)", "Register to sell wheat, paddy and other notified crops at MSP to government procurement centres.", "Farmers in Madhya Pradesh. Register before the season's deadline."),
        "hi": ("ई-उपार्जन (MSP खरीद)", "गेहूँ, धान और अन्य अधिसूचित फसलें MSP पर सरकारी खरीद केंद्रों को बेचने के लिए पंजीकरण।", "मध्य प्रदेश के किसान। मौसम की अंतिम तिथि से पहले पंजीकरण।"),
        "mr": ("ई-उपार्जन (MSP खरेदी)", "गहू, भात व इतर अधिसूचित पिके हमीभावाने शासकीय खरेदी केंद्रांना विकण्यासाठी नोंदणी.", "मध्य प्रदेशातील शेतकरी. हंगामाच्या मुदतीपूर्वी नोंदणी.")}),
    ("ka-fruits", "state", "Karnataka", "farming", "https://fruits.karnataka.gov.in", {
        "en": ("FRUITS farmer registration", "One farmer ID used for state agriculture benefits, procurement and subsidies.", "Farmers in Karnataka. Register with land records at the Raitha Samparka Kendra or online."),
        "hi": ("FRUITS किसान पंजीकरण", "राज्य कृषि लाभ, खरीद और सब्सिडी के लिए एक किसान पहचान।", "कर्नाटक के किसान। रैता संपर्क केंद्र या ऑनलाइन भूमि रिकॉर्ड से पंजीकरण।"),
        "mr": ("FRUITS शेतकरी नोंदणी", "राज्य कृषी लाभ, खरेदी व अनुदानांसाठी एकच शेतकरी ओळख.", "कर्नाटकातील शेतकरी. रैता संपर्क केंद्र किंवा ऑनलाइन नोंदणी.")}),
    ("ka-krishi-bhagya", "state", "Karnataka", "farming", "https://raitamitra.karnataka.gov.in", {
        "en": ("Krishi Bhagya", "Assistance for farm ponds and protective irrigation in rain-fed areas.", "Farmers in rain-fed areas of Karnataka. Apply at the Raitha Samparka Kendra."),
        "hi": ("कृषि भाग्य", "वर्षा-आधारित क्षेत्रों में खेत तालाब और सुरक्षात्मक सिंचाई के लिए सहायता।", "कर्नाटक के वर्षा-आधारित क्षेत्रों के किसान। रैता संपर्क केंद्र पर आवेदन।"),
        "mr": ("कृषी भाग्य", "पावसावर अवलंबून भागात शेततळे व संरक्षित सिंचनासाठी सहाय्य.", "कर्नाटकातील कोरडवाहू भागातील शेतकरी. रैता संपर्क केंद्रात अर्ज.")}),
]
CATS = {"income": ("Income support", "आय सहायता", "उत्पन्न सहाय्य"), "insurance": ("Insurance", "बीमा", "विमा"), "market": ("Selling & MSP", "बिक्री और MSP", "विक्री व हमीभाव"),
        "storage": ("Storage & transport", "भंडारण और ढुलाई", "साठवण व वाहतूक"), "farming": ("Farm support", "खेती सहायता", "शेती सहाय्य")}


def for_state(state: str | None, lang: str = "en") -> dict:
    L = lang if lang in ("en", "hi", "mr") else "en"
    st = (state or "").strip().lower()
    out = []
    for sid, level, sstate, cat, url, tr in S:
        if level == "state" and sstate.lower() != st:
            continue
        name, benefit, how = tr[L]
        out.append({"id": sid, "level": level, "state": sstate, "category": cat, "category_label": CATS[cat][("en", "hi", "mr").index(L)],
                    "name": name, "benefit": benefit, "how": how, "url": url})
    states = sorted({s[2] for s in S if s[2]})
    return {"state": state, "reviewed": REVIEWED, "schemes": out, "states_with_state_schemes": states}
