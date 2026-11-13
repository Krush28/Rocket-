"""Voice-agent bug hunter: an autonomous QA agent whose only job is to break the farmer voice agent and explain why it broke.

1. GENERATE  farmer utterances per intent x language (en / hi / mr / Hinglish): a hand-written core set plus fresh paraphrases from the
             local LLM each run (different wording, punctuation, mixed languages, filler words) - so it keeps finding new failures.
2. PLAY      each one through the real agent (action_agent.handle, real DB, real prices) starting from the right conversation stage:
             at the read-back, at a ready / storage question, at an order yes/no, or on the results screen.
3. JUDGE     against the expected outcome (state reached, tool run, order created or not) + invariants on every turn: no crash,
             reply in the farmer's script, no "I did not understand" for supported requests, no internal "demo" wording, < 4 s.
4. DIAGNOSE  every failure: the local LLM names the likely root cause (missing phrase, wrong route, ...) and the fix.
5. LEARN     (--learn) yes/no phrases the rules missed are added to app/qa/learned_phrases.json only when the LLM gives the same
             meaning twice with two different prompts and the phrase has no condition/negation in it; yes_no() loads that file.
Report: backend/qa_reports/BUGHUNT.md (+ .json). All test sessions use the "hunt-" prefix and are deleted afterwards.
Run:  docker compose exec backend python -m app.qa.bughunt [--paraphrases 4] [--learn] [--only confirm_yes,pending_yes]"""
import argparse
import json
import os
import re
import time
import uuid
from collections import defaultdict
from pathlib import Path

from sqlalchemy import delete

from app.agents import action_agent as A
from app.conversation import intake, profile_agent as P
from app.db.database import SessionLocal
from app.services import llm

OUT = Path(os.getenv("KRISHIX_QA_DIR", str(Path(__file__).resolve().parents[2] / "qa_reports")))  # backend/qa_reports
LEARNED = Path(__file__).with_name("learned_phrases.json")
DEVA = re.compile(r"[ऀ-ॿ]")

# intent: (stage, expectation, description for the LLM generator, hand-written seeds)
INTENTS = {
    "confirm_yes": ("readback", "plan", "the farmer confirms that the read-back of their crop, amount and village is correct and they are ready",
                    ["Yes, everything is correct.", "yes we are ready to sell", "haan ji sab sahi hai", "Yes. Go ahead.", "haan bilkul, maal taiyar hai",
                     "हाँ, सब सही है", "हो, सगळं बरोबर आहे", "correct hai bhai, aage badho", "that's right", "ji haan"]),
    "confirm_fix": ("readback", "collecting", "the farmer says the read-back is wrong and corrects the amount",
                    ["no, it is 60 quintal", "nahi, 60 quintal hai", "नहीं, 60 क्विंटल है", "नाही, 60 क्विंटल आहे", "wrong, make it 60 quintal"]),
    "ready_yes": ("ready", "ready=True", "the farmer says the produce is ready to sell now",
                  ["yes it is ready", "haan taiyar hai", "हाँ, माल तैयार है", "हो, तयार आहे", "yes, harvested and ready"]),
    "store_no": ("can_store", "can_store=False", "the farmer says they cannot store the produce",
                 ["no, I can't store it", "nahi, rakhne ki jagah nahi hai", "नहीं, भंडारण नहीं कर सकता", "नाही, साठवण नाही", "no storage at my place"]),
    "pending_yes": ("pending", "order", "the farmer agrees to create the sale order the assistant just proposed",
                    ["Yes, go ahead and sell it.", "haan bhai kar do", "हाँ, बना दो", "हो, करा", "ok do it", "sure, book it", "go for it"]),
    "pending_no": ("pending", "no_order", "the farmer declines creating the sale order for now",
                   ["no, not today", "nahi abhi mat karo", "नहीं, अभी नहीं", "नको, आत्ता नाही", "wait, don't do it yet"]),
    "pending_hedge": ("pending", "reask", "the farmer says yes but first asks how much money they will get",
                      ["yes but first tell me how much I will get", "haan par pehle batao kitna milega", "हाँ, पर पहले बताओ कितना मिलेगा?"]),
    "best_mandi": ("plan", "tool:compare|llm:best_mandi", "the farmer asks where they should sell or which mandi is best",
                   ["where should I sell?", "kahan bechu?", "कहाँ बेचूँ?", "कुठे विकू?", "which mandi gives me the most money"]),
    "sell_hold": ("plan", "tool:explain_decision|llm:sell_or_hold|explain|llm:explain", "the farmer asks whether to sell now or hold the crop",
                  ["should I sell now or wait?", "abhi bechu ya rukun?", "रुकूँ या बेचूँ?", "थांबू का विकू?"]),
    "forecast": ("plan", "tool:forecast|llm:forecast", "the farmer asks what the price will be next week",
                 ["what will the price be next week?", "agle hafte bhav kya rahega?", "भाव का अनुमान बताओ", "पुढच्या आठवड्यात भाव काय असेल?"]),
    "add_crop": ("plan", "tool:set_lot|llm:add_crop|add_crop", "the farmer says they also have another crop with an amount",
                 ["I also have 20 quintal potato", "mere paas 20 quintal aloo bhi hai", "माझ्याकडे 20 क्विंटल बटाटा पण आहे"]),
    "sell_it": ("plan", "confirm", "the farmer asks to sell the crop / create the order",
                ["sell it", "bech do", "बेच दो", "विकून टाका", "book the sale"]),
    "schemes": ("plan", "tool:schemes|llm:show_schemes", "the farmer asks to see government schemes",
                ["show government schemes", "sarkari yojana dikhao", "सरकारी योजना दिखाओ", "सरकारी योजना दाखवा"]),
    "storage": ("plan", "tool:logistics|llm:storage", "the farmer asks about cold storage or warehouses near them",
                ["is there cold storage near me?", "godam kahan milega?", "पास में गोदाम है क्या?", "जवळ शीतगृह आहे का?"]),
}
LANG_HINT = {"en": "English", "hi": "Hindi in Devanagari", "mr": "Marathi in Devanagari", "hinglish": "Hinglish (Hindi in Latin letters)"}
SETUP = ["", "onion", "50 quintal", "Niphad", "yes", "no"]  # -> read-back


def _lang_of(text: str) -> str:
    return P.detect_lang(text, "en") if DEVA.search(text) else "en"


def _generate(intent: str, desc: str, n: int) -> list[str]:
    if not llm.enabled() or n <= 0:
        return []
    out = []
    for lang, hint in LANG_HINT.items():
        raw = llm._gen(f"Write {n} different short things an Indian farmer might SAY to a voice assistant, in {hint}, where {desc}. "
                       "Vary wording, politeness, filler words and punctuation like real speech-to-text. Return JSON {\"lines\": [...]}.",
                       schema={"type": "object", "required": ["lines"], "properties": {"lines": {"type": "array", "maxItems": n, "items": {"type": "string", "maxLength": 120}}}},
                       max_tokens=60 * n, timeout=30)
        try:
            out += [x.strip() for x in json.loads(raw or "{}").get("lines", []) if isinstance(x, str) and 1 < len(x.strip()) <= 120]
        except ValueError:
            pass
    return out


def _stage(db, sid: str, stage: str):
    for t in SETUP:
        r = A.handle(sid, t, "en", db)
    if stage == "readback":
        return r
    if stage in ("ready", "can_store"):
        s = intake.pending(sid, db)
        s["awaiting"], s[stage] = stage, None
        intake.S[sid] = s
        return r
    r = A.handle(sid, "yes", "en", db)  # confirm -> plan
    if stage == "pending":
        r = A.handle(sid, "sell it", "en", db)
    return r


def _judge(expect: str, r: dict, sid: str, db) -> str | None:
    """None if the expectation holds, else what went wrong."""
    trace_tools = {t.get("tool") for t in r.get("trace", [])}
    if expect == "plan":
        return None if r["state"] == "plan" else f"stayed in {r['state']} ({r.get('awaiting')})"
    if expect == "collecting":
        return None if r["state"] == "collecting" else f"went to {r['state']} instead of re-reading the corrected details"
    if expect.startswith(("ready=", "can_store=")):
        k, v = expect.split("=")
        s = intake.pending(sid, db) or {}
        return None if str(s.get(k)) == v else f"{k} became {s.get(k)}"
    if expect == "order":
        return None if any(a["type"] == "order" for a in r.get("actions", [])) else f"no order created ({r['state']})"
    if expect == "no_order":
        return None if not any(a["type"] == "order" for a in r.get("actions", [])) else "created an order on a refusal"
    if expect == "reask":
        if any(a["type"] == "order" for a in r.get("actions", [])):
            return "created the order although the farmer asked something first"
        return None if r["state"] == "confirming_action" else "did not ask the yes/no question again"
    if expect == "confirm":
        return None if r["state"] == "confirming_action" else f"no yes/no question ({r['state']})"
    if expect.startswith("tool:"):
        ok = set(expect[5:].split("|"))
        return None if trace_tools & ok else f"ran {sorted(t for t in trace_tools if t) or 'nothing'}"
    return f"unknown expectation {expect}"


def _invariants(text: str, r: dict, ms: float) -> list[str]:
    bad = []
    reply = r.get("reply") or ""
    if not reply.strip():
        bad.append("empty reply")
    if ms > 4000:
        bad.append(f"slow ({ms / 1000:.1f} s)")
    if re.search(r"\bdemo\b|डेमो", reply, re.I):
        bad.append("internal 'demo' wording shown")
    if DEVA.search(text) and not DEVA.search(reply) and r.get("state") != "confirming_action":
        bad.append("Devanagari question, English answer")
    if "did not understand" in reply or "समझा नहीं" in reply or "समजले नाही" in reply:
        bad.append("said it did not understand")
    return bad


def _diagnose(text: str, intent: str, problem: str, reply: str) -> str:
    if not llm.enabled():
        return ""
    raw = llm._gen(f"A farmer voice assistant failed. Farmer said: {json.dumps(text, ensure_ascii=False)} (intended: {INTENTS[intent][2]}). "
                   f"Problem: {problem}. Assistant replied: {json.dumps(reply[:200], ensure_ascii=False)}. In one short sentence: the most likely root "
                   "cause (e.g. a phrase missing from the yes/no word list, the router not recognising a phrase, wrong language) and the fix.",
                   schema={"type": "object", "required": ["cause"], "properties": {"cause": {"type": "string", "maxLength": 240}}}, max_tokens=90, timeout=20)
    try:
        return json.loads(raw or "{}").get("cause", "")
    except ValueError:
        return ""


def _learn(text: str, intent: str) -> str | None:
    """Self-repair for yes/no: add the phrase if the LLM agrees twice and the phrase carries no condition or negation."""
    want = True if intent in ("confirm_yes", "pending_yes", "ready_yes") else False if intent in ("pending_no", "store_no") else None
    if want is None or P.hedged(text):
        return None
    phrase = " ".join(P._norm(text).split())
    if not phrase or len(phrase.split()) > 6 or (want and re.search(r"\b(no|not|nahi|nako)\b|नहीं|नाही|नको", phrase)):
        return None
    a = llm.yes_no("Shall I go ahead?", text)
    b = llm.yes_no("Is everything correct and should I continue?", text)
    if a is want and b is want:
        data = json.loads(LEARNED.read_text(encoding="utf-8")) if LEARNED.exists() else {"yes": [], "no": []}
        key = "yes" if want else "no"
        if phrase not in data[key]:
            data[key].append(phrase)
            LEARNED.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            P.reload_learned()
            return f"learned {key}: '{phrase}'"
    return None


def _cleanup(db, sids: list[str]):
    from app.models import ConversationSession, FarmerInventory, FarmerProfile, Notification, SaleOrder, StorageBooking, TransportJob
    orders = [o.id for o in db.query(SaleOrder).filter(SaleOrder.device.in_(sids))]
    if orders:
        db.execute(delete(TransportJob).where(TransportJob.order_id.in_(orders)))
        db.execute(delete(SaleOrder).where(SaleOrder.id.in_(orders)))
    db.execute(delete(StorageBooking).where(StorageBooking.device.in_(sids)))
    db.execute(delete(Notification).where(Notification.audience.in_([f"device:{s}" for s in sids])))
    profs = [p.id for p in db.query(FarmerProfile).filter(FarmerProfile.session_id.in_(sids))]
    if profs:
        db.execute(delete(FarmerInventory).where(FarmerInventory.farmer_profile_id.in_(profs)))
        db.execute(delete(FarmerProfile).where(FarmerProfile.id.in_(profs)))
    db.execute(delete(ConversationSession).where(ConversationSession.session_id.in_([f"intake:{s}" for s in sids] + sids)))
    db.commit()
    for s in sids:
        A.STATE.pop(s, None)
        intake.S.pop(s, None)


def hunt(paraphrases: int = 3, learn: bool = False, only: list[str] | None = None) -> dict:
    results, sids, learned = [], [], []
    t0 = time.time()
    with SessionLocal() as db:
        for intent, (stage, expect, desc, seeds) in INTENTS.items():
            if only and intent not in only:
                continue
            lines = list(dict.fromkeys(seeds + _generate(intent, desc, paraphrases)))
            for text in lines:
                sid = "hunt-" + uuid.uuid4().hex[:8]
                sids.append(sid)
                try:
                    _stage(db, sid, stage)
                    t = time.time()
                    r = A.handle(sid, text, None, db)
                    ms = (time.time() - t) * 1000
                    problem = _judge(expect, r, sid, db)
                    inv = _invariants(text, r, ms)
                except Exception as e:  # a crash is the worst bug
                    db.rollback()
                    r, ms, problem, inv = {"reply": "", "state": "crash"}, 0, f"CRASH {type(e).__name__}: {e}", []
                fail = [p for p in [problem] + inv if p]
                row = {"intent": intent, "lang": _lang_of(text), "text": text, "ok": not fail, "problems": fail,
                       "reply": (r.get("reply") or "")[:220], "state": r.get("state"), "ms": round(ms)}
                if fail:
                    row["diagnosis"] = _diagnose(text, intent, "; ".join(fail), row["reply"])
                    if learn and problem and intent in ("confirm_yes", "pending_yes", "ready_yes", "pending_no", "store_no"):
                        fix = _learn(text, intent)
                        if fix:
                            learned.append(fix)
                            row["self_fix"] = fix
                results.append(row)
        _cleanup(db, sids)
    by = defaultdict(lambda: [0, 0])
    for r in results:
        by[(r["intent"], r["lang"])][0] += r["ok"]
        by[(r["intent"], r["lang"])][1] += 1
    passed = sum(r["ok"] for r in results)
    report = {"run_at": time.strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0), "total": len(results), "passed": passed,
              "pass_rate": round(100 * passed / max(1, len(results)), 1), "llm": llm.enabled(), "learned": learned,
              "by_intent_lang": {f"{k[0]}|{k[1]}": v for k, v in sorted(by.items())}, "failures": [r for r in results if not r["ok"]],
              "slowest_ms": max((r["ms"] for r in results), default=0)}
    _write(report)
    return report


def _write(rep: dict):
    out = OUT
    out.mkdir(parents=True, exist_ok=True)
    (out / "BUGHUNT.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Voice agent bug hunt — {rep['run_at']}", "",
             f"**{rep['passed']} / {rep['total']} passed ({rep['pass_rate']}%)** in {rep['seconds']} s · local LLM paraphrases: {rep['llm']} · slowest turn {rep['slowest_ms']} ms", "",
             "| intent | language | passed |", "|---|---|---|"]
    lines += [f"| {k.split('|')[0]} | {k.split('|')[1]} | {v[0]}/{v[1]} |" for k, v in rep["by_intent_lang"].items()]
    if rep["learned"]:
        lines += ["", "## Self-repairs (learned phrases)", *[f"- {x}" for x in rep["learned"]]]
    lines += ["", "## Failures", ""] + ([f"- **{f['intent']}** `{f['text']}` → {'; '.join(f['problems'])}  \n  reply: {f['reply']}  \n  diagnosis: {f.get('diagnosis', '')}"
                                        for f in rep["failures"]] or ["None."])
    (out / "BUGHUNT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paraphrases", type=int, default=3)
    ap.add_argument("--learn", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    rep = hunt(a.paraphrases, a.learn, [x for x in a.only.split(",") if x] or None)
    print(f"{rep['passed']}/{rep['total']} passed ({rep['pass_rate']}%), {len(rep['failures'])} failures, learned {len(rep['learned'])}, {rep['seconds']} s")
    for f in rep["failures"][:40]:
        print(f" - [{f['intent']}/{f['lang']}] {f['text']!r}: {'; '.join(f['problems'])} | {f['reply'][:90]}")
