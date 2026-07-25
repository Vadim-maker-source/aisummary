from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    AnalyticsWarning,
    AutomationPotential,
    Category,
    QueryProblemReason,
)


class EventAnalysisResultPayload(BaseModel):
    effective_query: str
    category: Category
    classification_confidence: float = Field(ge=0, le=1)
    scenario_id: UUID | None = None
    scenario_confidence: float | None = Field(default=None, ge=0, le=1)
    query_problem_reasons: list[QueryProblemReason]
    automation_potential: AutomationPotential
    warnings: list[AnalyticsWarning]
    classifier_version: str


class DiscoveredScenarioPayload(BaseModel):
    category: Category
    name: str = Field(min_length=1, max_length=255)
    summary: str
    representative_queries: list[str]
    member_event_ids: list[UUID]
    common_problems: list[str]
    automation_potential: AutomationPotential
    suggested_action: str


class ScenarioDiscoveryPayload(BaseModel):
    scenarios: list[DiscoveredScenarioPayload]
    unclustered_event_ids: list[UUID]
    algorithm_version: str

