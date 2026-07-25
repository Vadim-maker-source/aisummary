"""Batch scenario discovery clustering (within a single category).

00_SHARED_CONTRACT.md section 8.2 + role file section 9:

- exact-duplicate queries are collapsed only for building the matrix, but
  membership is retained for every original event id;
- fewer than three unique queries in the category -> everything unclustered;
- vectorize with the mandated char-ngram TF-IDF (min_df=2) and cluster with
  AgglomerativeClustering(metric="cosine", linkage="average",
  distance_threshold=0.55);
- clusters with fewer than three unique queries do not become a scenario; their
  event ids go to ``unclustered``;
- for each surviving cluster pick up to 10 representative queries closest to the
  TF-IDF centroid (sorted by similarity desc, then query asc).

Determinism relies on the caller passing records already sorted by
``str(event_id)``.
"""

from __future__ import annotations

import re
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import embedding_client
from .schemas import Category, QueryProblemReason, ScenarioInputRecord

MIN_CLUSTER_SIZE = 3
DISTANCE_THRESHOLD = 0.55
SEMANTIC_DISTANCE_THRESHOLD = 0.425
MAX_REPRESENTATIVE_QUERIES = 10
MIN_DISCOVERY_CONFIDENCE = 0.65

_EXCLUDED_PROBLEMS = {
    QueryProblemReason.ambiguous,
    QueryProblemReason.multiple_intents,
    QueryProblemReason.unsupported_task,
    QueryProblemReason.unclassified,
}
_NAMED_SCENARIO_PREFIX_RE = re.compile(
    r"^нужно\s+выполнить\s+сценарий\s+«[^»]+»:\s*",
    re.IGNORECASE,
)
_GENERIC_PREFIX_RE = re.compile(
    r"^(?:пожалуйста,\s*|рабочая\s+задача:\s*|"
    r"помоги\s+сотруднику:\s*)",
    re.IGNORECASE,
)
_GENERIC_SUFFIX_RE = re.compile(
    r"\s+(?:укажи\s+результат\s+кратко|"
    r"перечисли\s+следующие\s+действия|"
    r"используй\s+только\s+доступные\s+корпоративные\s+данные|"
    r"не\s+придумывай\s+отсутствующие\s+сведения)\.?\s*$",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class ClusterResult:
    representative_queries: List[str] = field(default_factory=list)
    member_event_ids: List[str] = field(default_factory=list)
    category: Optional[Category] = None


def normalize_for_clustering(query: str) -> str:
    """Remove boilerplate that describes output style, not user intent."""

    text = _WHITESPACE_RE.sub(" ", query or "").strip().lower()
    text = text.replace("ё", "е")
    text = _NAMED_SCENARIO_PREFIX_RE.sub("", text)
    text = _GENERIC_PREFIX_RE.sub("", text)
    text = _GENERIC_SUFFIX_RE.sub("", text)
    return text.strip(" .")


def eligible_for_scenario_discovery(record: ScenarioInputRecord) -> bool:
    if record.category == Category.other:
        return False
    if (
        record.classification_confidence is not None
        and record.classification_confidence < MIN_DISCOVERY_CONFIDENCE
    ):
        return False
    return not bool(set(record.query_problem_reasons) & _EXCLUDED_PROBLEMS)


async def cluster_semantically(
    records: List[ScenarioInputRecord],
) -> Tuple[List[ClusterResult], List[str]]:
    """Cluster all eligible categories in one semantic embedding space.

    Cross-category discovery prevents an early classification mistake from
    permanently splitting one use case. A cluster receives the majority
    category of its members; deterministic lexical order resolves ties.
    Complete linkage prevents a cluster from growing through a chain of weak
    similarities.
    """

    if len(records) < MIN_CLUSTER_SIZE:
        return [], [record.event_id for record in records]

    normalized_queries = [
        normalize_for_clustering(record.effective_query)
        for record in records
    ]
    nonempty_indices = [
        index
        for index, query in enumerate(normalized_queries)
        if query
    ]
    unclustered = [
        records[index].event_id
        for index, query in enumerate(normalized_queries)
        if not query
    ]
    if len(nonempty_indices) < MIN_CLUSTER_SIZE:
        unclustered.extend(records[index].event_id for index in nonempty_indices)
        return [], unclustered

    vectors = await embedding_client.embed_texts(
        [normalized_queries[index] for index in nonempty_indices]
    )
    labels = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="complete",
        distance_threshold=SEMANTIC_DISTANCE_THRESHOLD,
    ).fit_predict(vectors)

    label_to_positions: "defaultdict[int, List[int]]" = defaultdict(list)
    for position, label in enumerate(labels):
        label_to_positions[int(label)].append(position)

    clusters: List[ClusterResult] = []
    ordered_labels = sorted(
        label_to_positions,
        key=lambda label: min(label_to_positions[label]),
    )
    for label in ordered_labels:
        positions = label_to_positions[label]
        record_indices = [nonempty_indices[position] for position in positions]
        # In semantic mode repeated requests are meaningful demand evidence,
        # so the minimum applies to events rather than unique wording.
        if len(record_indices) < MIN_CLUSTER_SIZE:
            unclustered.extend(records[index].event_id for index in record_indices)
            continue

        votes = Counter(records[index].category for index in record_indices)
        category = sorted(
            votes,
            key=lambda candidate: (-votes[candidate], candidate.value),
        )[0]
        representatives = _semantic_representatives(
            vectors[positions],
            [records[index].effective_query for index in record_indices],
        )
        clusters.append(
            ClusterResult(
                representative_queries=representatives,
                member_event_ids=[
                    records[index].event_id
                    for index in record_indices
                ],
                category=category,
            )
        )
    return clusters, unclustered


def _make_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=2,
        max_features=5000,
        sublinear_tf=True,
    )


def cluster_category(records: List[ScenarioInputRecord]) -> Tuple[List[ClusterResult], List[str]]:
    """Cluster one category's records. Returns (clusters, unclustered_event_ids)."""

    # Map each unique query -> ordered list of original event ids.
    query_to_events: "OrderedDict[str, List[str]]" = OrderedDict()
    for record in records:
        query_to_events.setdefault(record.effective_query, []).append(record.event_id)

    all_event_ids = [record.event_id for record in records]
    unique_queries = list(query_to_events.keys())

    # Fewer than three unique queries -> nothing clusters.
    if len(unique_queries) < MIN_CLUSTER_SIZE:
        return [], list(all_event_ids)

    try:
        matrix = _make_vectorizer().fit_transform(unique_queries)
        dense = matrix.toarray().astype(np.float64)
    except ValueError:
        # Empty vocabulary (e.g. everything dropped by min_df) -> unclustered.
        return [], list(all_event_ids)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=DISTANCE_THRESHOLD,
    )
    labels = clustering.fit_predict(dense)

    # Group unique-query indices by cluster label.
    label_to_indices: "defaultdict[int, List[int]]" = defaultdict(list)
    for idx, label in enumerate(labels):
        label_to_indices[int(label)].append(idx)

    clusters: List[ClusterResult] = []
    unclustered: List[str] = []

    # Deterministic cluster order: by the smallest unique-query index it holds.
    ordered_labels = sorted(label_to_indices, key=lambda lab: min(label_to_indices[lab]))
    for label in ordered_labels:
        indices = label_to_indices[label]
        cluster_queries = [unique_queries[i] for i in indices]

        if len(cluster_queries) < MIN_CLUSTER_SIZE:
            for query in cluster_queries:
                unclustered.extend(query_to_events[query])
            continue

        representative = _representative_queries(dense[indices], cluster_queries)

        member_ids: List[str] = []
        for query in cluster_queries:
            member_ids.extend(query_to_events[query])

        clusters.append(
            ClusterResult(
                representative_queries=representative,
                member_event_ids=member_ids,
            )
        )

    return clusters, unclustered


def _representative_queries(sub_matrix: np.ndarray, cluster_queries: List[str]) -> List[str]:
    centroid = sub_matrix.mean(axis=0, keepdims=True)
    sims = cosine_similarity(sub_matrix, centroid).ravel()
    # Sort by similarity desc, then query text asc for stable ties.
    order = sorted(range(len(cluster_queries)), key=lambda k: (-float(sims[k]), cluster_queries[k]))
    return [cluster_queries[k] for k in order[:MAX_REPRESENTATIVE_QUERIES]]


def _semantic_representatives(
    vectors: np.ndarray,
    queries: List[str],
) -> List[str]:
    centroid = vectors.mean(axis=0, keepdims=True)
    similarities = cosine_similarity(vectors, centroid).ravel()
    order = sorted(
        range(len(queries)),
        key=lambda index: (-float(similarities[index]), queries[index]),
    )
    representatives: List[str] = []
    seen: set[str] = set()
    for index in order:
        query = queries[index]
        normalized = normalize_for_clustering(query)
        if normalized in seen:
            continue
        seen.add(normalized)
        representatives.append(query)
        if len(representatives) == MAX_REPRESENTATIVE_QUERIES:
            break
    return representatives
