from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DataInput(StrictModel):
    date: date
    value: float = Field(ge=0, le=1440, allow_inf_nan=False)
    memo: str = Field(default="", max_length=300)


class Message(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class ConversationInput(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    messages: list[Message] = Field(min_length=1, max_length=50)


class ChatInput(StrictModel):
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,128}$"
    )

