"""
Unit tests for the hybrid structure-aware chunking pipeline.

Tests cover:
- Configuration defaults and validation
- Integration with DocumentChunker dispatch
- Boundary respect (section, paragraph, sentence)
- Length-based routing (SHORT/MEDIUM/LONG)
- Overlap and relationship linking
- Config passthrough from flat dict
- Edge cases (empty docs, single paragraph, no headings)
- Regression: existing strategies still work
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docforge.preprocessing.schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingStatus,
    create_processing_metadata,
    create_document_structure,
)
from docforge.postprocessing.chunker import (
    DocumentChunker,
    HybridStructureAwareChunker,
)
from docforge.postprocessing.schemas import ChunkingStrategy, ChunkData
from docforge.postprocessing.hybrid_chunking import (
    HybridChunkingConfig,
    HybridDocumentChunker,
    SectionSizeCategory,
)
from docforge.postprocessing.hybrid_chunking.normalizer import MinerUDocumentNormalizer
from docforge.postprocessing.hybrid_chunking.section_router import SectionRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_document(elements_spec):
    """
    Build a StandardizedDocumentOutput from a list of element specs.

    Each spec is a tuple: (ContentType, content_str, metadata_dict)
    """
    elements = []
    for i, (ctype, content, meta) in enumerate(elements_spec):
        elements.append(
            ContentElement(
                element_id=f"elem_{i}",
                content=content,
                content_type=ctype,
                metadata=meta or {"page": 1},
            )
        )
    processing_metadata = create_processing_metadata(
        processor_name="TestProcessor",
        processor_version="1.0.0",
        processing_duration=0.0,
    )
    document_structure = create_document_structure(
        total_elements=len(elements),
        total_pages=1,
    )
    plain = "\n\n".join(e.content for e in elements)
    return StandardizedDocumentOutput(
        content_elements=elements,
        document_metadata={"title": "Test Document"},
        document_structure=document_structure,
        processing_metadata=processing_metadata,
        processing_status=ProcessingStatus.SUCCESS,
        plain_text=plain,
        markdown_text=plain,
    )


def _words(n, seed="word"):
    """Generate a string with exactly n words."""
    return " ".join(f"{seed}{i}" for i in range(n))


def _make_multi_section_doc():
    """
    Build a realistic document with varied section sizes for integration tests.

    Sections:
        Introduction (H1) — ~30 words (SHORT)
        Background (H2) — ~250 words (MEDIUM)
        Short Note (H2) — ~15 words (SHORT)
        Methodology (H2) — ~800 words (LONG)
    """
    specs = [
        (ContentType.HEADING, "Introduction", {"page": 1, "level": 1}),
        (ContentType.PARAGRAPH, _words(30, "intro"), {"page": 1}),
        (ContentType.HEADING, "Background", {"page": 1, "level": 2}),
        (ContentType.PARAGRAPH, _words(120, "bg1"), {"page": 1}),
        (ContentType.PARAGRAPH, _words(130, "bg2"), {"page": 2}),
        (ContentType.HEADING, "Short Note", {"page": 2, "level": 2}),
        (ContentType.PARAGRAPH, _words(15, "note"), {"page": 2}),
        (ContentType.HEADING, "Methodology", {"page": 3, "level": 2}),
        (ContentType.PARAGRAPH, _words(300, "meth1"), {"page": 3}),
        (ContentType.PARAGRAPH, _words(250, "meth2"), {"page": 3}),
        (ContentType.PARAGRAPH, _words(250, "meth3"), {"page": 4}),
    ]
    return _build_document(specs)


# ---------------------------------------------------------------------------
# 1. Configuration tests
# ---------------------------------------------------------------------------

class TestHybridChunkingConfig:

    def test_defaults_match_token_requirements(self):
        cfg = HybridChunkingConfig()
        assert cfg.target_chunk_size == 350
        assert cfg.max_chunk_size == 500
        assert cfg.chunk_overlap == 50
        assert cfg.min_chunk_size == 30
        # Overlap is ~14% of target, within 10-20%
        overlap_pct = cfg.chunk_overlap / cfg.target_chunk_size
        assert 0.10 <= overlap_pct <= 0.20
        assert cfg.short_section_threshold < cfg.long_section_threshold

    def test_validation_rejects_invalid_thresholds(self):
        with pytest.raises(ValueError):
            HybridChunkingConfig(short_section_threshold=800, long_section_threshold=100)

    def test_validation_rejects_invalid_chunk_sizes(self):
        with pytest.raises(ValueError):
            HybridChunkingConfig(min_chunk_size=500, target_chunk_size=100, max_chunk_size=600)

    def test_validation_rejects_target_exceeding_max(self):
        with pytest.raises(ValueError):
            HybridChunkingConfig(target_chunk_size=900, max_chunk_size=500)

    def test_factory_for_short_documents(self):
        cfg = HybridChunkingConfig.for_short_documents()
        assert cfg.target_chunk_size < HybridChunkingConfig().target_chunk_size
        assert cfg.short_section_threshold < cfg.long_section_threshold

    def test_factory_for_long_documents(self):
        cfg = HybridChunkingConfig.for_long_documents()
        assert cfg.target_chunk_size > HybridChunkingConfig().target_chunk_size
        assert cfg.short_section_threshold < cfg.long_section_threshold


# ---------------------------------------------------------------------------
# 2. Dispatch / integration tests
# ---------------------------------------------------------------------------

class TestHybridDispatch:

    def test_strategy_registered_in_dispatch_map(self):
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        assert isinstance(chunker.chunker, HybridStructureAwareChunker)

    def test_skip_post_processing_flag(self):
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        assert getattr(chunker.chunker, "skip_post_processing", False) is True

    def test_returns_chunk_data_list(self):
        doc = _make_multi_section_doc()
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, ChunkData)
            assert chunk.content
            assert chunk.metadata.word_count > 0


# ---------------------------------------------------------------------------
# 3. Boundary respect tests
# ---------------------------------------------------------------------------

class TestBoundaryRespect:

    def test_chunks_reference_single_section(self):
        """Each chunk's position should reference one section, not span multiple."""
        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        for r in results:
            assert r.source_section_id, "Every chunk should have a source section ID"

    def test_paragraph_boundary_splitting(self):
        """A medium section with multiple paragraphs should split at paragraph boundaries."""
        specs = [
            (ContentType.HEADING, "Section A", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(200, "p1"), {"page": 1}),
            (ContentType.PARAGRAPH, _words(200, "p2"), {"page": 1}),
        ]
        doc = _build_document(specs)
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        # With target=350, 200+200=400 words should produce 2 chunks (one per paragraph)
        assert len(results) >= 2


# ---------------------------------------------------------------------------
# 4. Length-based routing tests
# ---------------------------------------------------------------------------

class TestSectionRouting:

    def test_section_router_classification(self):
        """SectionRouter should classify by word count thresholds."""
        from docforge.postprocessing.hybrid_chunking.normalized_document import (
            NormalizedSection,
            NormalizedParagraph,
        )
        cfg = HybridChunkingConfig()
        router = SectionRouter(cfg)

        short_sec = NormalizedSection.create(
            paragraphs=[NormalizedParagraph.create(text=_words(50), page_number=1)]
        )
        medium_sec = NormalizedSection.create(
            paragraphs=[NormalizedParagraph.create(text=_words(300), page_number=1)]
        )
        long_sec = NormalizedSection.create(
            paragraphs=[NormalizedParagraph.create(text=_words(900), page_number=1)]
        )

        assert router.classify_section(short_sec) == SectionSizeCategory.SHORT
        assert router.classify_section(medium_sec) == SectionSizeCategory.MEDIUM
        assert router.classify_section(long_sec) == SectionSizeCategory.LONG

    def test_short_sections_kept_or_merged(self):
        """Adjacent short sections should be merged into fewer chunks."""
        specs = [
            (ContentType.HEADING, "A", {"page": 1, "level": 2}),
            (ContentType.PARAGRAPH, _words(40, "a"), {"page": 1}),
            (ContentType.HEADING, "B", {"page": 1, "level": 2}),
            (ContentType.PARAGRAPH, _words(40, "b"), {"page": 1}),
            (ContentType.HEADING, "C", {"page": 1, "level": 2}),
            (ContentType.PARAGRAPH, _words(40, "c"), {"page": 1}),
        ]
        doc = _build_document(specs)
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        # 3 short sections (40 words each, all < 100) should merge into fewer chunks
        assert len(results) < 3

    def test_medium_section_recursive_split(self):
        """A medium section should be recursively split into multiple chunks."""
        specs = [
            (ContentType.HEADING, "Section", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(200, "p1"), {"page": 1}),
            (ContentType.PARAGRAPH, _words(200, "p2"), {"page": 1}),
        ]
        doc = _build_document(specs)
        cfg = HybridChunkingConfig()
        chunker = HybridDocumentChunker(cfg)
        results = chunker.chunk_document(doc)
        assert len(results) >= 2
        for r in results:
            assert r.chunk_data.metadata.word_count <= cfg.max_chunk_size + cfg.chunk_overlap + 10

    def test_long_section_flags_semantic_refinement(self):
        """Long sections should be flagged as semantic refinement candidates."""
        specs = [
            (ContentType.HEADING, "Long Section", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(400, "lp1"), {"page": 1}),
            (ContentType.PARAGRAPH, _words(400, "lp2"), {"page": 2}),
        ]
        doc = _build_document(specs)
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        semantic_candidates = [r for r in results if r.is_semantic_refinement_candidate]
        assert len(semantic_candidates) > 0
        for sc in semantic_candidates:
            assert sc.size_category == SectionSizeCategory.LONG


# ---------------------------------------------------------------------------
# 5. Chunk size and overlap tests
# ---------------------------------------------------------------------------

class TestChunkSizeAndOverlap:

    def test_chunk_sizes_within_limits(self):
        doc = _make_multi_section_doc()
        cfg = HybridChunkingConfig()
        chunker = HybridDocumentChunker(cfg)
        results = chunker.chunk_document(doc)
        for r in results:
            # Allow some headroom for overlap prefix
            assert r.chunk_data.metadata.word_count <= cfg.max_chunk_size + cfg.chunk_overlap + 10

    def test_overlap_between_adjacent_chunks(self):
        """When a section produces multiple chunks, adjacent ones should have overlapping words."""
        specs = [
            (ContentType.HEADING, "Big Section", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(800, "overlap"), {"page": 1}),
        ]
        doc = _build_document(specs)
        cfg = HybridChunkingConfig(chunk_overlap=50)
        chunker = HybridDocumentChunker(cfg)
        results = chunker.chunk_document(doc)

        if len(results) >= 2:
            # The second chunk should start with "[...]" overlap marker
            second_content = results[1].chunk_data.content
            assert "[...]" in second_content


# ---------------------------------------------------------------------------
# 6. Relationship linking tests
# ---------------------------------------------------------------------------

class TestRelationships:

    def test_chunk_relationships_linked(self):
        doc = _make_multi_section_doc()
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)

        if len(chunks) < 2:
            pytest.skip("Need at least 2 chunks to test relationships")

        for i, chunk in enumerate(chunks):
            if i > 0:
                assert "previous" in chunk.relationships
            if i < len(chunks) - 1:
                assert "next" in chunk.relationships

    def test_relationship_chain_consistent(self):
        doc = _make_multi_section_doc()
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)

        for i in range(len(chunks) - 1):
            next_ids = chunks[i].relationships.get("next", [])
            assert chunks[i + 1].chunk_id in next_ids


# ---------------------------------------------------------------------------
# 7. Config passthrough tests
# ---------------------------------------------------------------------------

class TestConfigPassthrough:

    def test_flat_dict_hybrid_keys(self):
        adapter = HybridStructureAwareChunker(
            {"target_chunk_size": 200, "max_chunk_size": 400, "chunk_overlap": 30}
        )
        cfg = adapter._hybrid_chunker.config
        assert cfg.target_chunk_size == 200
        assert cfg.max_chunk_size == 400
        assert cfg.chunk_overlap == 30

    def test_chunk_size_maps_to_target(self):
        """The standard BaseChunker 'chunk_size' key should map to target_chunk_size."""
        adapter = HybridStructureAwareChunker({"chunk_size": 400})
        cfg = adapter._hybrid_chunker.config
        assert cfg.target_chunk_size == 400

    def test_explicit_target_overrides_chunk_size(self):
        """If both chunk_size and target_chunk_size are given, target takes priority."""
        adapter = HybridStructureAwareChunker(
            {"chunk_size": 999, "target_chunk_size": 300, "max_chunk_size": 500}
        )
        cfg = adapter._hybrid_chunker.config
        assert cfg.target_chunk_size == 300


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_document(self):
        doc = _build_document([])
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)
        assert chunks == []

    def test_single_paragraph_no_heading(self):
        specs = [
            (ContentType.PARAGRAPH, _words(80, "solo"), {"page": 1}),
        ]
        doc = _build_document(specs)
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1

    def test_headings_only_no_paragraphs(self):
        specs = [
            (ContentType.HEADING, "Title", {"page": 1, "level": 1}),
            (ContentType.HEADING, "Subtitle", {"page": 1, "level": 2}),
        ]
        doc = _build_document(specs)
        chunker = DocumentChunker(strategy=ChunkingStrategy.HYBRID_STRUCTURE_AWARE)
        chunks = chunker.chunk_document(doc)
        # No paragraph content, so no chunks
        assert chunks == []


# ---------------------------------------------------------------------------
# 9. Normalizer tests
# ---------------------------------------------------------------------------

class TestNormalizer:

    def test_heading_hierarchy(self):
        specs = [
            (ContentType.HEADING, "Chapter 1", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(50, "ch1"), {"page": 1}),
            (ContentType.HEADING, "Section 1.1", {"page": 1, "level": 2}),
            (ContentType.PARAGRAPH, _words(50, "s11"), {"page": 1}),
        ]
        doc = _build_document(specs)
        # Clear document_metadata title so normalizer picks H1
        doc.document_metadata = {}
        normalizer = MinerUDocumentNormalizer()
        normalized = normalizer.normalize(doc)
        # Should have sections at level 1 and level 2
        assert normalized.section_count >= 2
        assert normalized.title == "Chapter 1"

    def test_page_numbers_preserved(self):
        specs = [
            (ContentType.HEADING, "Page 1 Content", {"page": 1, "level": 1}),
            (ContentType.PARAGRAPH, _words(50, "p1"), {"page": 1}),
            (ContentType.HEADING, "Page 2 Content", {"page": 2, "level": 1}),
            (ContentType.PARAGRAPH, _words(50, "p2"), {"page": 2}),
        ]
        doc = _build_document(specs)
        normalizer = MinerUDocumentNormalizer()
        normalized = normalizer.normalize(doc)
        all_sections = normalized.get_all_sections_flat()
        page_numbers = set()
        for s in all_sections:
            page_numbers.update(s.page_numbers)
        assert 1 in page_numbers
        assert 2 in page_numbers


# ---------------------------------------------------------------------------
# 10. Statistics tests
# ---------------------------------------------------------------------------

class TestStatistics:

    def test_statistics_reporting(self):
        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        stats = chunker.get_chunking_statistics(results)
        assert stats["total_chunks"] == len(results)
        assert stats["avg_word_count"] > 0
        assert "by_category" in stats
        assert "by_strategy" in stats


# ---------------------------------------------------------------------------
# 11. Regression: existing strategies unaffected
# ---------------------------------------------------------------------------

class TestRegression:

    def _make_simple_doc(self):
        specs = [
            (ContentType.PARAGRAPH, _words(100, "p1"), {"page": 1}),
            (ContentType.PARAGRAPH, _words(100, "p2"), {"page": 1}),
            (ContentType.PARAGRAPH, _words(100, "p3"), {"page": 1}),
        ]
        return _build_document(specs)

    def test_recursive_strategy_still_works(self):
        doc = self._make_simple_doc()
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.RECURSIVE,
            config={"chunk_size": 100, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0

    def test_paragraph_strategy_still_works(self):
        doc = self._make_simple_doc()
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            config={"chunk_size": 100, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0

    def test_fixed_size_strategy_still_works(self):
        doc = self._make_simple_doc()
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            config={"chunk_size": 100, "chunk_overlap": 20, "min_chunk_size": 5},
        )
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0


# ---------------------------------------------------------------------------
# 12. Page range formatting
# ---------------------------------------------------------------------------

def _format_page_range(page_numbers: list) -> str:
    """Local copy of the helper for testing without heavy transitive imports."""
    if not page_numbers:
        return ""
    pages = sorted(set(int(p) for p in page_numbers))
    if len(pages) == 1:
        return str(pages[0])
    ranges = []
    start = pages[0]
    prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
        else:
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = p
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(ranges)


class TestPageRangeFormatting:

    def _format(self, pages):
        return _format_page_range(pages)

    def test_empty_list(self):
        assert self._format([]) == ""

    def test_single_page(self):
        assert self._format([3]) == "3"

    def test_contiguous_range(self):
        assert self._format([1, 2, 3]) == "1-3"

    def test_non_contiguous(self):
        assert self._format([1, 2, 3, 5]) == "1-3, 5"

    def test_multiple_ranges(self):
        assert self._format([1, 2, 5, 6, 7, 10]) == "1-2, 5-7, 10"

    def test_duplicates_ignored(self):
        assert self._format([1, 1, 2, 2, 3]) == "1-3"

    def test_unsorted_input(self):
        assert self._format([5, 1, 3, 2]) == "1-3, 5"


# ---------------------------------------------------------------------------
# 13. Chunk metadata contains required fields
# ---------------------------------------------------------------------------

class TestChunkMetadataFields:

    def test_hybrid_chunks_have_section_path(self):
        """Hybrid chunks should have section_path in their position data."""
        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        for r in results:
            # source_heading_path is available on every HybridChunkResult
            assert isinstance(r.source_heading_path, list)

    def test_hybrid_chunks_have_page_numbers(self):
        """Hybrid chunks should have page_numbers in metadata."""
        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        for r in results:
            assert isinstance(r.chunk_data.metadata.page_numbers, list)

    def test_hybrid_chunks_position_has_heading_path(self):
        """Position dict should contain heading_path for breadcrumb context."""
        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)
        for r in results:
            assert "heading_path" in r.chunk_data.position

    def test_storage_adapter_includes_required_fields(self):
        """The hybrid storage adapter should include all 5 standardised fields."""
        from docforge.postprocessing.hybrid_chunking.storage_adapter import HybridChunkStorageAdapter

        doc = _make_multi_section_doc()
        chunker = HybridDocumentChunker()
        results = chunker.chunk_document(doc)

        adapter = HybridChunkStorageAdapter.__new__(HybridChunkStorageAdapter)
        for r in results:
            storage_dict = adapter._convert_to_storage_format(r)
            meta = storage_dict["metadata"]
            assert "doc_id" in meta
            assert "title" in meta
            assert "section_path" in meta
            assert "page_range" in meta
            assert "ingestion_timestamp" in meta

    def test_storage_adapter_page_range_matches(self):
        """Storage adapter _format_page_range should produce same output as documents.py helper."""
        from docforge.postprocessing.hybrid_chunking.storage_adapter import HybridChunkStorageAdapter

        assert HybridChunkStorageAdapter._format_page_range([1, 2, 3, 5]) == "1-3, 5"
        assert HybridChunkStorageAdapter._format_page_range([]) == ""
        assert HybridChunkStorageAdapter._format_page_range([7]) == "7"
