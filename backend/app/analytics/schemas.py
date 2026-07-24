"""Pydantic models for the analytics module.

Every model here mirrors the shapes and enums defined in
``00_SHARED_CONTRACT.md`` exactly. Backend imports the *result* models via
``analytics.public``; nothing else in the module is part of the public contract.

The code is written to run on both Python 3.9 (local CI sandbox) and the
contract target 3.12. We therefore rely on ``from __future__ import
annotations`` plus ``Optional``/``List`` from ``typing`` (never the ``X | Y``
union operator, which Pydantic could not resolve on 3.9).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums (00_SHARED_CONTRACT.md section 4)
# --------------------------------------------------------------------------- #
class Category(str, Enum):
    text_generation = "text_generation"
    information_search = "information_search"
    summarization = "summarization"
    data_analysis = "data_analysis"
    reporting_export = "reporting_export"
    task_management = "task_management"
    monitoring_automation = "monitoring_automation"
    calendar_planning = "calendar_planning"
    knowledge_explanation = "knowledge_explanation"
    other = "other"


class AutomationPotential(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class QueryProblemReason(str, Enum):
    # NOTE: declaration order == canonical enum order used when emitting a
    # deduplicated, ordered list of problem reasons.
    ambiguous = "ambiguous"
    missing_context = "missing_context"
    multiple_intents = "multiple_intents"
    oversized_context = "oversized_context"
    unsupported_task = "unsupported_task"
    low_classification_confidence = "low_classification_confidence"
    unclassified = "unclassified"


class AnalyticsWarning(str, Enum):
    query_truncated = "query_truncated"
    llm_unavailable = "llm_unavailable"
    llm_invalid_response = "llm_invalid_response"
    no_user_message = "no_user_message"
    no_matching_scenario = "no_matching_scenario"


class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


# --------------------------------------------------------------------------- #
# Input models
# --------------------------------------------------------------------------- #
class Message(BaseModel):
    role: Role
    content: str = ""


class AnalysisInput(BaseModel):
    """Input to :func:`analytics.public.analyze_event`."""

    event_id: str
    messages: List[Message] = Field(default_factory=list)
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None


class KnownScenario(BaseModel):
    """An already-discovered scenario, used for assignment of a new event."""

    id: str
    category: Category
    name: str
    representative_queries: List[str] = Field(default_factory=list)


class ScenarioInputRecord(BaseModel):
    """One record fed to :func:`analytics.public.discover_scenarios`."""

    event_id: str
    effective_query: str
    category: Category


# --------------------------------------------------------------------------- #
# Output models
# --------------------------------------------------------------------------- #
class EventAnalysisResult(BaseModel):
    effective_query: str
    category: Category
    classification_confidence: float
    scenario_id: Optional[str] = None
    scenario_confidence: Optional[float] = None
    query_problem_reasons: List[QueryProblemReason] = Field(default_factory=list)
    automation_potential: AutomationPotential
    warnings: List[AnalyticsWarning] = Field(default_factory=list)
    classifier_version: str = "v1"


class DiscoveredScenario(BaseModel):
    category: Category
    name: str
    summary: str
    representative_queries: List[str] = Field(default_factory=list)
    member_event_ids: List[str] = Field(default_factory=list)
    common_problems: List[str] = Field(default_factory=list)
    automation_potential: AutomationPotential
    suggested_action: str


class ScenarioDiscoveryResult(BaseModel):
    scenarios: List[DiscoveredScenario] = Field(default_factory=list)
    unclustered_event_ids: List[str] = Field(default_factory=list)
    algorithm_version: str = "tfidf-agg-v1"


# --------------------------------------------------------------------------- #
# Internal LLM-response models (not part of the public contract)
# --------------------------------------------------------------------------- #
class LLMClassification(BaseModel):
    """Schema the classifier LLM must return."""

    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    problem_reasons: List[QueryProblemReason] = Field(default_factory=list)
    automation_potential: AutomationPotential


class LLMScenarioSummary(BaseModel):
    """Schema the summarizer LLM must return."""

    name: str
    summary: str
    common_problems: List[str] = Field(default_factory=list)
    automation_potential: AutomationPotential
    suggested_action: str
