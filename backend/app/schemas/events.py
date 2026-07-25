from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import (
    AnalysisStatus,
    AutomationPotential,
    Category,
    ExecutionStatus,
    QueryProblemReason,
)


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class UsagePayload(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class RequestPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(default=None, max_length=255)
    stream: bool = False
    messages: list[Message] = Field(min_length=1)


class ResponsePayload(BaseModel):
    content: str | None = None
    usage: UsagePayload | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_openai_response(cls, value):
        if not isinstance(value, dict) or "content" in value:
            return value
        choices = value.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    normalized = dict(value)
                    normalized["content"] = message.get("content")
                    return normalized
        return value


class EventCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    agent_id: str = Field(min_length=1, max_length=255)
    user_id: str | None = Field(default=None, max_length=255)
    team: str | None = Field(default=None, max_length=255)
    direction: str | None = Field(default=None, max_length=255)
    is_synthetic: bool = False
    occurred_at: datetime | None = None
    request: RequestPayload
    response: ResponsePayload | None = None
    execution_status: ExecutionStatus = ExecutionStatus.UNKNOWN
    latency_ms: int | None = Field(default=None, ge=0)
    rating: Decimal | None = Field(default=None, ge=1, le=5)
    task_completed: bool | None = None
    estimated_minutes_saved: int | None = Field(default=None, ge=0)

    @field_validator("external_id", "agent_id")
    @classmethod
    def strip_identifiers(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("user_id", "team", "direction")
    @classmethod
    def strip_optional_dimensions(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class EventAccepted(BaseModel):
    id: UUID
    accepted: bool = True
    duplicate: bool
    analysis_status: AnalysisStatus


class ScenarioReference(BaseModel):
    id: UUID
    name: str


class EventListItem(BaseModel):
    id: UUID
    external_id: str
    agent_id: str
    user_id: str | None
    team: str | None
    direction: str | None
    is_synthetic: bool
    occurred_at: datetime | None
    received_at: datetime
    effective_user_query: str | None
    category: Category | None
    scenario: ScenarioReference | None
    classification_confidence: float | None
    query_problem_reasons: list[QueryProblemReason] | None
    automation_potential: AutomationPotential | None
    analysis_status: AnalysisStatus


class EventListResponse(BaseModel):
    items: list[EventListItem]
    page: int
    page_size: int
    total: int


class EventDetail(EventListItem):
    model: str | None
    stream: bool
    execution_status: ExecutionStatus
    latency_ms: int | None
    rating: float | None
    task_completed: bool | None
    estimated_minutes_saved: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    warnings: list[str] | None


class EventRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    agent_id: str
    analysis_status: AnalysisStatus

