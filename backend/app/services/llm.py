"""Optional local LLM (Ollama, e.g. qwen3:4b on the GPU). Off unless KRISHIMITRA_LLM=ollama. It only picks a tool NAME for requests the
fast rules did not understand, fills slots the rules missed, and (opt-in) phrases explanations. It never calculates money.
Speed: short timeout, no "thinking", model kept loaded; any failure falls back to rules instantly."""
import json
import os

import httpx

TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_S", "6"))


def enabled() -> bool:
    return os.getenv("KRISHIMITRA_LLM", "").lower() == "ollama"


def _gen(prompt: str, as_json=False, max_tokens: int = 60) -> str | None:
    try:
        r = httpx.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate", timeout=TIMEOUT,
                       json={"model": os.getenv("OLLAMA_MODEL", "qwen3:4b"), "prompt": prompt, "stream": False, "think": False, "keep_alive": "30m",
                             "options": {"temperature": 0, "num_predict": max_tokens}, **({"format": "json"} if as_json else {})})
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


def pick_tool(text: str, tools: list[str], ctx: dict) -> dict | None:
    """Ask the local model to choose ONE tool name. Only the name is trusted: arguments are re-derived by deterministic rules."""
    if not enabled():
        return None
    raw = _gen(f"You control a farmer's selling assistant. The farmer may speak English, Hindi or Marathi. Choose exactly one tool for the request. "
               f"Tools: {tools}. Context: {ctx}. Request: {text!r}. Reply as JSON: {{\"tool\": \"<name or unknown>\"}}", as_json=True, max_tokens=20)
    try:
        d = json.loads(raw or "{}")
        return {"tool": d.get("tool")} if isinstance(d, dict) else None
    except Exception:
        return None
