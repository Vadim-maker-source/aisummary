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
9. if all request messages together are longer than 20000 chars, or
   ``prompt_tokens`` exceeds 50000, add the ``oversized_context`` problem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .schemas import AnalysisInput, AnalyticsWarning, QueryProblemReason, Role

# <user_query> ... </user_query>: case-insensitive, dot matches newline,
# non-greedy so multiple pairs are captured independently (we keep the last).
_USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")

CLASSIFIER_MAX_CHARS = 8000
TRUNCATE_HALF = 4000
OVERSIZED_CONTENT_CHARS = 20000
OVERSIZED_PROMPT_TOKENS = 50000


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

    # 3/4. prefer the LAST <user_query> pair; never read <context>
    matches = _USER_QUERY_RE.findall(raw_content)
    extracted = matches[-1] if matches else raw_content

    # 5/6. normalize whitespace
    effective_query = _WHITESPACE_RE.sub(" ", extracted).strip()

    # 8. classifier text with symmetric truncation
    if len(effective_query) <= CLASSIFIER_MAX_CHARS:
        classifier_text = effective_query
    else:
        classifier_text = effective_query[:TRUNCATE_HALF] + effective_query[-TRUNCATE_HALF:]
        warnings.append(AnalyticsWarning.query_truncated)

    # 9. Oversized context must include system/tool/history messages too. A
    # short final user question can still be backed by a 100k-token prompt.
    total_context_chars = sum(len(message.content or "") for message in data.messages)
    prompt_tokens = data.prompt_tokens
    if total_context_chars > OVERSIZED_CONTENT_CHARS or (
        prompt_tokens is not None and prompt_tokens > OVERSIZED_PROMPT_TOKENS
    ):
        problems.append(QueryProblemReason.oversized_context)

    return ExtractionResult(
        effective_query=effective_query,
        classifier_text=classifier_text,
        has_user_message=True,
        warnings=warnings,
        problems=problems,
    )
