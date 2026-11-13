import os
import tempfile
from pathlib import Path

_model = None

def transcribe_audio(audio: bytes, filename: str):
    global _model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "Voice transcription is not installed. Run: pip install faster-whisper. "
            "The model is downloaded on first use."
        )

    if _model is None:
        model_name = os.getenv("WHISPER_MODEL", "small")
        _model = WhisperModel(model_name, device="cpu", compute_type="int8")

    suffix = Path(filename).suffix or ".webm"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio)
            temp_path = tmp.name
        segments, info = _model.transcribe(temp_path, vad_filter=True)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "transcript": transcript,
            "detected_language": info.language,
            "language_probability": round(float(info.language_probability), 3),
            "note": "Speech recognition result; please review before using it.",
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
