# Voice agent bug hunt — 2026-11-13 22:39

**183 / 203 passed (90.1%)** in 178 s · local LLM paraphrases: True · slowest turn 2061 ms

| intent | language | passed |
|---|---|---|
| add_crop | en | 8/8 |
| add_crop | mr | 1/1 |
| best_mandi | en | 9/9 |
| best_mandi | hi | 4/4 |
| best_mandi | mr | 3/3 |
| confirm_fix | en | 12/12 |
| confirm_fix | hi | 2/2 |
| confirm_fix | mr | 3/3 |
| confirm_yes | en | 14/17 |
| confirm_yes | hi | 1/1 |
| confirm_yes | mr | 1/1 |
| forecast | en | 8/8 |
| forecast | hi | 3/3 |
| forecast | mr | 1/1 |
| pending_hedge | en | 8/8 |
| pending_hedge | hi | 1/1 |
| pending_hedge | mr | 1/3 |
| pending_no | en | 9/9 |
| pending_no | hi | 4/4 |
| pending_no | mr | 3/3 |
| pending_yes | en | 11/14 |
| pending_yes | hi | 1/1 |
| pending_yes | mr | 1/1 |
| ready_yes | en | 6/9 |
| ready_yes | hi | 5/5 |
| ready_yes | mr | 3/3 |
| schemes | en | 11/11 |
| schemes | hi | 1/1 |
| schemes | mr | 1/1 |
| sell_hold | en | 4/8 |
| sell_hold | hi | 3/3 |
| sell_hold | mr | 4/4 |
| sell_it | en | 8/9 |
| sell_it | hi | 2/2 |
| sell_it | mr | 3/3 |
| storage | en | 8/8 |
| storage | hi | 1/1 |
| storage | mr | 1/4 |
| store_no | en | 8/9 |
| store_no | hi | 4/4 |
| store_no | mr | 1/1 |

## Failures

- **confirm_yes** `Yeah, that's right, 50 quintals from Niphad, ready to go!` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintals (5,000 kg). Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant assumed 'Niphad' was a crop type (onion) instead of a village name, likely because the phrase 'onion 50 quintals' was misinterpreted as a crop name and quantity without context for the location. The root cause is the assistant
- **confirm_yes** `Correct, 50 quintals Niphad, all set for delivery now.` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintals (5,000 kg). Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant assumed 'Niphad' was a crop type (onion) instead of a village name, likely because the phrase 'onion 50 quintals' was misinterpreted as a crop specification without context for 'Niphad'. The root cause is the assistant's lackl
- **confirm_yes** `Yep, 50 quintals Niphad, confirmed, ready to ship!` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintals (5,000 kg). Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The assistant assumed 'Niphad' was a crop type (onion) instead of a village name, likely because the phrase list for crop types includes 'onion' but not 'Niphad' as a village. The farmer's phrase '50 quintals Niphad' was misinterpreted as '
- **ready_yes** `These onions are fresh and ready—just need to sell them, no holdup.` → ready became None  
  reply: Let us first finish your details. Is your produce ready for sale now?  
  diagnosis: The phrase 'ready for sale' was not in the yes/no word list, so the assistant interpreted 'ready' as 'None'. The assistant's response suggests it expected a confirmation of readiness but didn't have the phrase 'ready for sale' in its yes/no
- **ready_yes** `Onions are all here, ready to go; let's sell them quick before it gets busy.` → ready became None  
  reply: Let us first finish your details. Is your produce ready for sale now?  
  diagnosis: The phrase 'ready for sale' was not in the yes/no word list, so the assistant interpreted 'ready' as 'None'. The assistant expected a yes/no response but the farmer's phrase 'ready' was ambiguous without context of 'for sale'. The fix is to
- **ready_yes** `Dilli se aaya hai, ab koi bhi le sakte hain, bhaiya!` → ready became None  
  reply: Sorry, I did not catch that. Is your produce ready for sale now?  
  diagnosis: The phrase 'ready' was not recognized by the assistant's language model due to a missing context or a misinterpretation of the word 'ready' in the farmer's speech. The farmer's statement 'Dilli se aaya hai, ab koi bhi le sakte hain, bhaiya'
- **store_no** `50 quintal onion store karna mushkil hai, kya karo bhai?` → can_store became None  
  reply: Can you store the produce for a few days if it pays more? (yes or no)  
  diagnosis: the assistant's response is not in the expected language (Hindi) but the user's input was in Hindi, so the assistant should have responded in Hindi too. The assistant's response is in English, which is not matching the user's language. The 
- **pending_yes** `Haan, aaj hi karo, thoda wait kar do, bhaiya.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The farmer's phrase 'Haan, aaj hi karo, thoda wait kar do, bhaiya.' contains the word 'bhaiya' which is a Hindi/Urdu term for 'brother' and might not be recognized by the assistant's language model trained on English or a different language
- **pending_yes** `Bhaiya, aaj ke order ko confirm karo, thoda delay nahi hoga.` → no order created (confirming_action)  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The farmer's phrase 'thoda delay nahi hoga' (meaning 'there won't be much delay') was misinterpreted as a refusal to confirm the order, but the assistant's response assumed the farmer was asking to create a new order instead of confirming a
- **pending_yes** `Haan, aaj hi sale karo, thoda wait kar do, bhaiya.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The phrase 'aaj hi sale karo' was not recognized as a positive confirmation due to missing context in the yes/no word list (e.g., 'aaj hi' not being a valid yes phrase). The assistant expected a simple 'yes' or 'no' but the farmer used a ph
- **pending_hedge** `हा ओळख वाटून तुम्ही कित्ते देणार आहात?` → said it did not understand  
  reply: मला समजले नाही. म्हणा: "कुठे विकू", "भाव अंदाज दाखवा", "थांबू का विकू", "ट्रक बुक करा" किंवा "ऑर्डर तयार करा". मी सर्वोत्तम पर्यायासाठी विक्री ऑर्डर तयार करू का? होय किंवा नाही म्हणा.  
  diagnosis: The farmer's query is in Marathi, but the assistant's language model is trained on English and other languages without proper Marathi support. The assistant fails to recognize the Marathi phrase because it lacks Marathi language support in其
- **pending_hedge** `तुम्ही कित्ते देणार आहात? आणि ते कित्ते?` → said it did not understand  
  reply: मला समजले नाही. म्हणा: "कुठे विकू", "भाव अंदाज दाखवा", "थांबू का विकू", "ट्रक बुक करा" किंवा "ऑर्डर तयार करा". मी सर्वोत्तम पर्यायासाठी विक्री ऑर्डर तयार करू का? होय किंवा नाही म्हणा.  
  diagnosis: 
- **sell_hold** `Do you think prices will go up if I hold them?` → ran ['llm:forecast']  
  reply: Forecast for APMC Pimpalgaon Baswant: in 1 days about ₹4,203 (₹4,074 to ₹4,507); in 3 days about ₹4,242 (₹4,035 to ₹4,913). Not a guarantee.  
  diagnosis: The farmer's question was misinterpreted as asking about price forecasts for APMC Pimpalga: 'Do you think prices will go up if I hold them?' (intended: 'Do you think I should sell now or hold the crop?') - the assistant's response focused '
- **sell_hold** `Bhai, abhi kya hua? Main abhi sell karna hai ya hold karna?` → ran ['create_order']  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response assumes the farmer is asking about creating a sale order, but the farmer's actual question is about whether to sell now or hold the crop (i.e., a decision between two actions: sell now vs. hold). The phrase 'sell' (
- **sell_hold** `Abhi kya hua? Kya abhi sell karna hai ya koi delay karna?` → ran ['create_order']  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response assumes a yes/no decision for creating a sale order, but the farmer's query is about whether to sell now or hold the crop (i.e., a choice between two actions), not a simple yes/no confirmation. The phrase 'sell now'
- **sell_hold** `Bhai, abhi kya hua? Sell karna hai ya hold karna?` → ran ['create_order']  
  reply: Shall I create the sale order for the best option? Say yes or no.  
  diagnosis: The assistant's response assumes the user is asking about creating a sale order, but the farmer's original query was about whether to sell now or hold the crop (i.e., a decision between two actions: sell or hold). The assistant's response '
- **sell_it** `Dekh lo, 50 quintal onion, aapko kya rate chahiye?` → no yes/no question (plan)  
  reply: I have no onion price for that place in today's data.  
  diagnosis: The farmer's query is in Hindi, but the assistant's language model is trained primarily on English data, causing it to misinterpret the query as a request for onion prices in English context rather than a Hindi-speaking farmer's request to 
- **storage** `अरे, तुम तो ठारा ठारा ठारा, कोणता ठेका आहे ना?` → ran ['llm:switch_language', 'unknown']; said it did not understand  
  reply: मला समजले नाही. म्हणा: "कुठे विकू", "भाव अंदाज दाखवा", "थांबू का विकू", "ट्रक बुक करा" किंवा "ऑर्डर तयार करा".  
  diagnosis: The farmer's query is in Marathi, but the assistant's language model was not configured to handle Marathi. The phrase 'ठारा' (which means 'cold storage' or 'warehouses') is a Marathi term, but the assistant's language model was not trained/
- **storage** `कोणता ठेका आहे ना, तुम्हाला ठारा ठारा ठारा ठारा?` → ran ['llm:switch_language', 'unknown']; said it did not understand  
  reply: मला समजले नाही. म्हणा: "कुठे विकू", "भाव अंदाज दाखवा", "थांबू का विकू", "ट्रक बुक करा" किंवा "ऑर्डर तयार करा".  
  diagnosis: The phrase 'कोणता ठेका' (cold storage/warehouse) was not recognized because the language model's training data lacks specific agricultural terms like 'ठेका' (contract/warehouse) in Marathi. The assistant's response suggests it expected a 'v
- **storage** `तुम्हाला कोणता ठेका आहे, ठारा ठारा ठारा?` → ran ['llm:switch_language', 'unknown']; said it did not understand  
  reply: मला समजले नाही. म्हणा: "कुठे विकू", "भाव अंदाज दाखवा", "थांबू का विकू", "ट्रक बुक करा" किंवा "ऑर्डर तयार करा".  
  diagnosis: The phrase 'cold storage' or 'warehouses' was not in the yes/no word list for the language switcher, causing the LLM to fail to recognize the query as a yes/no question. The farmer's query was in Marathi, but the LLM was not configured to '
