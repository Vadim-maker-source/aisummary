"""Effective-query extraction.

Implements the algorithm from 00_SHARED_CONTRACT.md section 6 literally:

1. find the last ``role=user`` message;
2. if there is none -> empty query + ``no_user_message`` warning;
3. if the content contains ``<user_query>...</user_query>`` take the content of
   the *last* such pair (case-insensitive, dot-matches-newline);
4. otherwise take the whole content of the last user message;
5. strip surrounding whitespace;
6. collapse runs of whitespace to a single space;
7. store the full extracted text as ``effective_user_query``;
8. build ``classifier_text``: whole text if <= 8000 chars, otherwise the first
   4000 + last 4000 chars plus a ``query_truncated`` warning;
9. accept context up to and including 100k prompt tokens. If provider usage is
   unavailable, use a conservative 400k-character guard. Only inputs strictly
   above that supported boundary get the ``oversized_context`` problem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from app.core.context_limits import context_exceeds_supported_limit

from .schemas import AnalysisInput, AnalyticsWarning, QueryProblemReason, Role

# <user_query> ... </user_query>: case-insensitive, dot matches newline,
# non-greedy so multiple pairs are captured independently (we keep the last).
_USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.IGNORECASE | re.DOTALL)
_CONTEXT_RE = re.compile(r"<context\b[^>]*>.*?</context>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")

CLASSIFIER_MAX_CHARS = 8000
TRUNCATE_HALF = 4000


@dataclass
class ExtractionResult:
    effective_query: str
    classifier_text: str
    has_user_message: bool
    warnings: List[AnalyticsWarning] = field(default_factory=list)
    problems: List[QueryProblemReason] = field(default_factory=list)


def _role_value(role) -> str:
    return role.value if isinstance(role, Role) else str(role)


def extract_effective_query(data: AnalysisInput) -> ExtractionResult:
    warnings: List[AnalyticsWarning] = []
    problems: List[QueryProblemReason] = []

    # 1. last user message
    last_user_content = None
    for message in data.messages:
        if _role_value(message.role).lower() == "user":
            last_user_content = message.content or ""

    # 2. no user message at all
    if last_user_content is None:
        return ExtractionResult(
            effective_query="",
            classifier_text="",
            has_user_message=False,
            warnings=[AnalyticsWarning.no_user_message],
            problems=[],
        )

    raw_content = last_user_content

    # 3/4. Prefer the LAST <user_query> pair. If a producer supplied only
    # <context> tags, remove those blocks and analyze the remaining instruction.
    # This keeps a 100k document out of the classification prompt without
    # requiring every integration to emit <user_query>.
    matches = _USER_QUERY_RE.findall(raw_content)
    if matches:
        extracted = matches[-1]
    else:
        without_context = _CONTEXT_RE.sub(" ", raw_content)
        extracted = without_context if without_context.strip() else raw_content

    # 5/6. normalize whitespace
    effective_query = _WHITESPACE_RE.sub(" ", extracted).strip()

    # 8. classifier text with symmetric truncation
    if len(effective_query) <= CLASSIFIER_MAX_CHARS:
        classifier_text = effective_query
    else:
        classifier_text = effective_query[:TRUNCATE_HALF] + effective_query[-TRUNCATE_HALF:]
        warnings.append(AnalyticsWarning.query_truncated)

    # 9. Context includes system/tool/history messages too. Provider usage is
    # authoritative; the character limit is only a fallback when usage is absent.
    total_context_chars = sum(len(message.content or "") for message in data.messages)
    if context_exceeds_supported_limit(
        total_context_chars=total_context_chars,
        prompt_tokens=data.prompt_tokens,
    ):
        problems.append(QueryProblemReason.oversized_context)

    return ExtractionResult(
        effective_query=effective_query,
        classifier_text=classifier_text,
        has_user_message=True,
        warnings=warnings,
        problems=problems,
    )
