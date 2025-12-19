"""Utility helpers for estimating token usage."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

try:
    import tiktoken  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    tiktoken = None  # type: ignore


class TokenCounter:
    """Counts tokens for text using tiktoken when available."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.encoder = self._load_encoder(model_name)

    def _load_encoder(self, model_name: str):
        if not tiktoken:
            return None
        try:
            return tiktoken.encoding_for_model(model_name)
        except Exception:  # pragma: no cover - fallback path
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None

    def count(self, text: Optional[str]) -> int:
        """Return the approximate token count for ``text``."""
        if not text:
            return 0

        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:  # pragma: no cover - encoder failure
                pass

        # Simple heuristic fallback: ~4 characters per token
        avg_chars_per_token = 4
        return max(1, len(text) // avg_chars_per_token)


@lru_cache(maxsize=4)
def get_token_counter(model_name: str = "gpt-3.5-turbo") -> TokenCounter:
    """Return a cached token counter instance."""
    return TokenCounter(model_name=model_name)
