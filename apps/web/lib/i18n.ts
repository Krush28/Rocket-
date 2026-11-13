export type Lang = "en" | "hi" | "mr";

const T = {
  title: { en: "What do you want to sell today?", hi: "आज आप क्या बेचना चाहते हैं?", mr: "आज तुम्हाला काय विकायचे आहे?" },
  sub: { en: "Say your crop, amount and village. I find where you keep the most after costs.", hi: "फसल, मात्रा और गाँव बताइए। मैं बताऊँगा कि खर्च के बाद सबसे ज़्यादा कहाँ बचेगा।", mr: "पीक, प्रमाण आणि गाव सांगा. खर्चानंतर सर्वाधिक कुठे राहील ते मी सांगतो." },
  tap: { en: "Tap and speak", hi: "दबाएँ और बोलें", mr: "दाबा आणि बोला" },
  listening: { en: "Listening… tap to stop", hi: "सुन रहा हूँ… रोकने के लिए दबाएँ", mr: "ऐकत आहे… थांबवण्यासाठी दाबा" },
  type: { en: "Or type here", hi: "या यहाँ लिखें", mr: "किंवा येथे लिहा" },
  send: { en: "Send", hi: "भेजें", mr: "पाठवा" },
  yes: { en: "Yes, correct", hi: "हाँ, सही है", mr: "होय, बरोबर" },
  change: { en: "Change something", hi: "कुछ बदलना है", mr: "काही बदलायचे आहे" },
  yesWord: { en: "yes", hi: "हाँ", mr: "होय" },
  noWord: { en: "no", hi: "नहीं", mr: "नाही" },
  crop: { en: "Crop", hi: "फसल", mr: "पीक" },
  qty: { en: "Amount", hi: "मात्रा", mr: "प्रमाण" },
  place: { en: "Place", hi: "जगह", mr: "ठिकाण" },
  ready: { en: "Ready now", hi: "अभी तैयार", mr: "आता तयार" },
  store: { en: "Can store", hi: "रख सकते हैं", mr: "साठवू शकता" },
  keep: { en: "You take home about", hi: "आपके हाथ में लगभग", mr: "तुमच्या हाती सुमारे" },
  slip: { en: "Settlement estimate", hi: "हिसाब का अनुमान", mr: "हिशोबाचा अंदाज" },
  gross: { en: "Gross sale", hi: "कुल बिक्री", mr: "एकूण विक्री" },
  net: { en: "You keep", hi: "आपको बचेगा", mr: "तुम्हाला राहील" },
  hold: { en: "Sell now or hold?", hi: "अभी बेचें या रुकें?", mr: "आता विकायचे की थांबायचे?" },
  where: { en: "Where to sell", hi: "कहाँ बेचें", mr: "कुठे विकायचे" },
  history: { en: "Price history", hi: "भाव का इतिहास", mr: "भावाचा इतिहास" },
  retail: { en: "Retail prices (consumer context)", hi: "खुदरा भाव (ग्राहक संदर्भ)", mr: "किरकोळ भाव (ग्राहक संदर्भ)" },
  storage: { en: "Cold storage nearby", hi: "पास के कोल्ड स्टोरेज", mr: "जवळची शीतगृहे" },
  transport: { en: "Transport", hi: "ढुलाई", mr: "वाहतूक" },
  order: { en: "Create sale order", hi: "बिक्री ऑर्डर बनाएँ", mr: "विक्री ऑर्डर तयार करा" },
  restart: { en: "New lot", hi: "नया माल", mr: "नवीन माल" },
  real: { en: "What is real", hi: "क्या असली है", mr: "काय खरे आहे" },
} as const;

export type Key = keyof typeof T;
export const t = (k: Key, l: Lang) => T[k][l];
export const rupees = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
