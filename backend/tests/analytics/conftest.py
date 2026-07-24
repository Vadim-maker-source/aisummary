"""Pytest configuration for the analytics test suite.

- Puts the ``backend/`` directory on ``sys.path`` so tests import the module as
  ``app.analytics.*`` (matching how the backend imports it).
- Clears any ``LLM_*`` environment variables so every test runs fully offline
  by default; tests that exercise the LLM path monkeypatch the client directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "LLM_TIMEOUT_SECONDS"):
        monkeypatch.delenv(var, raising=False)
    yield
