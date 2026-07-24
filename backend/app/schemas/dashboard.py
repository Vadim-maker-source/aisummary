from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AutomationPotential, Category


class DashboardSummary(BaseModel):
    total_requests: int
    analyzed_requests: int
    pending_requests: int
    failed_requests: int
    category_count: int
    scenario_count: int
    unclassified_count: int
    query_problem_rate: float
    response_count: int
    rated_count: int
    timestamped_count: int
    dimensioned_count: int
    synthetic_requests: int


class CategoryItem(BaseModel):
    category: Category
    request_count: int
    percentage: float


class CategoryListResponse(BaseModel):
    items: list[CategoryItem]


class ScenarioListItem(BaseModel):
    id: UUID
    category: Category
    name: str
    summary: str
    request_count: int
    automation_potential: AutomationPotential
    common_problems: list[str]
    suggested_action: str


class ScenarioListResponse(BaseModel):
    items: list[ScenarioListItem]
    page: int
    page_size: int
    total: int


class ScenarioDetail(ScenarioListItem):
    representative_queries: list[str]


class TimelineItem(BaseModel):
    date: date
    request_count: int
    query_problem_count: int


class TimelineResponse(BaseModel):
    items: list[TimelineItem]


class ProblemItem(BaseModel):
    code: str
    label: str
    count: int
    percentage: float
    kind: Literal["query", "agent"]


class ProblemListResponse(BaseModel):
    items: list[ProblemItem]
    total_requests: int
    agent_quality_available: bool


class ScenarioTrendItem(BaseModel):
    id: UUID
    name: str
    category: Category
    current_count: int
    previous_count: int
    growth_percent: float | None
    trend: Literal["growing", "stable", "declining", "new"]


class ScenarioTrendResponse(BaseModel):
    available: bool
    window_days: int
    date_from: date | None
    date_to: date | None
    items: list[ScenarioTrendItem]


class EffectivenessItem(BaseModel):
    name: str
    total_requests: int
    analyzed_requests: int
    problem_rate: float
    success_rate: float | None
    answer_coverage: float
    average_rating: float | None
    average_latency_ms: float | None
    unique_users: int | None


class EffectivenessResponse(BaseModel):
    dimension: Literal["agent_id", "team", "direction"]
    available: bool
    coverage_percent: float
    items: list[EffectivenessItem]


class AnalysisRunAccepted(BaseModel):
    run_id: UUID
    status: str

