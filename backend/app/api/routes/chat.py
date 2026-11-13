from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse, ConfirmRequest
from app.conversation.manager import conversation_manager

router = APIRouter(tags=["conversation"])

@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    return conversation_manager.reply(payload.session_id, payload.message)

@router.post("/profile/confirm", response_model=ChatResponse)
def confirm_profile(payload: ConfirmRequest):
    return conversation_manager.confirm(payload.session_id, payload.confirmed)

@router.get("/profile/{session_id}", response_model=ChatResponse)
def get_profile(session_id: str):
    state = conversation_manager._session(session_id)
    profile = state["profile"]
    missing = [field for field in ("crop", "quantity_kg", "location", "ready_when") if not profile.get(field)]
    return ChatResponse(session_id=session_id, reply="Profile loaded.", profile=profile, missing_fields=missing,
        ready_for_confirmation=not missing, confirmed=state["confirmed"])
