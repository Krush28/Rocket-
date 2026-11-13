"""Optional local LLM (Ollama). Off by default. Used ONLY to extract farmer slots and to phrase explanations.
All numbers come from deterministic code; the LLM never calculates money. Enable: KRISHIMITRA_LLM=ollama, OLLAMA_URL, OLLAMA_MODEL."""
import json
import os

import httpx


def enabled() -> bool:
    return os.getenv("KRISHIMITRA_LLM", "").lower() == "ollama"


def _gen(prompt: str, as_json=False) -> str | None:
    try:
        r = httpx.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate", timeout=30,
                       json={"model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"), "prompt": prompt, "stream": False, **({"format": "json"} if as_json else {})})
        return r.json().get("response")
    except Exception:
        return None


def extract_slots(text: str, known: dict) -> dict | None:
    raw = _gen('Extract farmer details from the text. Return JSON with optional keys: crop (onion|tomato|potato), variety, grade (A|B|C). '
               f"Text: {text!r}. Known: {list(known)}.", as_json=True)
    try:
        d = json.loads(raw or "{}")
        return {k: v for k, v in d.items() if k in ("variety", "grade") or (k == "crop" and v in ("onion", "tomato", "potato"))}
    except Exception:
        return None


def explain(facts: dict, lang: str) -> str | None:
    if not enabled():
        return None
    return _gen(f"Explain this selling recommendation to a farmer in {lang}, in 3 short sentences. Use ONLY these facts, do not invent numbers: {json.dumps(facts, default=str)}")
