import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import action_agent
from app.db.database import get_db
from app.schemas.chat import ChatIn

router = APIRouter(tags=["agent"])


@router.post("/agent")
def agent(b: ChatIn, db: Session = Depends(get_db)):
    """Voice action agent: multi-crop intake (confirm first), then free-form requests -> tools (views, plan edits, orders after yes/no).
    session_id is the browser's device id: it is how a returning farmer is remembered."""
    return action_agent.handle(b.session_id or uuid.uuid4().hex, b.text, b.lang, db)
