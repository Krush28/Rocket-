"""Local LLM brain (Ollama qwen3:4b on the GPU). Off unless KRISHIMITRA_LLM=ollama.
It understands free speech and decides WHAT to do: plans tool calls (`plan_tools`), extracts intake facts (`extract_intake`) and answers
questions from given facts (`grounded_answer`). Python executes every tool and does all money maths; any number the model writes that
the tools did not produce is rejected. Speed: /api/generate + JSON schema (no thinking), model kept loaded; failure -> rules."""
import json
import os
import re

import httpx

TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_S", "6"))


def enabled() -> bool:
    return os.getenv("KRISHIMITRA_LLM", "").lower() == "ollama"


def _gen(prompt: str, as_json=False, max_tokens: int = 60, schema: dict | None = None, timeout: float | None = None) -> str | None:
    try:
        r = httpx.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate", timeout=timeout or TIMEOUT,
                       json={"model": os.getenv("OLLAMA_MODEL", "qwen3:4b"), "prompt": prompt, "stream": False, "think": False, "keep_alive": "24h",
                             "options": {"temperature": 0, "num_predict": max_tokens},
                             **({"format": schema} if schema else {"format": "json"} if as_json else {})})
        return r.json().get("response")
    except Exception:
        return None


def extract_slots(text: str, known: dict) -> dict | None:
    if not enabled():
        return None
    raw = _gen('Extract farmer details from the text. Return JSON with optional keys: variety, grade (A|B|C). '
               f"Text: {text!r}. Known: {list(known)}.", as_json=True)
    try:
        d = json.loads(raw or "{}")
        return {k: v for k, v in d.items() if k in ("variety", "grade") and isinstance(v, str)}
    except Exception:
        return None


def explain(facts: dict, lang: str) -> str | None:
    """Opt-in (KRISHIX_LLM_EXPLAIN=1): generating prose costs seconds per plan, so the instant template is the default."""
    if not enabled() or os.getenv("KRISHIX_LLM_EXPLAIN") != "1":
        return None
    return _gen(f"Explain this selling recommendation to a farmer in {lang}, in 3 short sentences. Use ONLY these facts, do not invent numbers: "
                f"{json.dumps(facts, default=str)}", max_tokens=160)


def warm() -> None:
    """Load the model onto the GPU in the background at startup: a cold load takes about a minute, a warm call about 0.5 s."""
    if not enabled():
        return
    import threading

    def go():
        try:
            httpx.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate", timeout=180,
                       json={"model": os.getenv("OLLAMA_MODEL", "qwen3:4b"), "prompt": "ok", "stream": False, "think": False,
                             "keep_alive": "24h", "options": {"num_predict": 1}})
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


def pick_tool(text: str, tools: list[str], ctx: dict) -> dict | None:
    """Legacy single-tool pick (kept for callers that only need a name)."""
    calls = plan_tools(text, ctx)
    return {"tool": calls[0]["tool"]} if calls else None


# ---------------------------------------------------------------- agentic planner
PLAN_TOOLS = {
    "best_mandi": "where to sell / best mandi / compare mandis / how much money will I get",
    "price_at": "MANDI wholesale rate or bhav of a crop, optionally at a town or mandi (args crop, place)",
    "forecast": "future price / price trend / will the price go up",
    "sell_or_hold": "should I sell now or wait / hold / store",
    "storage": "warehouses or cold storage near me",
    "transport": "truck / transport cost or options",
    "add_crop": "farmer has another crop or lot (args crop, qty, unit)",
    "remove_crop": "remove a crop (args crop)",
    "change_quantity": "the amount of the current crop changed (args qty, unit)",
    "change_place": "farm location changed (args place)",
    "set_cost": "change a cost assumption (args name: commission|hamali|risk|road_factor, value)",
    "create_order": "make the sale order / sell it now",
    "book_transport": "send the order to a transporter / book a truck for the order",
    "book_storage": "book a warehouse / cold storage for my crop",
    "track_order": "order status / where is my order",
    "retail_price": "ONLY shop / retail / consumer price in a city (args crop, city)",
    "show_schemes": "government schemes / yojana / subsidy information (args state)",
    "switch_language": "speak another language (args lang: en|hi|mr)",
    "explain": "why / explain / any other question about the plan, prices or costs",
    "chat": "greeting, thanks, or something unrelated to selling crops",
}
PLAN_SCHEMA = {"type": "object", "required": ["calls"], "properties": {"calls": {"type": "array", "maxItems": 3, "items": {
    "type": "object", "required": ["tool", "args"], "properties": {
        "tool": {"type": "string", "enum": list(PLAN_TOOLS)},
        "args": {"type": "object", "properties": {
            "crop": {"type": "string"}, "qty": {"type": "number"}, "unit": {"type": "string", "enum": ["kg", "quintal", "tonne"]},
            "place": {"type": "string"}, "city": {"type": "string"}, "state": {"type": "string"},
            "name": {"type": "string"}, "value": {"type": "number"}, "lang": {"type": "string", "enum": ["en", "hi", "mr"]}}}}}}}}


def plan_tools(text: str, ctx: dict) -> list[dict] | None:
    """Free-form request -> up to 3 tool calls (names + raw args) in order. Python validates and executes them."""
    if not enabled():
        return None
    tools = "\n".join(f"- {k}: {v}" for k, v in PLAN_TOOLS.items())
    raw = _gen("You route a farmer's request (English, Hindi, Marathi or Hinglish) to tools, in the order to run them. "
               f"Tools:\n{tools}\nContext: {json.dumps(ctx, ensure_ascii=False)}. Use crop keys from crop_words when given. "
               f"Request: {json.dumps(text, ensure_ascii=False)}", schema=PLAN_SCHEMA, max_tokens=160, timeout=20)
    try:
        calls = json.loads(raw or "{}").get("calls")
    except (ValueError, AttributeError):
        return None
    if not isinstance(calls, list):
        return None
    return [{"tool": c["tool"], "args": c.get("args") if isinstance(c.get("args"), dict) else {}}
            for c in calls if isinstance(c, dict) and c.get("tool") in PLAN_TOOLS][:3]


INTAKE_SCHEMA = {"type": "object", "properties": {
    "crops": {"type": "array", "maxItems": 6, "items": {"type": "object", "required": ["crop"], "properties": {
        "crop": {"type": "string"}, "qty": {"type": "number"}, "unit": {"type": "string", "enum": ["kg", "quintal", "tonne"]}}}},
    "place": {"type": "string"}, "ready": {"type": "boolean"}, "can_store": {"type": "boolean"}}}


def extract_intake(text: str, asked: str | None) -> dict | None:
    """Free speech -> crops (with amounts), farm place, ready, can store. Only facts present in the text; missing keys stay missing."""
    if not enabled():
        return None
    raw = _gen("Extract what a farmer said (English/Hindi/Marathi/Hinglish). Crop names in English (e.g. brinjal, okra, wheat). "
               "Number words to digits (do = 2, teen = 3, paanch = 5). Include ONLY facts present in the text; omit anything not said. "
               f"The assistant had asked about: {asked or 'nothing'}. Text: {json.dumps(text, ensure_ascii=False)}",
               schema=INTAKE_SCHEMA, max_tokens=150, timeout=20)
    try:
        d = json.loads(raw or "{}")
        return d if isinstance(d, dict) else None
    except ValueError:
        return None


LANG_NAME = {"en": "English", "hi": "Hindi (Devanagari script)", "mr": "Marathi (Devanagari script)"}
_NUM = re.compile(r"\d+(?:\.\d+)?")


def grounded_answer(question: str, facts: str, lang: str) -> str | None:
    """Short answer using ONLY the given facts; None if it states any number the facts/question do not contain."""
    if not enabled():
        return None
    raw = _gen(f"You are KRISHI-X, a farmer's selling assistant. Write the answer in {LANG_NAME.get(lang, 'English')}, at most 3 short sentences, "
               "using ONLY these facts. If the facts do not answer it, say briefly what you can help with (best mandi, sell or hold, prices, "
               f"transport, storage, orders, government schemes). Never invent numbers.\nFacts: {facts}\nQuestion: {question}",
               schema={"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string", "maxLength": 400}}}, max_tokens=220, timeout=25)
    try:
        out = str(json.loads(raw or "{}").get("answer") or "").strip()
    except ValueError:
        return None
    allowed = set(_NUM.findall((facts + " " + question).replace(",", "")))
    if not out or any(n not in allowed for n in _NUM.findall(out.replace(",", ""))):
        return None
    return out
