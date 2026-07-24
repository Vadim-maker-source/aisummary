from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list[AgentEvent]] = relationship(back_populates="import_job")
    analysis_run: Mapped[AnalysisRun | None] = relationship(
        back_populates="trigger_import",
        uselist=False,
    )


class AgentEvent(Base):
    __tablename__ = "agent_events"
    __table_args__ = (
        UniqueConstraint("agent_id", "external_id", name="uq_event_agent_external"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_latency"),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_rating",
        ),
        Index("ix_events_analysis_status", "analysis_status"),
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_import_id", "import_id"),
        Index("ix_events_team", "team"),
        Index("ix_events_direction", "direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imports.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_request: Mapped[dict[str, object]] = mapped_column(JSON_TYPE, nullable=False)
    raw_response: Mapped[dict[str, object] | None] = mapped_column(
        JSON_TYPE, nullable=True
    )
    agent_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown"
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    analysis_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    import_job: Mapped[ImportJob | None] = relationship(back_populates="events")
    analysis: Mapped[EventAnalysis | None] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scenario_memberships: Mapped[list[ScenarioMember]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class EventAnalysis(Base):
    __tablename__ = "event_analyses"
    __table_args__ = (
        Index("ix_analyses_category", "category"),
        Index("ix_analyses_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    effective_user_query: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False
    )
    query_problem_reasons: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    automation_potential: Mapped[str] = mapped_column(String(16), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    classifier_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    event: Mapped[AgentEvent] = relationship(back_populates="analysis")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_current", "is_current"),
        Index("ix_analysis_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trigger_import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("imports.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    algorithm_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="tfidf-agg-v1"
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    trigger_import: Mapped[ImportJob | None] = relationship(
        back_populates="analysis_run"
    )
    scenarios: Mapped[list[Scenario]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_run_category", "analysis_run_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    representative_queries: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    common_problems: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    automation_potential: Mapped[str] = mapped_column(String(16), nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="scenarios")
    members: Mapped[list[ScenarioMember]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class ScenarioMember(Base):
    __tablename__ = "scenario_members"
    __table_args__ = (
        Index("ix_scenario_members_event", "event_id"),
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_events.id", ondelete="CASCADE"), primary_key=True
    )
    similarity: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    scenario: Mapped[Scenario] = relationship(back_populates="members")
    event: Mapped[AgentEvent] = relationship(back_populates="scenario_memberships")

