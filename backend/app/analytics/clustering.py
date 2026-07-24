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

from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schemas import ScenarioInputRecord

MIN_CLUSTER_SIZE = 3
DISTANCE_THRESHOLD = 0.55
MAX_REPRESENTATIVE_QUERIES = 10


@dataclass
class ClusterResult:
    representative_queries: List[str] = field(default_factory=list)
    member_event_ids: List[str] = field(default_factory=list)


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
            ClusterResult(representative_queries=representative, member_event_ids=member_ids)
        )

    return clusters, unclustered


def _representative_queries(sub_matrix: np.ndarray, cluster_queries: List[str]) -> List[str]:
    centroid = sub_matrix.mean(axis=0, keepdims=True)
    sims = cosine_similarity(sub_matrix, centroid).ravel()
    # Sort by similarity desc, then query text asc for stable ties.
    order = sorted(range(len(cluster_queries)), key=lambda k: (-float(sims[k]), cluster_queries[k]))
    return [cluster_queries[k] for k in order[:MAX_REPRESENTATIVE_QUERIES]]
