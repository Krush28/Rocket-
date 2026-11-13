"""Conversation state persisted per session id, so a restart or second worker does not lose the farmer's answers."""
from sqlalchemy.orm import Session

from app.models import ConversationSession


def load(db: Session, sid: str) -> dict | None:
    row = db.get(ConversationSession, sid)
    return dict(row.state) if row else None


def save(db: Session, sid: str, state: dict, confirmed: bool) -> None:
    db.merge(ConversationSession(session_id=sid, state=state, confirmed=confirmed))
    db.commit()
