import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents import orchestrator
from app.conversation import profile_agent as P
from app.db.database import get_db
from app.repositories import sessions as SS
from app.schemas.chat import ChatIn, PlanIn

router = APIRouter(tags=["conversation"])


@router.post("/chat")
def chat(b: ChatIn, db: Session = Depends(get_db)):
    """Farmer Profile Agent turn. Market work (the plan) runs ONLY after the farmer confirms the read-back."""
    sid = b.session_id or uuid.uuid4().hex[:16]
    r = P.chat(sid, b.text, b.lang, db=db)
    r["session_id"] = sid
    if r["done"]:
        r["inventory_id"] = P.on_confirm(db, sid, r["profile"])
        r["plan"] = orchestrator.run(r["profile"])
    return r


@router.post("/plan")
def plan(b: PlanIn, db: Session = Depends(get_db)):
    """Re-run the market plan for a confirmed session (for example with edited cost assumptions)."""
    s = SS.load(db, b.session_id)
    if s is None:
        raise HTTPException(404, "unknown session")
    if s.get("state") != "confirmed" or not s.get("profile"):
        raise HTTPException(409, "profile not confirmed")
    return orchestrator.run(s["profile"], b.assumptions)
