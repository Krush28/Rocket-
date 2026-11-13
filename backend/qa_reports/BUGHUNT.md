# Voice agent bug hunt — 2026-11-13 22:59

**188 / 203 passed (92.6%)** in 106 s · local LLM paraphrases: True · slowest turn 3254 ms

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
| pending_hedge | mr | 3/3 |
| pending_no | en | 9/9 |
| pending_no | hi | 4/4 |
| pending_no | mr | 3/3 |
| pending_yes | en | 12/14 |
| pending_yes | hi | 1/1 |
| pending_yes | mr | 1/1 |
| ready_yes | en | 5/9 |
| ready_yes | hi | 5/5 |
| ready_yes | mr | 3/3 |
| schemes | en | 11/11 |
| schemes | hi | 1/1 |
| schemes | mr | 1/1 |
| sell_hold | en | 7/8 |
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
  diagnosis: The phrase 'ready to go' was misinterpreted as 'ready to sell now' instead of 'ready to go' (meaning ready for transport). The assistant assumed 'ready to go' meant 'ready to sell now' when it actually means the crop is ready for immediate,
- **confirm_yes** `Correct, 50 quintals Niphad, all set for delivery now.` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintals (5,000 kg). Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The phrase 'all set for delivery now' was misinterpreted as 'you cannot store it' because the assistant assumed the farmer meant they couldn't store the crop (since 'ready to sell now' implies no storage), but the farmer's original phrase '
- **confirm_yes** `Yep, 50 quintals Niphad, confirmed, ready to ship!` → stayed in collecting (confirm)  
  reply: I understood: onion 50 quintals (5,000 kg). Farm near Niphad. Ready to sell now. You cannot store it. Is this correct?  
  diagnosis: The phrase 'confirmed' was misinterpreted as a yes/no confirmation instead of a confirmation of read-back details. The assistant expected a yes/no response but the farmer used 'confirmed' to mean the read-back was correct, which is a type '
- **ready_yes** `These onions are fresh and ready—just need to sell them, no holdup.` → ready became None  
  reply: Let us first finish your details. Is your produce ready for sale now?  
  diagnosis: The phrase 'ready' was misinterpreted as 'None' because the assistant's yes/no list didn't include the context of 'produce ready for sale now' as a confirmation. The farmer's statement 'These onions are fresh and ready—just need to sell' is
- **ready_yes** `Onions are all here, ready to go; let's sell them quick before it gets busy.` → ready became None  
  reply: Let us first finish your details. Is your produce ready for sale now?  
  diagnosis: The phrase 'ready to go' was misinterpreted as 'ready' (None) because the assistant's yes/no list didn't include 'ready to go' as a yes phrase. The farmer meant 'produce is ready to sell now' (yes), but the assistant's tool expected a yes/n
- **ready_yes** `Dilli se aaya hai, ab koi bhi le sakte hain, bhaiya!` → ready became None  
  reply: Sorry, I did not catch that. Is your produce ready for sale now?  
  diagnosis: The phrase 'ab koi bhi le sakte hain' was misinterpreted as a negative response due to missing 'yes' context in the yes/no list, causing 'ready' to become None instead of 'now'. The assistant's reply asked a yes/no question without checking
- **ready_yes** `Yeh onion khatam hai, ab bhi chhod do, bhaiya!` → ready became False  
  reply: I understood: onion 50 quintal (5,000 kg). Farm near Niphad. Not ready yet. You cannot store it. Is this correct?  
  diagnosis: The phrase 'ab bhi chhod do' was misinterpreted as 'not ready' instead of 'ready now' due to missing 'ab' in the yes/no list (ab = now). The assistant's response incorrectly assumed the produce was not ready when the farmer said 'chhod do'.
- **store_no** `50 quintal onion store karna mushkil hai, kya karo bhai?` → can_store became None  
  reply: Can you store the produce for a few days if it pays more? (yes or no)  
  diagnosis: The phrase 'store karna mushkil hai' was misinterpreted as 'can_store' being None instead of a yes/no question about storage difficulty. The root cause is that the voice assistant's response assumed a yes/no question when the farmer's input
- **pending_yes** `Haan, aaj hi karo, thoda wait kar do, bhaiya.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The phrase 'thoda wait kar do' was not recognized as a 'yes' because the assistant's yes/no list only includes short confirmations like 'haan', 'ji', etc., but 'thoda wait kar do' is a request to delay the action, not a confirmation of yes.
- **pending_yes** `Haan, aaj hi sale karo, thoda wait kar do, bhaiya.` → no order created (plan)  
  reply: Okay, I did not do it.  
  diagnosis: The phrase 'thoda wait kar do' was not recognized as a 'yes' because the assistant expected a simple yes/no confirmation after proposing the sale order, but the farmer added a request to wait slightly before proceeding, which the assistant误
- **sell_hold** `Do you think prices will go up if I hold them?` → ran ['llm:forecast']  
  reply: Forecast for APMC Pimpalgaon Baswant: in 1 days about ₹4,203 (₹4,074 to ₹4,507); in 3 days about ₹4,242 (₹4,035 to ₹4,913). Not a guarantee.  
  diagnosis: The phrase 'hold them' was misinterpreted as 'hold the crop' instead of 'sell now or hold' (rukun ya bechu). The assistant ran the forecast tool without confirming the farmer's intent to sell now or hold, leading to an incorrect response. A
- **sell_it** `Dekh lo, 50 quintal onion, aapko kya rate chahiye?` → no yes/no question (plan)  
  reply: I have no onion price for that place in today's data.  
  diagnosis: The farmer's question 'Dekh lo, ... kya rate chahiye?' is a request to create a sale order (bech do), not a yes/no question. The assistant expected a yes/no response but the farmer didn't provide one, so it assumed the farmer was asking for
- **storage** `अरे, तुम तो ठारा ठारा ठारा, कोणता ठेका आहे ना?` → ran ['llm:explain']  
  reply: अरे, तुम्ही ठारा ठारा ठारा, कोणता ठेका आहे ना? आज APMC Pimpalgaon Baswant, नाशिक, महाराष्ट्र येथे विका. नुकसान नको तर आजच विका.  
  diagnosis: The phrase 'कोणता ठेका' was misinterpreted as 'what is the deal' instead of 'what is the warehouse' due to the assistant's language model not recognizing the specific crop storage context in Marathi. The phrase 'ठेका' in Marathi means 'ware
- **storage** `कोणता ठेका आहे ना, तुम्हाला ठारा ठारा ठारा ठारा?` → ran ['llm:explain']  
  reply: कोणता ठेका आहे ना, तुम्हाला ठारा ठारा ठारा ठारा?  
  diagnosis: The phrase 'ठारा' is not in the yes/no word list, so the assistant didn't recognize it as a yes/no response. The farmer is asking about cold storage (godown) in Marathi, but the assistant's response is a literal repetition of the input, not
- **storage** `तुम्हाला कोणता ठेका आहे, ठारा ठारा ठारा?` → ran ['llm:explain']  
  reply: तुम्हाला कोणता ठेका आहे, ठारा ठारा ठारा?  
  diagnosis: The phrase 'ठारा ठारा ठारा' is a repetition of the word 'tharā' (meaning 'warehouse' in Marathi) without a clear context for the question, and the assistant's response is a direct repetition of the input without interpreting the farmer's 'k
