"""Thin async client for an OpenAI-compatible ``/chat/completions`` endpoint.

Configuration is read from environment variables (00_SHARED_CONTRACT.md
section 8.1 / 13)::

    LLM_BASE_URL
    LLM_API_KEY
    LLM_MODEL
    LLM_TIMEOUT_SECONDS   (default 20)

If the endpoint is not configured the module reports itself as *not
configured* and callers fall back to the deterministic rule-based path. Any
transport / HTTP / decoding failure is normalised to :class:`LLMError` so the
public functions never raise because of the LLM.

Tests monkeypatch :func:`is_configured` and :func:`chat_completion` on this
module, so callers must reference them as module attributes (never
``from .llm_client import chat_completion``).
"""

from __future__ import annotations

import os
from typing import Dict, List

import httpx

DEFAULT_TIMEOUT_SECONDS = 20.0


class LLMError(Exception):
    """Raised for any LLM transport/HTTP/decoding failure."""


def _get_timeout() -> float:
    raw = os.getenv("LLM_TIMEOUT_SECONDS", "")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
        return value if value > 0 else DEFAULT_TIMEOUT_SECONDS
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def get_config() -> Dict[str, object]:
    return {
        "base_url": (os.getenv("LLM_BASE_URL") or "").strip(),
        "api_key": (os.getenv("LLM_API_KEY") or "").strip(),
        "model": (os.getenv("LLM_MODEL") or "").strip(),
        "timeout": _get_timeout(),
    }


def is_configured() -> bool:
    """True only when we have enough to attempt a real request."""

    cfg = get_config()
    return bool(cfg["base_url"] and cfg["model"])


async def chat_completion(messages: List[Dict[str, str]]) -> str:
    """POST an OpenAI-style chat completion and return the message content.

    Uses ``temperature=0`` and ``stream=false`` for determinism. Raises
    :class:`LLMError` on any failure.
    """

    cfg = get_config()
    base_url = str(cfg["base_url"]).rstrip("/")
    if not base_url:
        raise LLMError("LLM not configured")

    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = str(cfg["api_key"])
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]
    except LLMError:
        raise
    except Exception as exc:  # timeout, HTTP status, JSON, key errors …
        raise LLMError(str(exc)) from exc
