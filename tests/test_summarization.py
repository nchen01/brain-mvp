"""Unit tests for the SummarizationService and summarization-aware chunker.

Run with:
    pytest tests/test_summarization.py -v
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch

import pytest

# ── path bootstrap ──────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.schemas import (
    ContentElement,
    ContentType,
    DocumentStructure,
    ProcessingMetadata,
    ProcessingStatus,
    StandardizedDocumentOutput,
)
from docforge.postprocessing.schemas import (
    ChunkData,
    ChunkMetadata,
    ChunkType,
    DocumentSummaries,
)
from docforge.postprocessing.summarizer import SummarizationService
from docforge.postprocessing.chunker import DocumentChunker
from docforge.postprocessing.schemas import ChunkingStrategy


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_element(eid: str, ctype: str, content: str, page: int = 1) -> ContentElement:
    return ContentElement(
        element_id=eid,
        content_type=ctype,
        content=content,
        metadata={"page": page},
    )


def _make_processing_metadata() -> ProcessingMetadata:
    return ProcessingMetadata(
        processor_name="test",
        processor_version="0.0",
        processing_timestamp=datetime.now(timezone.utc),
        processing_duration=0.0,
    )


def _make_document(elements: List[ContentElement], title: str = "Test Doc") -> StandardizedDocumentOutput:
    plain_text = "\n".join(e.content for e in elements)
    return StandardizedDocumentOutput(
        content_elements=elements,
        document_metadata={"title": title},
        document_structure=DocumentStructure(total_elements=len(elements)),
        processing_metadata=_make_processing_metadata(),
        processing_status=ProcessingStatus.SUCCESS,
        plain_text=plain_text,
    )


def _make_chunk(chunk_id: str, content: str, source_elements: List[str] = None) -> ChunkData:
    meta = ChunkMetadata(
        chunk_id=chunk_id,
        chunk_index=0,
        chunk_type=ChunkType.TEXT,
        source_elements=source_elements or [],
        word_count=len(content.split()),
        character_count=len(content),
    )
    return ChunkData(chunk_id=chunk_id, content=content, chunk_type=ChunkType.TEXT, metadata=meta)


# ─────────────────────────────────────────────────────────────────────────────
# SummarizationService – disabled
# ─────────────────────────────────────────────────────────────────────────────

class TestSummarizationServiceDisabled:
    def test_returns_empty_when_disabled(self):
        elements = [_make_element("e1", "paragraph", "Some content here.")]
        doc = _make_document(elements)
        service = SummarizationService(enabled=False)
        result = service.summarize_document(doc)
        assert result.doc_summary == ""
        assert result.section_summaries == {}


# ─────────────────────────────────────────────────────────────────────────────
# SummarizationService – extractive mode (no LLM calls)
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractiveSummarizer:
    def _service(self) -> SummarizationService:
        return SummarizationService(enabled=True, mode="extractive")

    def test_returns_non_empty_doc_summary(self):
        text = (
            "Alpha is the first letter of the Greek alphabet. "
            "Beta follows alpha in the sequence. "
            "Gamma comes after beta. "
            "Delta is the fourth letter. "
            "Epsilon rounds out the first five."
        )
        elements = [_make_element("e1", "paragraph", text)]
        doc = _make_document(elements, title="Greek Letters")
        result = self._service().summarize_document(doc)
        assert result.doc_summary != ""
        assert isinstance(result.doc_summary, str)

    def test_extractive_no_section_summaries(self):
        """Extractive mode only generates a doc summary, not section-level ones."""
        elements = [
            _make_element("h1", "heading", "Introduction"),
            _make_element("e1", "paragraph", "This introduces the topic."),
        ]
        doc = _make_document(elements)
        result = self._service().summarize_document(doc)
        assert result.section_summaries == {}

    def test_short_doc_returned_as_is(self):
        """Docs with few sentences are returned without truncation."""
        text = "First sentence. Second sentence."
        elements = [_make_element("e1", "paragraph", text)]
        doc = _make_document(elements)
        result = self._service().summarize_document(doc)
        assert "First sentence" in result.doc_summary or "Second sentence" in result.doc_summary

    def test_empty_doc_returns_empty_summary(self):
        doc = _make_document([], title="Empty")
        result = self._service().summarize_document(doc)
        assert result.doc_summary == ""


# ─────────────────────────────────────────────────────────────────────────────
# SummarizationService – LLM mode (mocked)
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMSummarizer:
    def _service(self) -> SummarizationService:
        return SummarizationService(
            enabled=True,
            mode="llm",
            api_provider="anthropic",
            section_summary_min_tokens=10,  # low threshold so test sections are summarized
        )

    def _mock_llm(self, service: SummarizationService, responses: list) -> None:
        """Replace _call_llm with successive canned responses."""
        call_iter = iter(responses)
        service._call_llm = lambda prompt: next(call_iter)

    def test_doc_summary_returned(self):
        service = self._service()
        self._mock_llm(service, ["This doc covers Greek letters.", "Intro section covers alpha."])
        elements = [
            _make_element("h1", "heading", "Introduction"),
            _make_element("e1", "paragraph", "Alpha beta gamma delta epsilon zeta."),
        ]
        doc = _make_document(elements)
        result = service.summarize_document(doc)
        assert result.doc_summary == "This doc covers Greek letters."

    def test_section_summary_for_large_section(self):
        """A section above section_summary_min_tokens should receive its own summary."""
        service = self._service()
        # min_tokens=10 → ~40 chars minimum → craft a section that exceeds that
        long_section = " ".join(["word"] * 60)  # ~300 chars → ~75 tokens
        self._mock_llm(service, ["Doc summary.", "Section summary for intro."])
        elements = [
            _make_element("h1", "heading", "Introduction"),
            _make_element("e1", "paragraph", long_section),
        ]
        doc = _make_document(elements)
        result = service.summarize_document(doc)
        assert "h1" in result.section_summaries
        assert result.section_summaries["h1"] == "Section summary for intro."

    def test_small_section_skipped(self):
        """Sections below the token threshold don't get summaries."""
        service = SummarizationService(
            enabled=True, mode="llm", section_summary_min_tokens=500
        )
        self._mock_llm(service, ["Doc summary."])
        elements = [
            _make_element("h1", "heading", "Tiny section"),
            _make_element("e1", "paragraph", "Short."),
        ]
        doc = _make_document(elements)
        result = service.summarize_document(doc)
        assert result.section_summaries == {}


# ─────────────────────────────────────────────────────────────────────────────
# DocumentChunker – summary attachment
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentChunkerSummaryAttachment:
    def _make_doc_with_sections(self) -> StandardizedDocumentOutput:
        elements = [
            _make_element("h1", "heading", "Chapter One"),
            _make_element("p1", "paragraph", " ".join(["word"] * 80)),
            _make_element("p2", "paragraph", " ".join(["word"] * 80)),
            _make_element("h2", "heading", "Chapter Two"),
            _make_element("p3", "paragraph", " ".join(["word"] * 80)),
        ]
        return _make_document(elements, title="My Document")

    def test_all_chunks_share_doc_summary(self):
        doc = self._make_doc_with_sections()
        summaries = DocumentSummaries(
            doc_summary="Global doc summary.",
            section_summaries={},
        )
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            config={"chunk_size": 500, "chunk_overlap": 0, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc, summaries=summaries)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.doc_summary == "Global doc summary."

    def test_chunks_in_section_share_section_summary(self):
        doc = self._make_doc_with_sections()
        summaries = DocumentSummaries(
            doc_summary="Doc summary.",
            section_summaries={"h1": "Chapter one covers basics."},
        )
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            config={"chunk_size": 500, "chunk_overlap": 0, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc, summaries=summaries)
        # Chunks whose source elements are p1/p2 (under heading h1) should carry section summary
        for chunk in chunks:
            if any(e in ("p1", "p2") for e in chunk.metadata.source_elements):
                assert chunk.section_summary == "Chapter one covers basics."

    def test_no_summaries_leaves_fields_empty(self):
        doc = self._make_doc_with_sections()
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            config={"chunk_size": 500, "chunk_overlap": 0, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc, summaries=None)
        for chunk in chunks:
            assert chunk.doc_summary == ""
            assert chunk.section_summary == ""


# ─────────────────────────────────────────────────────────────────────────────
# DocumentChunker.build_enriched_text
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildEnrichedText:
    def _chunk(self, content: str, doc_summary: str = "", section_summary: str = "", section_path: str = "") -> ChunkData:
        chunk = _make_chunk("c1", content)
        chunk.doc_summary = doc_summary
        chunk.section_summary = section_summary
        chunk.section_path = section_path
        return chunk

    def test_contains_all_parts(self):
        chunk = self._chunk(
            content="Raw content here.",
            doc_summary="Document overview.",
            section_summary="Section detail.",
            section_path="Intro > Background",
        )
        enriched = DocumentChunker.build_enriched_text(chunk, title="My Doc")
        assert "My Doc" in enriched
        assert "Document overview." in enriched
        assert "Intro > Background" in enriched
        assert "Section detail." in enriched
        assert "Raw content here." in enriched

    def test_empty_parts_omitted(self):
        chunk = self._chunk(content="Just content.")
        enriched = DocumentChunker.build_enriched_text(chunk, title="")
        # Should only contain the content part
        assert "Document:" not in enriched
        assert "Overall summary:" not in enriched
        assert "Content: Just content." in enriched

    def test_no_title(self):
        chunk = self._chunk(content="Content.", doc_summary="Summary.")
        enriched = DocumentChunker.build_enriched_text(chunk)  # title defaults to ""
        assert "Document:" not in enriched
        assert "Overall summary: Summary." in enriched
        assert "Content: Content." in enriched

    def test_enriched_is_string(self):
        chunk = self._chunk(content="abc")
        assert isinstance(DocumentChunker.build_enriched_text(chunk), str)
