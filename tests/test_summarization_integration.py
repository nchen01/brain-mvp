"""Integration tests for SummarizationService with real OpenAI API calls.

Requires:
    OPENAI_API_KEY set in environment or .env

Run with:
    pytest tests/test_summarization_integration.py -v -s
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

# ── path bootstrap ──────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env so OPENAI_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from docforge.preprocessing.schemas import (
    ContentElement,
    DocumentStructure,
    ProcessingMetadata,
    ProcessingStatus,
    StandardizedDocumentOutput,
)
from docforge.postprocessing.schemas import ChunkingStrategy, DocumentSummaries
from docforge.postprocessing.summarizer import SummarizationService
from docforge.postprocessing.chunker import DocumentChunker


# ── skip if no key ───────────────────────────────────────────────────────────
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _service(section_min_tokens: int = 100) -> SummarizationService:
    return SummarizationService(
        enabled=True,
        mode="llm",
        api_provider="openai",
        model_name="gpt-4o-mini",
        max_doc_tokens_for_direct_summary=8000,
        section_summary_min_tokens=section_min_tokens,
    )


def _make_element(eid, ctype, content, page=1):
    return ContentElement(
        element_id=eid,
        content_type=ctype,
        content=content,
        metadata={"page": page},
    )


def _make_doc(elements: List[ContentElement], title: str = "Test Document"):
    plain_text = "\n".join(e.content for e in elements)
    return StandardizedDocumentOutput(
        content_elements=elements,
        document_metadata={"title": title},
        document_structure=DocumentStructure(total_elements=len(elements)),
        processing_metadata=ProcessingMetadata(
            processor_name="test",
            processor_version="0.0",
            processing_timestamp=datetime.now(timezone.utc),
            processing_duration=0.0,
        ),
        processing_status=ProcessingStatus.SUCCESS,
        plain_text=plain_text,
    )


# ── tests ────────────────────────────────────────────────────────────────────

class TestRealOpenAISummarization:

    def test_doc_summary_is_coherent(self):
        """Real LLM call: doc summary should be a non-empty, readable string."""
        elements = [
            _make_element("h1", "heading", "Introduction to Perovskite Solar Cells"),
            _make_element("p1", "paragraph",
                "Perovskite solar cells have emerged as a promising photovoltaic technology "
                "due to their high power conversion efficiency and low manufacturing cost. "
                "The metal-insulator-semiconductor junction plays a critical role in selective "
                "charge collection, reducing recombination losses at interfaces."),
            _make_element("h2", "heading", "Experimental Methods"),
            _make_element("p2", "paragraph",
                "Thin films were deposited via spin coating at 4000 rpm for 30 seconds. "
                "Current-voltage characteristics were measured under AM1.5G illumination "
                "at 100 mW/cm2 using a Keithley 2400 source meter. Transient photovoltage "
                "and photocurrent decay measurements were performed to assess recombination dynamics."),
            _make_element("h3", "heading", "Results and Discussion"),
            _make_element("p3", "paragraph",
                "Devices incorporating the MIS junction achieved a champion efficiency of 21.3% "
                "compared to 18.7% for the control group. Open-circuit voltage improved from "
                "1.08V to 1.14V, attributed to suppressed non-radiative recombination at the "
                "electron transport layer interface. Electrochemical impedance spectroscopy "
                "confirmed reduced interfacial trap density in MIS devices."),
        ]
        doc = _make_doc(elements, title="Perovskite Solar Cells Study")

        summaries = _service().summarize_document(doc)

        print(f"\n--- Doc Summary ---\n{summaries.doc_summary}")

        assert summaries.doc_summary != ""
        assert len(summaries.doc_summary.split()) >= 10  # at least a real sentence
        # Should mention something relevant — perovskite, solar, efficiency, or charge
        keywords = {"perovskite", "solar", "efficiency", "charge", "junction", "photovoltaic"}
        words = summaries.doc_summary.lower()
        assert any(kw in words for kw in keywords), \
            f"Summary doesn't mention relevant content: {summaries.doc_summary}"

    def test_section_summaries_generated_for_large_sections(self):
        """Sections above threshold should each get their own summary."""
        long_para = " ".join(["Perovskite solar cells exhibit high charge carrier mobility."] * 15)
        elements = [
            _make_element("h1", "heading", "Background"),
            _make_element("p1", "paragraph", long_para),
            _make_element("h2", "heading", "Results"),
            _make_element("p2", "paragraph", long_para),
        ]
        doc = _make_doc(elements, title="Solar Cell Research")

        summaries = _service(section_min_tokens=50).summarize_document(doc)

        print(f"\n--- Section Summaries ---")
        for k, v in summaries.section_summaries.items():
            print(f"  [{k}]: {v}")

        assert "h1" in summaries.section_summaries, "h1 section should have a summary"
        assert "h2" in summaries.section_summaries, "h2 section should have a summary"
        assert summaries.section_summaries["h1"] != ""
        assert summaries.section_summaries["h2"] != ""

    def test_small_sections_not_summarized(self):
        """Sections below threshold should be skipped to save API cost."""
        elements = [
            _make_element("h1", "heading", "Intro"),
            _make_element("p1", "paragraph", "Short intro."),
        ]
        doc = _make_doc(elements)

        # Very high threshold so nothing qualifies
        summaries = _service(section_min_tokens=9999).summarize_document(doc)

        print(f"\n--- Section summaries (expect empty): {summaries.section_summaries}")
        assert summaries.section_summaries == {}

    def test_large_doc_uses_excerpt_strategy(self):
        """Docs over max_doc_tokens_for_direct_summary should still get a summary."""
        # ~9000 tokens worth of text (well over the 1000-token limit we set)
        long_text = "Perovskite solar cells improve efficiency through defect passivation. " * 300
        elements = [
            _make_element("h1", "heading", "Overview"),
            _make_element("p1", "paragraph", long_text),
        ]
        doc = _make_doc(elements, title="Long Technical Report")

        # Very small token limit to force the excerpt path
        svc = SummarizationService(
            enabled=True, mode="llm", api_provider="openai",
            model_name="gpt-4o-mini",
            max_doc_tokens_for_direct_summary=1000,
            section_summary_min_tokens=99999,
        )
        summaries = svc.summarize_document(doc)

        print(f"\n--- Large doc summary (excerpt path) ---\n{summaries.doc_summary}")
        assert summaries.doc_summary != ""

    def test_chunks_carry_summaries_end_to_end(self):
        """Full pipeline: summarize → chunk → verify every chunk has doc_summary."""
        long_para = " ".join(["The MIS junction improves open-circuit voltage significantly."] * 20)
        elements = [
            _make_element("h1", "heading", "Introduction"),
            _make_element("p1", "paragraph", long_para),
            _make_element("h2", "heading", "Methods"),
            _make_element("p2", "paragraph", long_para),
        ]
        doc = _make_doc(elements, title="MIS Junction Study")

        summaries = _service(section_min_tokens=50).summarize_document(doc)

        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            config={"chunk_size": 300, "chunk_overlap": 0, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc, summaries=summaries)

        print(f"\n--- {len(chunks)} chunks produced ---")
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i}: doc_summary={bool(chunk.doc_summary)}, "
                  f"section_summary={bool(chunk.section_summary)}, "
                  f"section_path='{chunk.section_path}'")
            enriched = DocumentChunker.build_enriched_text(chunk, title="MIS Junction Study")
            print(f"    enriched preview: {enriched[:120]}...")

        assert len(chunks) > 0
        # Every chunk must carry the doc summary
        for chunk in chunks:
            assert chunk.doc_summary == summaries.doc_summary, \
                f"Chunk {chunk.chunk_id} missing doc_summary"

        # Enriched text must contain the summary
        for chunk in chunks:
            enriched = DocumentChunker.build_enriched_text(chunk, title="MIS Junction Study")
            assert "Overall summary:" in enriched
            assert chunk.content in enriched
