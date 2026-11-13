"""Offline text-to-speech with Piper (rhasspy/piper-voices). Used only when the farmer's device has no voice for the language
(common for Hindi/Marathi on Windows); the browser's own voice is tried first because it is instant.
Voices download once from Hugging Face into PIPER_DIR (a Docker volume) and stay loaded in memory for speed."""
import io
import os
import threading
import wave
from pathlib import Path

import httpx

VOICES = {"hi": "hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium", "mr": "mr/mr_IN/google/medium/mr_IN-google-medium",
          "en": "en/en_US/amy/medium/en_US-amy-medium"}
BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
DIR = Path(os.getenv("PIPER_DIR", "/models/piper"))
MAX_CHARS = 600  # keep spoken replies short and fast
_loaded: dict = {}
_lock = threading.Lock()


def _voice(lang: str):
    if lang in _loaded:
        return _loaded[lang]
    from piper import PiperVoice  # optional dependency: imported only when speech is actually requested
    with _lock:
        if lang not in _loaded:
            DIR.mkdir(parents=True, exist_ok=True)
            onnx = DIR / (Path(VOICES[lang]).name + ".onnx")
            for p, url in ((onnx, BASE + VOICES[lang] + ".onnx"), (onnx.with_suffix(".onnx.json"), BASE + VOICES[lang] + ".onnx.json")):
                if not p.exists():
                    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                        r.raise_for_status()
                        tmp = p.with_suffix(p.suffix + ".part")
                        with open(tmp, "wb") as f:
                            for chunk in r.iter_bytes():
                                f.write(chunk)
                        tmp.rename(p)
            _loaded[lang] = PiperVoice.load(str(onnx))
    return _loaded[lang]


def synthesize(text: str, lang: str) -> bytes:
    """WAV bytes for the text. Raises KeyError for an unsupported language, RuntimeError if Piper is unavailable."""
    if lang not in VOICES:
        raise KeyError(lang)
    try:
        v = _voice(lang)
    except ImportError as e:
        raise RuntimeError("Offline speech is not installed (pip install piper-tts).") from e
    buf = io.BytesIO()
    try:
        with wave.open(buf, "wb") as wf:
            if hasattr(v, "synthesize_wav"):  # piper-tts >= 1.3
                v.synthesize_wav(text[:MAX_CHARS], wf)
            else:
                v.synthesize(text[:MAX_CHARS], wf)
    except wave.Error as e:  # nothing speakable (e.g. only symbols, or text in another script)
        raise ValueError("nothing to speak in this text") from e
    return buf.getvalue()


def warm(langs=("hi", "mr", "en")) -> None:
    """Download and load voices in the background at startup so the first spoken reply is not slow."""
    def go():
        for lang in langs:
            try:
                _voice(lang)
            except Exception:
                pass
    threading.Thread(target=go, daemon=True).start()
