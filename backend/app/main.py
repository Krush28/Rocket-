from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes.chat import router as chat_router
from app.api.routes.voice import router as voice_router
from app.db.database import init_db

app = FastAPI(
    title="KRISHI-X API",
    description="Voice-first mandi price intelligence and farm-to-market platform",
    version="0.1.0",
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(voice_router, prefix="/api")

init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "krishi-x-api"}
