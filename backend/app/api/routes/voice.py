from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.schemas.chat import Lang
from app.services import tts
from app.services.speech import transcribe_audio

router = APIRouter(tags=["voice"])


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    lang: Lang = "en"


@router.post("/voice/speak")
async def speak(b: SpeakIn):
    """Offline Piper voice (WAV) for devices without a Hindi/Marathi/English voice of their own."""
    try:
        wav = await run_in_threadpool(tts.synthesize, b.text, b.lang)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})

@router.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.content_type or not (
        file.content_type.startswith("audio/") or file.content_type in
        {"application/octet-stream", "video/webm"}
    ):
        raise HTTPException(status_code=415, detail="Please upload an audio recording.")
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="The audio recording is empty.")
    if len(audio) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be 15 MB or smaller.")
    try:
        return await run_in_threadpool(transcribe_audio, audio, file.filename or "recording.webm")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
