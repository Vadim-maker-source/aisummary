from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class EventCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    agent_id: str = Field(min_length=1, max_length=255)
    occurred_at: datetime | None = None
    request: RequestPayload
    response: ResponsePayload | None = None
    execution_status: ExecutionStatus = ExecutionStatus.UNKNOWN
    latency_ms: int | None = Field(default=None, ge=0)
    rating: Decimal | None = Field(default=None, ge=1, le=5)

    @field_validator("external_id", "agent_id")
    @classmethod
    def strip_identifiers(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


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
    prompt_tokens: int | None
    completion_tokens: int | None
    warnings: list[str] | None


class EventRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    agent_id: str
    analysis_status: AnalysisStatus

