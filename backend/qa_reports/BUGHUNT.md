# Voice agent bug hunt — 2026-11-13 20:44

**128 / 167 passed (76.6%)** in 268 s · local LLM paraphrases: True · slowest turn 5770 ms

| intent | language | passed |
|---|---|---|
| add_crop | en | 8/9 |
| add_crop | hi | 0/1 |
| add_crop | mr | 1/1 |
| best_mandi | en | 5/9 |
| best_mandi | hi | 4/4 |
| best_mandi | mr | 1/1 |
| confirm_fix | en | 7/7 |
| confirm_fix | hi | 1/1 |
| confirm_fix | mr | 1/1 |
| confirm_yes | en | 8/14 |
| confirm_yes | hi | 1/1 |
| confirm_yes | mr | 1/1 |
| forecast | en | 7/8 |
| forecast | hi | 4/4 |
| forecast | mr | 1/1 |
| pending_hedge | en | 5/5 |
| pending_hedge | hi | 4/4 |
| pending_no | en | 6/7 |
| pending_no | hi | 1/1 |
| pending_no | mr | 1/1 |
| pending_yes | en | 9/13 |
| pending_yes | hi | 1/1 |
| pending_yes | mr | 2/2 |
| ready_yes | en | 9/9 |
| ready_yes | hi | 1/1 |
| ready_yes | mr | 1/1 |
| schemes | en | 10/11 |
| schemes | hi | 1/1 |
| schemes | mr | 1/1 |
| sell_hold | en | 4/8 |
| sell_hold | hi | 1/1 |
| sell_hold | mr | 1/1 |
| sell_it | en | 3/9 |
| sell_it | hi | 1/2 |
| sell_it | mr | 1/1 |
| storage | en | 5/11 |
| storage | hi | 1/1 |
| storage | mr | 1/1 |
| store_no | en | 6/9 |
| store_no | hi | 1/1 |
| store_no | mr | 1/1 |

## Failures

- **confirm_yes** `Yeah, that's right - my wheat crop is 500 kg, in the village of Sonepur, and I'm ready to go.` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintal (5,000 kg), wheat 500 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted 'wheat 500 kg' as 'onion 50 quintal (5,000 kg)' due to a missing unit specification in the yes/no word list. The phrase '500 kg' was not correctly parsed as 'wheat' without a unit conversion context, leading to 
- **confirm_yes** `Okay, so the read-back says 500 kg of wheat, Sonepur village, and I confirm it's correct - I'm all set.` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintal (5,000 kg), wheat 500 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted 'wheat 500 kg' as 'onion 50 quintal (5,000 kg)' due to a missing phrase 'wheat' in the yes/no word list, causing it to default to onion (a common crop in the region). The phrase 'Sonepur village' was also mislau
- **confirm_yes** `Hmm, the system says 500 kg wheat, Sone:pur village, and yep, that's exactly what I have - I'm good to go.` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintal (5,000 kg), wheat 500 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted '500 kg wheat' as '50 quintal (5,000 kg) wheat' because it assumed the unit was quintal instead of kilograms, likely due to a missing unit specification in the yes/no word list or a misinterpretation of the unit
- **confirm_yes** `Haan, bhaiya, crop kya hai? 100 kg, village kya hai? Kharagpur, hai, correct hai, ready ho gaya!` → stayed in collecting (confirm)  
  reply: I understood: onion 100 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted 'Kharagpur' as 'Niphad' because it didn't have a phrase for 'Kharagpur' in its language model. The phrase 'Kharagpur' is a village name in India, but the assistant's model likely used a different language or had
- **confirm_yes** `Yes, bhai, crop is 100 kg, village is Kharagpur, read-back correct hai, ready to go!` → stayed in collecting (confirm); slow (4.5 s)  
  reply: I understood: onion 100 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted 'Kharagpur' as 'Niphad' due to a missing or incorrect mapping in the location database, causing the assistant to use a different village name from the farmer's input. This likely happened because the assistant's
- **confirm_yes** `Aye, crop 100 kg, village Kharag: Kharagpur, read-back sahi hai, ready ho gaya!` → stayed in collecting (confirm)  
  reply: I understood: onion 100 kg. Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant misinterpreted 'Kharagpur' as 'Niphad' due to a missing or incorrect mapping in the location database. The phrase 'Kharagpur' is a specific village name in India, but the assistant's system likely used a different location (N.
- **store_no** `Hey, can you help me? I can't store my produce, it's just too much.` → can_store became None  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: the phrase 'cannot store' was not in the yes/no word list for the 'can_store' feature, so the assistant interpreted 'I can't store' as 'can_store' being None instead of a negative statement about storage capability. The yes/no word list for
- **store_no** `Um, I'm trying to figure out how to store my crops, but I don't have the space for it.` → can_store became None  
  reply: Sorry, I did not catch that. Can you store the produce for a few days if it pays more? (yes or no)  
  diagnosis: the assistant did not recognize the phrase 'cannot store the produce' as a negative response to the question about storing for a few days, leading to a misinterpretation of the farmer's intent. the farmer was trying to express that they don
- **store_no** `I'm sorry, but I can't store the produce—I don't have enough room in my barn.` → can_store became None  
  reply: Sorry, I did not catch that. Can you store the produce for a few days if it pays more? (yes or no)  
  diagnosis: the phrase 'can store' was not in the yes/no word list for the assistant to recognize as a valid option for the user's question about storage capacity and payment terms (the assistant expected a simple yes/no response to the question 'can I
- **pending_yes** `Aapne kaha hai ki mera 300 kg khadiya khet ka khadiya bhi chhod diya hai, toh main aaj hi order bana do, thoda sa time b` → no order created (confirming_action)  
  reply: Changed to onion 300 kg. Best option: Sell at APMC Pimpalgaon Baswant, Nashik, Maharashtra today. You keep about ₹11,801. Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response assumes the farmer will confirm the order creation by saying 'yes' or 'no', but the farmer's original message indicates agreement to create the order immediately (with a time constraint). The farmer's phrase 'thoda'
- **pending_yes** `Haan, bhaiya, main accept karta hoon, thoda wait karo, abhi kuch chhota sa change karna hai.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The farmer's phrase 'main accept karta hoon' (I agree) was not recognized as a positive confirmation in the yes/no word list because the assistant only expects 'yes' or 'no' for acceptance. The phrase 'thoda wait karo' (please wait a bit) +
- **pending_yes** `Aapne kaha tha, toh main accept karta hoon, lekin ek chhota sa request hai, please wait 2 seconds.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The farmer's response 'Aapne kaha tha, toh main accept karta hoon, lekin ek chhota sa request hai, please wait 2 seconds.' was not recognized as a 'yes' due to the phrase 'please wait 2 seconds' being too long and not in the yes/no wordlist
- **pending_yes** `Yes, bhai, main agree karta hoon, but just a sec, kuch small thing change karne hai.` → no order created (confirming_action); said it did not understand  
  reply: I did not understand. Try: "where should I sell", "show the forecast", "should I hold", "book transport" or "create the order". Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The farmer's response 'Yes, bhai, main agree karta hoon, but just a sec, kuch small thing change karne hai.' contains the phrase 'kuch small thing change karne hai' which translates to 'some small thing to change' in English. The assistant,
- **pending_no** `Hmm, abhi koi bhi order nahi karna, chhote sa bhi karo, maine apne kisan ke saath bhi kya kya khaali hai, so abhi sale k` → said it did not understand  
  reply: I did not understand. Try: "where should I sell", "show the forecast", "should I hold", "book transport" or "create the order". Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The farmer's phrase 'abhi koi bhi order nahi karna' was misinterpreted as a request to create a sale order, but the assistant's response list of options does not include the phrase 'abhi koi bhi order nahi karna' or a clear indication that 
- **best_mandi** `Could you tell me the best mandi for selling my rice? I'm not sure which one to go to.` → ran ['read_aloud']  
  reply: Best option: Sell at APMC Pimpalgaon Baswant, Nashik, Maharashtra today. You keep about ₹2,07,180.  
  diagnosis: The assistant's response is too specific and assumes the farmer wants to sell today at a particular APMC market, but the farmer's question was about which mandi (market) is best for selling rice in general, not a specific time or location. 
- **best_mandi** `Hey, can you tell me which mandi is best for selling my wheat today? I'm a bit confused between the two options.` → ran ['read_aloud']  
  reply: Best option: Sell at APMC Pimpalgaon Baswant, Nashik, Maharashtra today. You keep about ₹2,07,180.  
  diagnosis: The phrase 'which mandi' was misinterpreted as 'best option' instead of 'where to sell' or 'which mand: the farmer intended to ask for the name of the mandi (market) to sell at, but the assistant assumed it was asking for the best option to
- **best_mandi** `Saw a lot of people talking about the new mandi near the city, but I'm not sure if it's the right one. Can you help me?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'where to sell' is missing from the yes/no word list, so the assistant didn't recognize the farmer's intent to find the best mandi for selling crops. The assistant's response focuses on features like comparing mandis, explaining,
- **best_mandi** `Mandi? Oh, I need to sell my rice soon. Which one is the best place to sell it? I mean, I've heard of two places but I'm` → ran ['create_order']  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response assumes the farmer wants to create a sale order, but the farmer's actual intent was to ask about the best mandi (market) to sell rice. The phrase 'which one is the best place to sell it' implies the farmer is asking
- **sell_hold** `Hey, so I'm thinking about my wheat crop—should I sell it now or hold it for the market? I'm a bit nervous about the价格.` → ran ['create_order']  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The phrase 'price' was misinterpreted as 'sale' due to the assistant's context of the farmer's concern about crop pricing, but the assistant's response incorrectly assumed a sale order creation without acknowledging the price concern. The '
- **sell_hold** `Umm, hi there, voice assistant—can you check if I should sell my rice now or wait until next week? I don't want to miss出` → ran ['forecast']  
  reply: Forecast for APMC Pimpalgaon Baswant: in 1 days about ₹4,203 (₹4,074 to ₹4,507); in 3 days about ₹4,242 (₹4,035 to ₹4,913). Not a guarantee.  
  diagnosis: The phrase 'hold the crop' was not recognized as a valid option in the yes/no word list for the farmer's question. The farmer intended to ask whether to sell now or wait (i.e., hold the crop) until next week, but the assistant only provided
- **sell_hold** `Hello, I'm a farmer in India, so I need your help: should I sell my mangoes today or keep them for higher prices later?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'should I sell now or hold' is missing from the yes/no word list, causing the assistant to misinterpret the farmer's request as a command to list actions rather than a yes/no question about selling strategy. The farmer's actual意图
- **sell_hold** `Bhai, is it better to sell now or keep the crop? I'm worried about the price going down.` → ran ['forecast']  
  reply: Forecast for APMC Pimpalgaon Baswant: in 1 days about ₹4,203 (₹4,074 to ₹4,507); in 3 days about ₹4,242 (₹4,035 to ₹4,913). Not a guarantee.  
  diagnosis: The phrase 'sell now or keep' was not recognized as a yes/no question. The farmer's query was intended to be a yes/no question about whether to sell now or hold the crop, but the assistant interpreted it as a request for price forecasts. A 
- **forecast** `Mera kisan hai, kya next week ke ghee ke price kya hoga? Please help me out.` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'next week' was not recognized as a time reference in the context of price forecasting. The assistant's response focuses on general actions (e.g., 'show the forecast') but does not specify the time frame for the price prediction,
- **add_crop** `अरे ये तो बहुत अच्छा है, मैंने अपने फसल से 500 किलोग्राम चावल लेकर आया है, और अगले फसल में तो 300 किलोग्राम चावल हैं जोम` → slow (5.8 s)  
  reply: नया माल: Niphad के पास चावल 500 किलो। सबसे अच्छा विकल्प: आज APMC पुणे, पुणे, महाराष्ट्र में बेचें। आपके हाथ में लगभग ₹32,650। नया माल: Niphad के पास चावल 300 किलो। सबसे अच्छा विकल्प: आज APMC पुणे, पुणे, महाराष्ट्र में बे  
  diagnosis: 
- **add_crop** `Hai, aapke sath kya kya karte hain? Main 300 kg khadi ka crop bhi hai, kya aapko chahiye?` → ran ['set_qty']  
  reply: Changed to onion 300 kg. Best option: Sell at APMC Pimpalgaon Baswant, Nashik, Maharashtra today. You keep about ₹11,801.  
  diagnosis: The phrase 'khadi' was misinterpreted as 'onion' due to the assistant's language model not recognizing the context of the crop type. The word 'khadi' in Hindi means 'dry' or 'dried', but the assistant incorrectly mapped it to 'onion' (a cro
- **sell_it** `Hey, can you help me sell my wheat? I've got a big bag here, need to get it out quickly.` → no yes/no question (plan)  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The farmer's request is a command to create an order for selling wheat, but the assistant's response implies the assistant is providing information rather than executing the action. The root cause is that the assistant's yes/no question (or
- **sell_it** `Could you please create an order for my rice? I'm a bit busy right now, so just make it happen.` → slow (5.7 s)  
  reply: New lot: rice 1 kg near Niphad. Best option: Sell at APMC Ulhasnagar, Thane, Maharashtra today. You keep about ₹-2,831. Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response includes a negative amount (₹-2,831) which is confusing and incorrect for a sale order. The root cause is likely that the assistant's system is not properly handling negative values in financial contexts, or it's a 
- **sell_it** `Um, I need to sell my tomatoes today. Like, really fast, please? I don't want to wait too long.` → no yes/no question (plan)  
  reply: SELL NOW. No hold option clears the extra costs, loss and risk. No reliable forecast for the 7, 15, 30 day window(s); Best hold (3 d) changes net by Rs -2,325 with about 45% chance of a lower price; Spoilage risk on the   
  diagnosis: The farmer's request for 'sell now' was not explicitly recognized as a yes/no question in the assistant's plan. The assistant's response assumes a 'no hold' option is available, but the farmer's intent was to create an order immediately, so
- **sell_it** `अरे बात ये बात बहुत ज्यादा बात है ये तो बात है तो बात करूँ तो बात करूँ तो बात करूँ तो बात करूँ तो बात करूँ तो बात करूँ त` → no yes/no question (plan); said it did not understand  
  reply: मैं समझा नहीं। कहिए: "कहाँ बेचूँ", "भाव अनुमान दिखाओ", "रोकूँ या बेचूँ", "ट्रक बुक करो" या "ऑर्डर बनाओ"।  
  diagnosis: The farmer's query is a repetitive phrase that does not form a clear yes/no question or command. The assistant's response suggests that the system expects specific phrases like 'कहाँ बेचूँ' (where to sell), 'भाव अनुमान दिखाओ' (show price), 
- **sell_it** `Hey, can you help me sell my wheat? I have 500 kg ready for delivery today.` → no yes/no question (plan)  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The farmer's request is a command to create an order for selling wheat, but the assistant's yes/no question plan does not include a phrase that directly matches the farmer's intent to 'create the order' (e.g., 'create order', 'sell now', 'I
- **sell_it** `Please create an order for my 300 kg of rice, it's urgent, need to get it sold by tomorrow.` → no yes/no question (plan)  
  reply: New lot: rice 300 kg near Niphad. Best option: Sell at APMC Pune, Pune, Maharashtra today. You keep about ₹18,154.  
  diagnosis: The phrase 'sell' was not in the yes/no word list for the 'create order' action, so the assistant assumed 'create order' meant to create a new lot of rice instead of selling it. The root cause is that the yes/no word list for the 'create' (
- **sell_it** `Could you please help me with selling my tomatoes? I have a lot, and I want to make sure it gets ordered quickly.` → no yes/no question (plan)  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The farmer's request does not contain a clear yes/no question that the assistant can respond to. The assistant's response is a list of actions rather than a direct yes/no answer to the farmer's request. The root cause is that the farmer's '
- **schemes** `Could you help me check what government schemes I'm eligible for as a farmer?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'government schemes' was not recognized as a valid command in the yes/no word list. The assistant's response indicates it only understands commands related to selling, comparing mandis, etc., but not government schemes or related
- **storage** `Hey, can you tell me where the nearest cold storage or warehouse is? I need to store some produce before it gets spoiled` → ran ['spoilage']  
  reply: Spoilage risk on the best trip: SAFE (2%, about 2.5 hours).  
  diagnosis: The phrase 'near me' was missing from the query, causing the assistant to interpret the request as a general query about spoilage risk rather than a location-based request for cold storage or warehouses near the user's current location. The
- **storage** `Do you know any cold storage facilities or warehouses close by? I'm trying to get my crops to a safe place quickly` → ran ['list_crops']  
  reply: Your crops: onion 50 quintal (5,000 kg). Say a crop name to switch.  
  diagnosis: The assistant's response indicates it's using a list of crops (onion) but the farmer's query was about cold storage facilities, not crop names. The root cause is that the assistant is responding with crop data instead of location-based cold
- **storage** `Aapke paas kya cold storage ya warehouse hai neeche? Main ek chhota sa kisan hoon, aapko kya help chahiye?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'neeche' (meaning 'below' or 'near') was not recognized as a location query in the yes/no word list, causing the assistant to default to a generic help list instead of addressing the farmer's question about nearby cold storage or
- **storage** `Kya aapke area mein koi cold storage ya warehouse hai? Main neeche se puch raha hoon, kya aapko koi help chahiye?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'cold storage' or 'warehouse' was not included in the yes/no word list for the farmer's question, so the assistant interpreted 'help' as a command rather than a request for information about storage facilities. The assistant's 'I
- **storage** `Aapke paas kya cold storage ya warehouse hai? Main ek chhota sa kisan hoon, aapko kya help chahiye?` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The phrase 'near me' is missing from the yes/no word list, causing the assistant to assume the farmer is asking about general options rather than nearby facilities. The assistant's response lists generic features without filtering for the '
- **storage** `Pls help, I'm looking for a cold storage facility near here. My crops are getting cold, so I need it ASAP.` → ran ['help']  
  reply: I can tell you where to sell, compare mandis, explain sell now or hold, show the forecast, storage and transport, check a price, change a cost ("set commission to 3"), add a crop, and create and track an order. Say "star  
  diagnosis: The assistant's response indicates it's trying to list features or actions (e.g., 'sell', 'mandis', 'storage and transport') but the farmer's request was specifically about finding a cold storage facility near them. The root cause is likely
