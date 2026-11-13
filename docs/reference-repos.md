# Reference repositories (studied for ideas only, no code copied)

| Repo | Used as inspiration for | Licence |
|---|---|---|
| https://github.com/Abhilash-S27/AgroPrice-AI | price forecasting, decision services | none declared |
| https://github.com/rohanesor/Mandi-Agent | agent orchestration (FastAPI + LangGraph), data sources | none declared |
| https://github.com/TechOrbiters/KrishiSetu | supply-chain workflow, buyer matching, transport | none declared |
| https://github.com/srushtin24/AgroAssist-Trilingual-Voice-Chatbot | multilingual voice chatbot | none declared |
| https://github.com/SaswatBalyan/AgroSense-KrishiSutra | voice-first farmer UI | MIT |

Repos with no licence are all-rights-reserved by default, so they are not vendored here. Clone them separately if you want to read them.

## What was actually taken from them (rewritten in our own code, not copied)

| Idea | From | Where in KrishiMitra |
|---|---|---|
| Transit spoilage risk = transit hours / shelf life x temperature multiplier, with SAFE / MODERATE / HIGH / CRITICAL tiers | Mandi-Agent `spoilage_risk.py` | `krishimitra/backend/app/spoilage.py`; shown on each option and used as a ranking penalty |
| Explainable confidence built from named contributors and detractors | AgroPrice-AI `confidence_engine.py` | `krishimitra/backend/app/confidence.py`; "How sure are we?" box |
| Decision with a primary reason and secondary factors | Mandi-Agent `decision_engine.py` | `decision.factors` in `sell_vs_hold`; "why" list under the verdict |
| Data-error guard (new, prompted by their anomaly handling) | AgroPrice-AI anomaly signals | `adapters.crop_median` + `demo_data.price_outlier`; excludes prices far from today's national median |

Looked at and not used: KrishiSetu's transport and sell routes are hardcoded stubs; AgroSense is a Flutter app (MIT) that does not port to our web UI; Mandi-Agent's oversupply detector needs farmer-intent data we do not have.
Future idea: Sarvam AI (used by KrishiSetu) offers Indic speech-to-text and text-to-speech, which could replace the browser speech API.
