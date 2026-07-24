from datetime import date
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


class AnalysisRunAccepted(BaseModel):
    run_id: UUID
    status: str

