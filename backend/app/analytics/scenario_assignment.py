"""Assign a single new event to an existing known scenario.

Algorithm (00_SHARED_CONTRACT.md section 8.3):

1. only scenarios of the *same* category are candidates;
2. build a TF-IDF space over ``[new_query] + all representative_queries`` of
   the candidate scenarios, using the shared char-ngram configuration but with
   ``min_df=1``;
3. cosine-similarity of the new query against every representative query;
4. each scenario's score is its maximum similarity;
5. assign the best scenario when its score >= 0.45;
6. otherwise return ``scenario_id=None`` and the ``no_matching_scenario`` warning.

Ties on the best score are broken by the lexicographically smallest scenario
UUID. When there are no candidate scenarios at all (cold start / different
category), assignment simply does not apply and no warning is emitted.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .schemas import AnalyticsWarning, Category, KnownScenario

ASSIGNMENT_THRESHOLD = 0.45


def _make_vectorizer() -> TfidfVectorizer:
    # Shared config; min_df=1 for the assignment step.
    return TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=5000,
        sublinear_tf=True,
    )


def assign_scenario(
    query: str,
    category: Category,
    known_scenarios: List[KnownScenario],
) -> Tuple[Optional[str], Optional[float], List[AnalyticsWarning]]:
    candidates = [s for s in known_scenarios if s.category == category]

    # Flatten representative queries, remembering which scenario each belongs to.
    rep_texts: List[str] = []
    rep_owner: List[str] = []
    for scenario in candidates:
        for rep in scenario.representative_queries:
            if rep and rep.strip():
                rep_texts.append(rep)
                rep_owner.append(scenario.id)

    # Nothing to match against -> assignment not applicable (no warning).
    if not query or not query.strip() or not rep_texts:
        return None, None, []

    try:
        matrix = _make_vectorizer().fit_transform([query] + rep_texts)
        sims = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    except ValueError:
        # Degenerate vocabulary etc. -> treat as no match.
        return None, None, [AnalyticsWarning.no_matching_scenario]

    best_by_scenario: dict = {}
    for owner_id, sim in zip(rep_owner, sims):
        score = float(sim)
        if owner_id not in best_by_scenario or score > best_by_scenario[owner_id]:
            best_by_scenario[owner_id] = score

    best_score = max(best_by_scenario.values())
    if best_score < ASSIGNMENT_THRESHOLD:
        return None, None, [AnalyticsWarning.no_matching_scenario]

    # Tie-break: lexicographically smallest UUID among the top scorers.
    top_ids = sorted(
        sid for sid, score in best_by_scenario.items() if abs(score - best_score) < 1e-9
    )
    return top_ids[0], round(best_score, 3), []
