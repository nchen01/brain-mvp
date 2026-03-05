"""Summarization service for document and section summaries.

Supports LLM-based (Anthropic / OpenAI) and local extractive modes.
Toggle via SummarizationService(mode="extractive") for cost/latency-sensitive deployments.
"""

import logging
import math
import re
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

from docforge.preprocessing.schemas import StandardizedDocumentOutput
from docforge.postprocessing.schemas import DocumentSummaries  # canonical Pydantic model

logger = logging.getLogger(__name__)


class SummarizationService:
    """Generates document and section summaries for RAG chunk enrichment.

    Usage::

        service = SummarizationService(enabled=True, mode="llm")
        summaries = service.summarize_document(parsed_doc)
        # summaries.doc_summary  → 2-3 sentence overview
        # summaries.section_summaries  → {heading_element_id: "…"}
    """

    def __init__(
        self,
        enabled: bool = True,
        mode: str = "llm",
        model_name: str = "claude-haiku-4-5-20251001",
        api_provider: str = "anthropic",
        max_doc_tokens_for_direct_summary: int = 8000,
        section_summary_min_tokens: int = 200,
    ) -> None:
        """
        Args:
            enabled: Master switch.  When False, returns empty summaries immediately.
            mode: "llm" (default) or "extractive" (local TF-IDF, no API calls).
            model_name: LLM model identifier used when mode="llm".
            api_provider: "anthropic" (default) or "openai".
            max_doc_tokens_for_direct_summary: If the document is longer than this
                (estimated tokens), send only headings + head/tail excerpts instead
                of the full text.
            section_summary_min_tokens: Minimum estimated token count for a section
                to receive an individual LLM summary.
        """
        self.enabled = enabled
        self.mode = mode
        self.model_name = model_name
        self.api_provider = api_provider
        self.max_doc_tokens_for_direct_summary = max_doc_tokens_for_direct_summary
        self.section_summary_min_tokens = section_summary_min_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarize_document(self, document: StandardizedDocumentOutput) -> DocumentSummaries:
        """Generate doc-level and section-level summaries.

        Args:
            document: Preprocessed document output.

        Returns:
            DocumentSummaries (empty when disabled).
        """
        if not self.enabled:
            return DocumentSummaries()

        if self.mode == "extractive":
            return self._summarize_extractive(document)

        return self._summarize_llm(document)

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _summarize_llm(self, document: StandardizedDocumentOutput) -> DocumentSummaries:
        title = document.document_metadata.get("title", "Untitled")
        full_text = document.plain_text or ""
        token_estimate = len(full_text) // 4  # rough: ~4 chars / token

        if token_estimate <= self.max_doc_tokens_for_direct_summary:
            doc_input = f"Title: {title}\n\n{full_text}"
        else:
            # Headings + head/tail excerpts to stay within token budget
            headings = [
                e.content
                for e in document.content_elements
                if e.content_type in ("heading", "HEADING")
            ]
            headings_str = "\n".join(f"- {h}" for h in headings[:20])
            max_chars = self.max_doc_tokens_for_direct_summary * 3  # 3 chars/token safety margin
            half = max_chars // 2
            doc_input = (
                f"Title: {title}\n\n"
                f"Section headings:\n{headings_str}\n\n"
                f"Document excerpt (beginning):\n{full_text[:half]}\n\n"
                f"Document excerpt (end):\n{full_text[-half:]}"
            )

        doc_prompt = (
            "You are summarizing a document for a retrieval system. "
            "In 2–3 sentences, describe the main purpose, scope, and key topics "
            "without adding new facts.\n\n"
            f"{doc_input}"
        )

        start = time.time()
        try:
            doc_summary = self._call_llm(doc_prompt)
            logger.info(
                "Doc summary generated for '%s' (~%d tokens, %.2fs)",
                title,
                token_estimate,
                time.time() - start,
            )
        except Exception as exc:
            logger.error("Failed to summarize document '%s': %s", title, exc)
            doc_summary = ""

        # Section summaries for large sections only
        section_summaries: Dict[str, str] = {}
        for heading_id, section_text in self._extract_sections(document):
            if len(section_text) // 4 < self.section_summary_min_tokens:
                continue  # section too small – skip LLM call
            section_prompt = (
                "You are summarizing one section of a larger document. "
                "In 1–2 sentences, say what this section covers and how it relates "
                "to the document topic. Do not invent new facts.\n\n"
                f"Document title: {title}\n\n"
                f"Section content:\n{section_text}"
            )
            try:
                section_summaries[heading_id] = self._call_llm(section_prompt)
            except Exception as exc:
                logger.warning("Failed to summarize section %s: %s", heading_id, exc)

        return DocumentSummaries(doc_summary=doc_summary, section_summaries=section_summaries)

    # ------------------------------------------------------------------
    # Extractive fallback (no API calls)
    # ------------------------------------------------------------------

    def _summarize_extractive(self, document: StandardizedDocumentOutput) -> DocumentSummaries:
        """Return a TF-IDF sentence-scoring summary with no external calls."""
        title = document.document_metadata.get("title", "Untitled")
        full_text = document.plain_text or ""
        if not full_text:
            return DocumentSummaries()

        try:
            doc_summary = self._tfidf_sentences(full_text, n=3)
        except Exception as exc:
            logger.warning("Extractive summary failed for '%s': %s", title, exc)
            doc_summary = ""

        return DocumentSummaries(doc_summary=doc_summary, section_summaries={})

    @staticmethod
    def _tfidf_sentences(text: str, n: int = 3) -> str:
        """Select the top-n sentences by inverse-log word frequency score."""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) <= n:
            return " ".join(sentences)

        words_per_sent: List[List[str]] = [
            re.findall(r"\b\w+\b", s.lower()) for s in sentences
        ]
        freq = Counter(w for words in words_per_sent for w in words)

        def score(words: List[str]) -> float:
            if not words:
                return 0.0
            return sum(1.0 / math.log(1 + freq[w]) for w in words) / len(words)

        ranked = sorted(range(len(sentences)), key=lambda i: score(words_per_sent[i]), reverse=True)
        top = sorted(ranked[:n])
        return " ".join(sentences[i] for i in top)

    # ------------------------------------------------------------------
    # LLM dispatch
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        if self.api_provider == "anthropic":
            return self._call_anthropic(prompt)
        return self._call_openai(prompt)

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic  # optional dependency

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model_name,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _call_openai(self, prompt: str) -> str:
        import openai  # optional dependency

        client = openai.OpenAI()
        resp = client.chat.completions.create(
            model=self.model_name,
            max_tokens=256,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Section extraction helper
    # ------------------------------------------------------------------

    def _extract_sections(
        self, document: StandardizedDocumentOutput
    ) -> List[Tuple[str, str]]:
        """Group consecutive content elements into (heading_id, full_section_text) tuples.

        Each heading starts a new section; text until the next heading belongs to
        the previous section.
        """
        sections: List[Tuple[str, str]] = []
        current_heading_id: Optional[str] = None
        current_texts: List[str] = []

        for element in document.content_elements:
            is_heading = element.content_type in ("heading", "HEADING")
            if is_heading:
                if current_heading_id is not None and current_texts:
                    sections.append((current_heading_id, "\n".join(current_texts)))
                current_heading_id = element.element_id
                current_texts = [element.content]
            elif current_heading_id is not None:
                current_texts.append(element.content)

        # Flush last section
        if current_heading_id is not None and current_texts:
            sections.append((current_heading_id, "\n".join(current_texts)))

        return sections
