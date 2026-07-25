"""OpenAI-compatible embeddings client used by scenario discovery.

The embedding endpoint shares credentials with the classifier by default. All
settings can be overridden independently:

    EMBEDDING_BASE_URL
    EMBEDDING_API_KEY
    EMBEDDING_MODEL
    EMBEDDING_TIMEOUT_SECONDS
    EMBEDDING_BATCH_SIZE

When embeddings are unavailable, scenario discovery falls back to the fully
offline TF-IDF pipeline.
"""

from __future__ import annotations

import os
from typing import List

import httpx
import numpy as np
from sklearn.preprocessing import normalize

from app.core.config import get_settings

DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_BATCH_SIZE = 96


class EmbeddingError(Exception):
    """Raised when semantic vectors cannot be obtained or validated."""


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, ""))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def get_config() -> dict[str, object]:
    settings = get_settings()
    return {
        "base_url": (
            os.getenv("EMBEDDING_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or settings.embedding_base_url
            or settings.llm_base_url
            or ""
        ).strip(),
        "api_key": (
            os.getenv("EMBEDDING_API_KEY")
            or os.getenv("LLM_API_KEY")
            or settings.embedding_api_key
            or settings.llm_api_key
            or ""
        ).strip(),
        "model": (
            os.getenv("EMBEDDING_MODEL")
            or settings.embedding_model
            or DEFAULT_MODEL
        ).strip(),
        "timeout": _positive_float(
            "EMBEDDING_TIMEOUT_SECONDS",
            float(settings.embedding_timeout_seconds),
        ),
        "batch_size": min(
            _positive_int(
                "EMBEDDING_BATCH_SIZE",
                settings.embedding_batch_size,
            ),
            256,
        ),
    }


def is_configured() -> bool:
    config = get_config()
    return bool(config["base_url"] and config["model"])


async def embed_texts(texts: List[str]) -> np.ndarray:
    """Return L2-normalized vectors in the same order as ``texts``."""

    if not texts:
        return np.empty((0, 0), dtype=np.float64)
    config = get_config()
    base_url = str(config["base_url"]).rstrip("/")
    if not base_url:
        raise EmbeddingError("Embedding endpoint is not configured")

    headers = {"Content-Type": "application/json"}
    api_key = str(config["api_key"])
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    vectors: list[list[float]] = []
    batch_size = int(config["batch_size"])
    try:
        async with httpx.AsyncClient(timeout=float(config["timeout"])) as client:
            for start in range(0, len(texts), batch_size):
                response = await client.post(
                    f"{base_url}/embeddings",
                    headers=headers,
                    json={
                        "model": config["model"],
                        "input": texts[start : start + batch_size],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("data")
                if not isinstance(rows, list):
                    raise EmbeddingError("Embedding response has no data array")
                rows = sorted(rows, key=lambda row: int(row["index"]))
                vectors.extend(row["embedding"] for row in rows)
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError(str(exc)) from exc

    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"Expected {len(texts)} embeddings, received {len(vectors)}"
        )
    try:
        matrix = np.asarray(vectors, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise EmbeddingError("Embedding vectors are not numeric") from exc
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise EmbeddingError("Embedding vectors have an invalid shape")
    if not np.isfinite(matrix).all():
        raise EmbeddingError("Embedding vectors contain non-finite values")
    return normalize(matrix)
