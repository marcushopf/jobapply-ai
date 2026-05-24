"""Shared test helpers (importable, unlike conftest.py)."""

import hashlib
import os
from pathlib import Path

import pytest

CACHE_DIR = Path(__file__).parent / "fixtures" / "llm_cache"


def _has_api_key() -> bool:
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return True
    try:
        import keyring
        return bool(keyring.get_password("jobapply-ai", "google_api_key"))
    except Exception:
        return False


requires_api = pytest.mark.skipif(
    not _has_api_key(),
    reason="No GOOGLE_API_KEY found — skipping LLM test",
)


class CachedLLMClient:
    """LLM client that caches responses to disk for repeatable integration tests.

    On first run (or with REFRESH_LLM_CACHE=1), calls the real API and saves
    the response. Every subsequent run loads from cache — no API key needed,
    no quota burned, deterministic results.

    Model selection for cache refresh:
      - Set TEST_LLM_MODEL=groq/llama-3.1-8b-instant for fast, free Groq calls
      - Falls back to LLM_MODEL, then Gemini default

    Usage:
        client = CachedLLMClient()              # uses cache when available
        client = CachedLLMClient(refresh=True)  # forces fresh API call
        REFRESH_LLM_CACHE=1 pytest ...          # same via env var
        TEST_LLM_MODEL=groq/llama-3.1-8b-instant REFRESH_LLM_CACHE=1 pytest ...
    """

    def __init__(self, refresh: bool = False):
        self._refresh = refresh or os.getenv("REFRESH_LLM_CACHE", "").lower() in ("1", "true")
        self._real: object = None  # lazy — only created on cache miss
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _real_client(self):
        if self._real is None:
            # TEST_LLM_MODEL overrides LLM_MODEL during cache refresh
            test_model = os.getenv("TEST_LLM_MODEL", "").strip()
            if test_model:
                os.environ["LLM_MODEL"] = test_model
            from llm_client import LLMClient
            self._real = LLMClient()
        return self._real

    def chat(self, prompt: str, max_tokens: int = 1024) -> str:
        key = hashlib.sha256(f"{prompt}|{max_tokens}".encode()).hexdigest()[:20]
        cache_file = CACHE_DIR / f"{key}.txt"

        if not self._refresh and cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

        response = self._real_client().chat(prompt, max_tokens)
        cache_file.write_text(response, encoding="utf-8")
        return response

    @property
    def provider(self) -> str:
        return self._real_client().provider

    @property
    def model(self) -> str:
        return self._real_client().model
