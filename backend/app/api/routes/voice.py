from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.speech import transcribe_audio

router = APIRouter(tags=["voice"])

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
        return transcribe_audio(audio, file.filename or "recording.webm")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
