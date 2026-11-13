"""Government schemes for farmers that relate to selling, storing, insuring and income (central + state), with official portals.
Curated, short and conservative: amounts and rules change, so every card links to the official site. Credit / loan products are
intentionally not listed (out of scope for this platform). Reviewed 2026-11.
Farmers can ask by state, by kind (insurance / income / MSP / storage / farm support) or by scheme name: see parse() and for_state()."""

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
    ("rwbcis", "central", None, "insurance", "https://pmfby.gov.in", {
        "en": ("Weather Based Crop Insurance (RWBCIS)", "Crop insurance that pays on measured weather (rain, temperature, humidity) instead of a field survey; used mostly for fruit and vegetable crops.", "Farmers growing notified crops in notified areas. Enrol through your bank, CSC or the PMFBY portal before the cut-off date."),
        "hi": ("मौसम आधारित फसल बीमा (RWBCIS)", "खेत सर्वे के बजाय मापे गए मौसम (बारिश, तापमान, नमी) के आधार पर भुगतान करने वाला फसल बीमा; ज़्यादातर फल-सब्ज़ी फसलों के लिए।", "अधिसूचित क्षेत्र में अधिसूचित फसल उगाने वाले किसान। अंतिम तिथि से पहले बैंक, CSC या PMFBY पोर्टल से नामांकन।"),
        "mr": ("हवामान आधारित पीक विमा (RWBCIS)", "शेत पाहणीऐवजी मोजलेल्या हवामानावर (पाऊस, तापमान, आर्द्रता) भरपाई देणारा पीक विमा; मुख्यतः फळे-भाजीपाला पिकांसाठी.", "अधिसूचित क्षेत्रात अधिसूचित पिके घेणारे शेतकरी. अंतिम तारखेपूर्वी बँक, CSC किंवा PMFBY पोर्टलवर नोंदणी.")}),
    ("pmksy", "central", None, "farming", "https://pmksy.gov.in", {
        "en": ("PMKSY - Per Drop More Crop", "Subsidy for drip and sprinkler irrigation to save water.", "All farmers. Apply through the state agriculture / horticulture department portal."),
        "hi": ("पीएमकेएसवाई - प्रति बूंद अधिक फसल", "पानी बचाने के लिए ड्रिप और स्प्रिंकलर सिंचाई पर सब्सिडी।", "सभी किसान। राज्य कृषि / बागवानी विभाग के पोर्टल से आवेदन।"),
        "mr": ("पीएमकेएसवाय - प्रति थेंब अधिक पीक", "पाणी बचतीसाठी ठिबक व तुषार सिंचनावर अनुदान.", "सर्व शेतकरी. राज्य कृषी / फलोत्पादन विभागाच्या पोर्टलवर अर्ज.")}),
    ("midh", "central", None, "farming", "https://midh.gov.in", {
        "en": ("Horticulture Mission (MIDH)", "Assistance for fruit and vegetable growers: planting material, protected cultivation, pack houses and cold storage.", "Farmers, groups and FPOs. Apply through the state horticulture mission."),
        "hi": ("बागवानी मिशन (MIDH)", "फल-सब्ज़ी उत्पादकों को सहायता: रोपण सामग्री, संरक्षित खेती, पैक हाउस और कोल्ड स्टोरेज।", "किसान, समूह और FPO। राज्य बागवानी मिशन से आवेदन।"),
        "mr": ("फलोत्पादन अभियान (MIDH)", "फळे-भाजीपाला उत्पादकांना सहाय्य: लागवड साहित्य, संरक्षित शेती, पॅक हाऊस व शीतगृह.", "शेतकरी, गट व FPO. राज्य फलोत्पादन अभियानामार्फत अर्ज.")}),
    ("mh-kanda-chawl", "state", "Maharashtra", "storage", "https://mahadbt.maharashtra.gov.in", {
        "en": ("Kanda Chawl (onion storage structure)", "Subsidy to build an onion storage structure on the farm so onions can be held and sold later.", "Onion farmers in Maharashtra. Apply on MahaDBT under horticulture components."),
        "hi": ("कांदा चाळ (प्याज भंडारण ढाँचा)", "खेत पर प्याज भंडारण ढाँचा बनाने पर सब्सिडी, ताकि प्याज रोककर बाद में बेचा जा सके।", "महाराष्ट्र के प्याज किसान। महाडीबीटी पर बागवानी घटक में आवेदन।"),
        "mr": ("कांदा चाळ", "शेतावर कांदा चाळ उभारण्यासाठी अनुदान, म्हणजे कांदा साठवून नंतर विकता येतो.", "महाराष्ट्रातील कांदा उत्पादक शेतकरी. महाडीबीटीवर फलोत्पादन घटकाखाली अर्ज.")}),
    ("mh-apghat", "state", "Maharashtra", "insurance", "https://krishi.maharashtra.gov.in", {
        "en": ("Gopinath Munde Shetkari Apghat Suraksha", "Financial help to the family if a farmer dies or is disabled in an accident.", "Farmers and family members in Maharashtra. Apply at the taluka agriculture office with the accident papers."),
        "hi": ("गोपीनाथ मुंडे शेतकरी अपघात सुरक्षा", "दुर्घटना में किसान की मृत्यु या विकलांगता पर परिवार को आर्थिक सहायता।", "महाराष्ट्र के किसान और परिवार। दुर्घटना के कागज़ात के साथ तालुका कृषि कार्यालय में आवेदन।"),
        "mr": ("गोपीनाथ मुंडे शेतकरी अपघात सुरक्षा", "अपघातात शेतकऱ्याचा मृत्यू किंवा अपंगत्व आल्यास कुटुंबाला आर्थिक मदत.", "महाराष्ट्रातील शेतकरी व कुटुंबीय. अपघाताच्या कागदपत्रांसह तालुका कृषी कार्यालयात अर्ज.")}),
    ("tg-rythu-bharosa", "state", "Telangana", "income", "https://rythubharosa.telangana.gov.in", {
        "en": ("Rythu Bharosa", "State investment support paid per acre each crop season to farmers in Telangana.", "Farmers with land records in Telangana; paid to the bank account."),
        "hi": ("रैतु भरोसा", "तेलंगाना के किसानों को हर फसल मौसम में प्रति एकड़ राज्य निवेश सहायता।", "तेलंगाना में भूमि रिकॉर्ड वाले किसान; बैंक खाते में भुगतान।"),
        "mr": ("रयतू भरोसा", "तेलंगणातील शेतकऱ्यांना प्रत्येक हंगामात प्रति एकर राज्य गुंतवणूक सहाय्य.", "तेलंगणात जमीन नोंद असलेले शेतकरी; बँक खात्यात जमा.")}),
    ("tg-rythu-bima", "state", "Telangana", "insurance", "https://agri.telangana.gov.in", {
        "en": ("Rythu Bima (farmer life insurance)", "Life insurance cover for farmers; the state pays the premium and the family receives the claim if the farmer dies.", "Landholding farmers aged 18 to 59 in Telangana. Enrol through the agriculture extension officer."),
        "hi": ("रैतु बीमा (किसान जीवन बीमा)", "किसानों के लिए जीवन बीमा; प्रीमियम राज्य देता है और किसान की मृत्यु पर परिवार को दावा मिलता है।", "तेलंगाना के 18 से 59 वर्ष के भूमिधारक किसान। कृषि विस्तार अधिकारी के माध्यम से नामांकन।"),
        "mr": ("रयतू विमा (शेतकरी जीवन विमा)", "शेतकऱ्यांसाठी जीवन विमा; हप्ता राज्य भरते आणि शेतकऱ्याच्या मृत्यूनंतर कुटुंबाला दावा मिळतो.", "तेलंगणातील 18 ते 59 वयोगटातील जमीनधारक शेतकरी. कृषी विस्तार अधिकाऱ्यामार्फत नोंदणी.")}),
    ("ap-annadata", "state", "Andhra Pradesh", "income", "https://annadathasukhibhava.ap.gov.in", {
        "en": ("Annadata Sukhibhava", "State income support for farmer families in Andhra Pradesh, paid along with PM-KISAN.", "Farmer families in Andhra Pradesh; check status on the portal."),
        "hi": ("अन्नदाता सुखीभव", "आंध्र प्रदेश के किसान परिवारों को राज्य आय सहायता, पीएम-किसान के साथ।", "आंध्र प्रदेश के किसान परिवार; पोर्टल पर स्थिति देखें।"),
        "mr": ("अन्नदाता सुखीभव", "आंध्र प्रदेशातील शेतकरी कुटुंबांना राज्य उत्पन्न सहाय्य, पीएम-किसानसोबत.", "आंध्र प्रदेशातील शेतकरी कुटुंबे; पोर्टलवर स्थिती पाहा.")}),
    ("od-cm-kisan", "state", "Odisha", "income", "https://cmkisan.odisha.gov.in", {
        "en": ("CM-KISAN (earlier KALIA)", "State income support for small and marginal farmers and landless agricultural households in Odisha.", "Eligible households in Odisha; register and check status on the portal."),
        "hi": ("सीएम-किसान (पहले कालिया)", "ओडिशा के छोटे-सीमांत किसानों और भूमिहीन कृषि परिवारों को राज्य आय सहायता।", "ओडिशा के पात्र परिवार; पोर्टल पर पंजीकरण और स्थिति देखें।"),
        "mr": ("सीएम-किसान (पूर्वीचे कालिया)", "ओडिशातील लहान-अल्पभूधारक शेतकरी व भूमिहीन कृषी कुटुंबांना राज्य उत्पन्न सहाय्य.", "ओडिशातील पात्र कुटुंबे; पोर्टलवर नोंदणी व स्थिती पाहा.")}),
    ("wb-krishak-bandhu", "state", "West Bengal", "income", "https://krishakbandhu.wb.gov.in", {
        "en": ("Krishak Bandhu", "State income support for farmers in West Bengal, plus a death benefit to the family.", "Farmers and recorded sharecroppers in West Bengal. Apply through the block agriculture office."),
        "hi": ("कृषक बंधु", "पश्चिम बंगाल के किसानों को राज्य आय सहायता, और परिवार को मृत्यु लाभ।", "पश्चिम बंगाल के किसान और दर्ज बटाईदार। ब्लॉक कृषि कार्यालय से आवेदन।"),
        "mr": ("कृषक बंधू", "पश्चिम बंगालमधील शेतकऱ्यांना राज्य उत्पन्न सहाय्य, तसेच कुटुंबाला मृत्यू लाभ.", "पश्चिम बंगालमधील शेतकरी व नोंदणीकृत बटाईदार. ब्लॉक कृषी कार्यालयामार्फत अर्ज.")}),
    ("gj-ikhedut", "state", "Gujarat", "farming", "https://ikhedut.gujarat.gov.in", {
        "en": ("i-Khedut portal", "One portal to apply for Gujarat agriculture, horticulture and storage subsidies.", "Farmers in Gujarat. Apply online in the open window for each scheme."),
        "hi": ("आई-खेडूत पोर्टल", "गुजरात की कृषि, बागवानी और भंडारण सब्सिडी के आवेदन के लिए एक पोर्टल।", "गुजरात के किसान। हर योजना की खुली अवधि में ऑनलाइन आवेदन।"),
        "mr": ("आय-खेडूत पोर्टल", "गुजरातच्या कृषी, फलोत्पादन व साठवण अनुदानांच्या अर्जासाठी एकच पोर्टल.", "गुजरातमधील शेतकरी. प्रत्येक योजनेच्या खुल्या कालावधीत ऑनलाइन अर्ज.")}),
    ("rj-rajkisan", "state", "Rajasthan", "farming", "https://rajkisan.rajasthan.gov.in", {
        "en": ("Raj Kisan Saathi portal", "One portal to apply for Rajasthan agriculture subsidies such as farm ponds, pipelines, machinery and drip irrigation.", "Farmers in Rajasthan. Apply with Jan Aadhaar on the portal or at an e-Mitra centre."),
        "hi": ("राज किसान साथी पोर्टल", "खेत तालाब, पाइपलाइन, कृषि यंत्र और ड्रिप जैसी राजस्थान कृषि सब्सिडी के लिए एक पोर्टल।", "राजस्थान के किसान। जन आधार से पोर्टल या ई-मित्र केंद्र पर आवेदन।"),
        "mr": ("राज किसान साथी पोर्टल", "शेततळे, पाइपलाइन, कृषी यंत्रे व ठिबक यांसारख्या राजस्थान कृषी अनुदानांसाठी एकच पोर्टल.", "राजस्थानमधील शेतकरी. जन आधारसह पोर्टलवर किंवा ई-मित्र केंद्रात अर्ज.")}),
    ("hr-mfmb", "state", "Haryana", "market", "https://fasal.haryana.gov.in", {
        "en": ("Meri Fasal Mera Byora", "Register your crop each season; needed to sell at MSP in Haryana mandis and to get state scheme benefits.", "All farmers in Haryana. Register the sown crop on the portal every season."),
        "hi": ("मेरी फसल मेरा ब्योरा", "हर मौसम में फसल का पंजीकरण; हरियाणा की मंडियों में MSP पर बिक्री और राज्य योजनाओं के लाभ के लिए ज़रूरी।", "हरियाणा के सभी किसान। हर मौसम में बोई गई फसल पोर्टल पर दर्ज करें।"),
        "mr": ("मेरी फसल मेरा ब्योरा", "प्रत्येक हंगामात पिकाची नोंदणी; हरियाणाच्या मंडईत हमीभावाने विक्री व राज्य योजनांच्या लाभासाठी आवश्यक.", "हरियाणातील सर्व शेतकरी. प्रत्येक हंगामात पेरलेले पीक पोर्टलवर नोंदवा.")}),
    ("hr-bhavantar", "state", "Haryana", "market", "https://fasal.haryana.gov.in", {
        "en": ("Bhavantar Bharpai Yojana", "Pays the difference when notified vegetables and fruits sell below a protected price in Haryana mandis.", "Farmers in Haryana who registered the crop on Meri Fasal Mera Byora and sold it in the notified period."),
        "hi": ("भावांतर भरपाई योजना", "हरियाणा की मंडियों में अधिसूचित सब्ज़ी-फल संरक्षित मूल्य से कम बिकने पर अंतर का भुगतान।", "हरियाणा के किसान जिन्होंने मेरी फसल मेरा ब्योरा पर फसल दर्ज की और अधिसूचित अवधि में बेची।"),
        "mr": ("भावांतर भरपाई योजना", "हरियाणाच्या मंडईत अधिसूचित भाजीपाला-फळे संरक्षित दरापेक्षा कमी भावात विकल्यास फरकाची भरपाई.", "मेरी फसल मेरा ब्योरा वर पीक नोंदवून अधिसूचित कालावधीत विकलेले हरियाणातील शेतकरी.")}),
    ("br-dbt", "state", "Bihar", "farming", "https://dbtagriculture.bihar.gov.in", {
        "en": ("Bihar Agriculture DBT portal", "Register once for state subsidies on seed, diesel, machinery and other agriculture schemes.", "Farmers in Bihar. Register with Aadhaar and bank details."),
        "hi": ("बिहार कृषि डीबीटी पोर्टल", "बीज, डीज़ल, यंत्र और अन्य कृषि योजनाओं की राज्य सब्सिडी के लिए एक बार पंजीकरण।", "बिहार के किसान। आधार और बैंक विवरण से पंजीकरण।"),
        "mr": ("बिहार कृषी डीबीटी पोर्टल", "बियाणे, डिझेल, यंत्रे व इतर कृषी योजनांच्या राज्य अनुदानांसाठी एकदा नोंदणी.", "बिहारमधील शेतकरी. आधार व बँक तपशीलासह नोंदणी.")}),
    ("br-fasal-sahayata", "state", "Bihar", "insurance", "https://esahkari.bihar.gov.in", {
        "en": ("Bihar Rajya Fasal Sahayata Yojana", "State crop-loss assistance when yield falls because of a natural calamity; the farmer pays no premium.", "Farmers and sharecroppers in Bihar. Register on the cooperative department portal each season."),
        "hi": ("बिहार राज्य फसल सहायता योजना", "प्राकृतिक आपदा से उपज घटने पर राज्य की फसल-नुकसान सहायता; किसान को कोई प्रीमियम नहीं देना।", "बिहार के किसान और बटाईदार। हर मौसम में सहकारिता विभाग के पोर्टल पर पंजीकरण।"),
        "mr": ("बिहार राज्य फसल सहायता योजना", "नैसर्गिक आपत्तीमुळे उत्पादन घटल्यास राज्याची पीक-नुकसान मदत; शेतकऱ्याला हप्ता भरावा लागत नाही.", "बिहारमधील शेतकरी व बटाईदार. प्रत्येक हंगामात सहकार विभागाच्या पोर्टलवर नोंदणी.")}),
]
CATS = {"income": ("Income support", "आय सहायता", "उत्पन्न सहाय्य"), "insurance": ("Insurance", "बीमा", "विमा"), "market": ("Selling & MSP", "बिक्री और MSP", "विक्री व हमीभाव"),
        "storage": ("Storage & transport", "भंडारण और ढुलाई", "साठवण व वाहतूक"), "farming": ("Farm support", "खेती सहायता", "शेती सहाय्य")}


# words a farmer may use -> category (Latin lowercased; Devanagari as written)
CAT_WORDS = {"insurance": "bima beema insurance vima veema accident durghatna apghat बीमा विमा दुर्घटना अपघात",
             "income": "income pension paisa kist kisht installment samman sanman आय पेंशन पेन्शन किस्त हप्ता सम्मान उत्पन्न",
             "market": "msp procurement kharid hamibhav samarthan bhavantar e-nam enam खरीद खरेदी हमीभाव समर्थन भावांतर",
             "storage": "storage godown godam warehouse cold chawl bhandaran sathvan भंडारण गोदाम साठवण चाळ शीतगृह",
             "farming": "solar pump drip sprinkler irrigation sinchai machinery tractor yantra soil mitti pond talab shettale horticulture "
                        "सौर पंप ड्रिप ठिबक सिंचाई सिंचन यंत्र ट्रैक्टर ट्रॅक्टर मिट्टी माती तालाब शेततळे बागवानी फलोत्पादन"}
# spoken names -> scheme id, so "PM kisan dikhao" opens exactly that card
ALIASES = {"pm-kisan": "pm kisan|pmkisan|pm-kisan|kisan samman|पीएम किसान|पीएम-किसान|किसान सम्मान", "pmfby": "pmfby|fasal bima|pik vima|crop insurance|फसल बीमा|पीक विमा",
           "enam": "e-nam|enam|e nam|ई-नाम|ई नाम", "pm-aasha": "pm aasha|pm-aasha|पीएम आशा|पीएम-आशा", "op-greens": "operation greens|ऑपरेशन ग्रीन",
           "pm-kmy": "maan dhan|maandhan|mandhan|मान-धन|मानधन", "shc": "soil health|mitti jaanch|मृदा|माती तपासणी", "pm-kusum": "kusum|solar pump|कुसुम|सौर पंप",
           "rwbcis": "rwbcis|weather based|mausam adharit|मौसम आधारित|हवामान आधारित", "pmksy": "pmksy|per drop|प्रति बूंद|प्रति थेंब", "midh": "midh|horticulture mission|बागवानी मिशन",
           "mh-nsmny": "namo shetkari|नमो शेतकरी", "mh-mahadbt": "mahadbt|maha dbt|महाडीबीटी", "mh-shettale": "shettale|शेततळे", "mh-kanda-chawl": "kanda chawl|कांदा चाळ",
           "mh-apghat": "gopinath munde|गोपीनाथ मुंडे", "tg-rythu-bharosa": "rythu bharosa|rythu bandhu|रैतु भरोसा", "tg-rythu-bima": "rythu bima|रैतु बीमा",
           "ap-annadata": "annadata|annadatha|अन्नदाता", "od-cm-kisan": "cm kisan|cm-kisan|kalia|कालिया", "wb-krishak-bandhu": "krishak bandhu|कृषक बंधु|कृषक बंधू",
           "gj-ikhedut": "ikhedut|i-khedut|khedut|खेडूत", "rj-rajkisan": "raj kisan|rajkisan|राज किसान", "hr-mfmb": "meri fasal|मेरी फसल", "hr-bhavantar": "bhavantar|भावांतर",
           "br-fasal-sahayata": "fasal sahayata|फसल सहायता", "up-durghatna": "krishak durghatna|कृषक दुर्घटना", "mp-kkky": "kisan kalyan|किसान कल्याण",
           "mp-euparjan": "uparjan|उपार्जन", "pb-anaaj": "anaaj kharid|अनाज खरीद", "pb-crm": "crop residue|parali|पराली", "ka-fruits": "fruits registration|fruits id",
           "ka-krishi-bhagya": "krishi bhagya|कृषि भाग्य"}
# every Indian state a farmer may name (central schemes apply everywhere, so naming any of them is valid)
ALL_STATES = {"Andhra Pradesh": "andhra|आंध्र", "Assam": "assam|असम|आसाम", "Bihar": "bihar|बिहार", "Chhattisgarh": "chhattisgarh|chattisgarh|छत्तीसगढ़|छत्तीसगड",
              "Goa": "goa|गोवा", "Gujarat": "gujarat|गुजरात", "Haryana": "haryana|हरियाणा", "Himachal Pradesh": "himachal|हिमाचल", "Jharkhand": "jharkhand|झारखंड",
              "Karnataka": "karnataka|कर्नाटक", "Kerala": "kerala|केरल|केरळ", "Madhya Pradesh": "madhya pradesh| mp |मध्य प्रदेश|मध्यप्रदेश",
              "Maharashtra": "maharashtra|महाराष्ट्र", "Odisha": "odisha|orissa|ओडिशा|उड़ीसा", "Punjab": "punjab|पंजाब", "Rajasthan": "rajasthan|राजस्थान",
              "Tamil Nadu": "tamil nadu|tamilnadu|तमिलनाडु|तामिळनाडू", "Telangana": "telangana|तेलंगाना|तेलंगणा", "Uttar Pradesh": "uttar pradesh| up |उत्तर प्रदेश",
              "Uttarakhand": "uttarakhand|उत्तराखंड", "West Bengal": "west bengal|bengal|पश्चिम बंगाल|बंगाल"}
SAY = {"en": ("{what} for {state}: {names}.", "schemes", "{cat} schemes", "I have no {cat} scheme listed for {state}. Showing all schemes for {state}."),
       "hi": ("{state} के लिए {what}: {names}।", "योजनाएँ", "{cat} योजनाएँ", "{state} के लिए {cat} की कोई योजना सूची में नहीं है। {state} की सभी योजनाएँ दिखा रहा हूँ।"),
       "mr": ("{state} साठी {what}: {names}.", "योजना", "{cat} योजना", "{state} साठी {cat} ची योजना यादीत नाही. {state} च्या सर्व योजना दाखवतो.")}


def parse(text: str) -> dict:
    """What a farmer asked for, from plain words: {'state'?, 'category'?, 'q'?}. Rules only; unknown parts are left out."""
    low = " " + (text or "").lower().replace("़", "") + " "
    out = {}
    for state, pat in ALL_STATES.items():
        if any(w in low for w in pat.replace("़", "").split("|")):
            out["state"] = state
            break
    for sid, pat in ALIASES.items():
        if any(w in low for w in pat.replace("़", "").split("|")):
            out["q"] = sid
            break
    for cat, words in CAT_WORDS.items():
        if any(w in low for w in words.replace("़", "").split()):
            out["category"] = cat
            break
    return out


def _row(s, L):
    sid, level, sstate, cat, url, tr = s
    name, benefit, how = tr[L]
    return {"id": sid, "level": level, "state": sstate, "category": cat, "category_label": CATS[cat][("en", "hi", "mr").index(L)],
            "name": name, "benefit": benefit, "how": how, "url": url}


def for_state(state: str | None, lang: str = "en", category: str | None = None, q: str | None = None) -> dict:
    """Central schemes + that state's. Optional exact filters: category (income|insurance|market|storage|farming) and q (scheme id or name words)."""
    L = lang if lang in ("en", "hi", "mr") else "en"
    st = (state or "").strip().lower()
    rows = [s for s in S if s[1] == "central" or s[2].lower() == st]
    if q:
        ql = q.strip().lower()
        hit = [s for s in S if s[0] == ql] or [s for s in rows if any(ql in tr[0].lower() for tr in s[5].values())]
        rows = hit or rows
    if category in CATS and not (q and len(rows) == 1):
        rows = [s for s in rows if s[3] == category]
    states = sorted({s[2] for s in S if s[2]})
    return {"state": state, "category": category if category in CATS else None, "q": q, "reviewed": REVIEWED, "schemes": [_row(s, L) for s in rows],
            "states_with_state_schemes": states}


def say(state: str, lang: str, category: str | None = None, q: str | None = None, state_label: str | None = None) -> tuple[str, dict]:
    """Spoken one-liner naming exactly what is being shown, plus the filters that produced it (an empty category falls back to all)."""
    L = lang if lang in SAY else "en"
    tpl, all_word, cat_word, none = SAY[L]
    label = state_label or state
    d = for_state(state, L, category, q)
    cat_label = CATS[category][("en", "hi", "mr").index(L)] if category in CATS else None
    if not d["schemes"] and category:
        d = for_state(state, L, None, q)
        return none.format(cat=cat_label, state=label), {"state": state, "category": None, "q": q}
    if len(d["schemes"]) == 1:  # one scheme asked for by name: say what it gives, not just its name
        r = d["schemes"][0]
        return f"{r['name']}: {r['benefit']} {r['how']}", {"state": state, "category": None, "q": r["id"]}
    names = ", ".join(r["name"] for r in d["schemes"][:4])
    what = cat_word.format(cat=cat_label) if cat_label and len(d["schemes"]) != 1 else all_word
    return tpl.format(what=what[:1].upper() + what[1:], state=label, names=names), {"state": state, "category": category if category in CATS else None, "q": q}


def facts_text(state: str | None, category: str | None = None, q: str | None = None, limit: int = 8) -> str:
    """Compact English facts for the language model to answer scheme questions from (never from memory)."""
    return " | ".join(f"scheme {r['name']} ({r['category']}, {r['state'] or 'all India'}): {r['benefit']} How: {r['how']} Portal: {r['url']}"
                      for r in for_state(state, "en", category, q)["schemes"][:limit])
