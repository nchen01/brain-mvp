"""Enrichment module for advanced document processing."""

from .context_enricher import ContextEnricher
from .prompt_templates import (
    CONTEXT_ENRICHMENT_PROMPT,
    SHORT_CONTEXT_PROMPT,
    STRUCTURED_CONTEXT_PROMPT,
    get_prompt_template,
)

__all__ = [
    'ContextEnricher',
    'CONTEXT_ENRICHMENT_PROMPT',
    'SHORT_CONTEXT_PROMPT', 
    'STRUCTURED_CONTEXT_PROMPT',
    'get_prompt_template',
]
