from datetime import date
from typing import Any, Literal

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


class DataRecord(DataInput):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class SummaryMetrics(StrictModel):
    total: float
    average: float
    max: float
    min: float


class BestDay(StrictModel):
    date: date
    value: float


class DataSummary(StrictModel):
    period: str | None
    count: int = Field(ge=0)
    unit: Literal["분"]
    metrics: SummaryMetrics | None
    best_day: BestDay | None = None
    trend: str
    change_percent: float | None
    trend_basis: str | None = None


class ConversationRecord(ConversationInput):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    updated_at: str


class ConversationListItem(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    title: str = Field(min_length=1, max_length=100)
    updated_at: str


class ChatResponse(StrictModel):
    reply: str
    conversation_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    messages: list[Message] = Field(min_length=2, max_length=50)
    usage: dict[str, Any] | None


class HealthResponse(StrictModel):
    status: Literal["ok"]
    storage: Literal["local", "firestore"]
    ai_mode: Literal["mock", "openai"]
    ai_configured: bool
