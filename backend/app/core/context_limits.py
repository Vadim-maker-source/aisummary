"""Project-wide limits for analytics request context.

The case dataset has an average prompt size of 100k tokens, so 100k is a
supported input size, not an analytics problem. Token usage reported by the
provider is authoritative. When it is unavailable, a conservative character
budget is used only as a fallback guard.
"""

MAX_SUPPORTED_CONTEXT_TOKENS = 100_000
MAX_UNMETERED_CONTEXT_CHARS = 400_000


def context_exceeds_supported_limit(
    *,
    total_context_chars: int,
    prompt_tokens: int | None,
) -> bool:
    """Return whether context is strictly above the supported 100k boundary.

    An exact provider token count takes precedence over the character fallback.
    Both limits are inclusive: exactly 100k tokens or 400k unmetered characters
    are accepted.
    """

    if prompt_tokens is not None:
        return prompt_tokens > MAX_SUPPORTED_CONTEXT_TOKENS
    return total_context_chars > MAX_UNMETERED_CONTEXT_CHARS
