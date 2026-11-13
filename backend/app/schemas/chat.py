from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["en", "hi", "mr"]


class ChatIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_\-]+$")
    text: str = Field(default="", max_length=2000)
    lang: Lang | None = None


class PlanIn(BaseModel):
    session_id: str = Field(max_length=100)
    assumptions: dict | None = None


class OrderIn(BaseModel):
    option: dict
    profile: dict


class EventIn(BaseModel):
    event: str = Field(max_length=40)
    data: dict | None = None


class ImportIn(BaseModel):
    path: str = Field(max_length=300)
