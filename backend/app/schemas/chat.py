from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)

class ConfirmRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    confirmed: bool

class FarmerProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    preferred_language: Optional[str] = None
    crop: Optional[str] = None
    variety: Optional[str] = None
    quality_grade: Optional[str] = None
    quantity_kg: Optional[float] = Field(default=None, gt=0)
    quantity_original: Optional[str] = None
    location: Optional[str] = None
    ready_when: Optional[str] = None
    selling_preference: Optional[str] = None
    can_store: Optional[bool] = None

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    profile: dict[str, Any]
    missing_fields: list[str]
    ready_for_confirmation: bool
    confirmed: bool = False
    data_mode: str = "intake_only"
