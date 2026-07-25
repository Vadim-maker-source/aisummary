"""Public interface of the analytics module.

Backend imports **only** these two coroutines. Both are total: they never raise
because of the LLM or of degenerate input, and always return an exact-shape
Pydantic model.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Iterable, List, Optional

from . import classifier, clustering, extraction, problems, scenario_assignment, summarizer
from .categories import automation_for
from .schemas import (
    AnalysisInput,
    AnalyticsWarning,
    Category,
    DiscoveredScenario,
    EventAnalysisResult,
    KnownScenario,
    ScenarioDiscoveryResult,
    ScenarioInputRecord,
)

CLASSIFIER_VERSION = "v1"
TFIDF_ALGORITHM_VERSION = "tfidf-agg-v1"
SEMANTIC_ALGORITHM_VERSION = "qwen-embedding-agg-v2"


def _dedupe_warnings(warnings: Iterable[AnalyticsWarning]) -> List[AnalyticsWarning]:
    seen = set()
    ordered: List[AnalyticsWarning] = []
    for warning in warnings:
        if warning not in seen:
            seen.add(warning)
            ordered.append(warning)
    return ordered


async def analyze_event(
    data: AnalysisInput,
    known_scenarios: List[KnownScenario],
) -> EventAnalysisResult:
    known_scenarios = known_scenarios or []
    extracted = extraction.extract_effective_query(data)
    warnings: List[AnalyticsWarning] = list(extracted.warnings)

    # No user message: empty query, confidence 0, other (contract section 6.2).
    if not extracted.has_user_message:
        category = Category.other
        confidence = 0.0
        reasons = problems.build_problem_reasons(
            query="",
            category=category,
            confidence=confidence,
            extraction_problems=extracted.problems,
            llm_problems=[],
        )
        return EventAnalysisResult(
            effective_query="",
            category=category,
            classification_confidence=confidence,
            scenario_id=None,
            scenario_confidence=None,
            query_problem_reasons=reasons,
            automation_potential=automation_for(category),
            warnings=_dedupe_warnings(warnings),
            classifier_version=CLASSIFIER_VERSION,
        )

    outcome = await classifier.classify(extracted.classifier_text)
    warnings.extend(outcome.warnings)

    reasons = problems.build_problem_reasons(
        query=extracted.effective_query,
        category=outcome.category,
        confidence=outcome.confidence,
        extraction_problems=extracted.problems,
        llm_problems=outcome.llm_problem_reasons,
    )

    scenario_id, scenario_confidence, assign_warnings = scenario_assignment.assign_scenario(
        extracted.effective_query,
        outcome.category,
        known_scenarios,
    )
    warnings.extend(assign_warnings)

    return EventAnalysisResult(
        effective_query=extracted.effective_query,
        category=outcome.category,
        classification_confidence=round(float(outcome.confidence), 3),
        scenario_id=scenario_id,
        scenario_confidence=scenario_confidence,
        query_problem_reasons=reasons,
        automation_potential=outcome.automation_potential,
        warnings=_dedupe_warnings(warnings),
        classifier_version=CLASSIFIER_VERSION,
    )


async def discover_scenarios(
    records: List[ScenarioInputRecord],
) -> ScenarioDiscoveryResult:
    records = records or []

    # Fixed input order for reproducibility (role file section 9.2).
    ordered = sorted(records, key=lambda record: str(record.event_id))

    # Exclude requests that cannot form a reliable durable use case.
    eligible = [
        record
        for record in ordered
        if clustering.eligible_for_scenario_discovery(record)
    ]
    excluded_ids = [
        record.event_id
        for record in ordered
        if record.category != Category.other
        and record not in eligible
    ]

    semantic_clusters: Optional[List[clustering.ClusterResult]] = None
    semantic_unclustered: List[str] = []
    if clustering.embedding_client.is_configured() and eligible:
        try:
            semantic_clusters, semantic_unclustered = (
                await clustering.cluster_semantically(eligible)
            )
        except clustering.embedding_client.EmbeddingError:
            semantic_clusters = None

    if semantic_clusters is not None:
        semaphore = asyncio.Semaphore(4)

        async def build_semantic_scenario(
            cluster: clustering.ClusterResult,
        ) -> DiscoveredScenario:
            category = cluster.category or Category.other
            async with semaphore:
                meta = await summarizer.summarize_cluster(
                    category,
                    cluster.representative_queries,
                )
            return DiscoveredScenario(
                category=category,
                name=meta.name,
                summary=meta.summary,
                representative_queries=cluster.representative_queries,
                member_event_ids=cluster.member_event_ids,
                common_problems=meta.common_problems,
                automation_potential=meta.automation_potential,
                suggested_action=meta.suggested_action,
            )

        scenarios = list(
            await asyncio.gather(
                *(
                    build_semantic_scenario(cluster)
                    for cluster in semantic_clusters
                )
            )
        )
        return ScenarioDiscoveryResult(
            scenarios=scenarios,
            unclustered_event_ids=excluded_ids + semantic_unclustered,
            algorithm_version=SEMANTIC_ALGORITHM_VERSION,
        )

    # Offline fallback: group by category and use char-ngram TF-IDF.
    by_category: "OrderedDict[Category, List[ScenarioInputRecord]]" = OrderedDict()
    for record in eligible:
        by_category.setdefault(record.category, []).append(record)

    scenarios: List[DiscoveredScenario] = []
    unclustered: List[str] = list(excluded_ids)

    # Deterministic category processing order.
    for category in sorted(by_category, key=lambda c: c.value):
        clusters, category_unclustered = clustering.cluster_category(by_category[category])
        unclustered.extend(category_unclustered)

        for cluster in clusters:
            meta = await summarizer.summarize_cluster(category, cluster.representative_queries)
            scenarios.append(
                DiscoveredScenario(
                    category=category,
                    name=meta.name,
                    summary=meta.summary,
                    representative_queries=cluster.representative_queries,
                    member_event_ids=cluster.member_event_ids,
                    common_problems=meta.common_problems,
                    automation_potential=meta.automation_potential,
                    suggested_action=meta.suggested_action,
                )
            )

    return ScenarioDiscoveryResult(
        scenarios=scenarios,
        unclustered_event_ids=unclustered,
        algorithm_version=TFIDF_ALGORITHM_VERSION,
    )
