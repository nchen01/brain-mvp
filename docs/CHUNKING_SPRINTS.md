# Chunking Pipeline Sprints

This document tracks the development sprints for the hybrid chunking pipeline.

---

## Sprint 1: Baseline Hybrid Chunking Pipeline (Current)

**Status:** Complete
**Goal:** Extract a dedicated chunking interface with structure-aware recursive chunking

### Objectives
- [x] Create sprint tracking documentation
- [x] Normalize MinerU output into common document model
  - Title, section headings, page numbers, element IDs
- [x] Implement structure-aware recursive chunker
  - Section → Paragraph → Sentence boundary hierarchy
- [x] Implement length-based routing for sections
  - SHORT (< 150 words): Keep as single chunk or merge with adjacent
  - MEDIUM (150-800 words): Recursive paragraph/sentence splitting
  - LONG (> 800 words): Recursive split + flag for semantic refinement

### Deliverables
- `src/docforge/postprocessing/hybrid_chunking/` module
- Normalized document model with section hierarchy
- Length-based section router
- Structure-aware recursive chunker
- Storage adapter for ChunkStorage integration

### Configuration
```python
short_section_threshold: 150 words
long_section_threshold: 800 words
target_chunk_size: 500 words
max_chunk_size: 800 words
min_chunk_size: 50 words
chunk_overlap: 50 words
```

---

## Sprint 2: Semantic Refinement (Planned)

**Status:** Not Started
**Goal:** Add semantic chunking for long sections flagged in Sprint 1

### Objectives
- [ ] Implement semantic similarity-based chunk boundary refinement
- [ ] Use embeddings to detect topic shifts within long sections
- [ ] Refine chunk boundaries at semantic breakpoints
- [ ] A/B testing framework for chunk quality comparison

### Deliverables
- Semantic refinement module
- Embedding-based boundary detection
- Quality metrics and comparison tools

---

## Sprint 3: Context Enrichment (Planned)

**Status:** Not Started
**Goal:** Add contextual information to chunks for better retrieval

### Objectives
- [ ] Implement heading path context (breadcrumb)
- [ ] Add document summary context to chunks
- [ ] Implement chunk-level summaries using LLM
- [ ] Cross-reference related chunks

### Deliverables
- Context enrichment pipeline
- LLM integration for summaries
- Chunk relationship graph

---

## Sprint 4: Evaluation Framework (Planned)

**Status:** Not Started
**Goal:** Measure and optimize chunking quality

### Objectives
- [ ] Implement retrieval quality metrics
- [ ] Create test corpus with ground truth
- [ ] A/B testing different strategies
- [ ] Automated parameter tuning

### Deliverables
- Evaluation metrics module
- Test corpus and benchmarks
- Parameter optimization tools

---

## Architecture Overview

```
StandardizedDocumentOutput (MinerU)
         │
         ▼
┌─────────────────────┐
│  MinerUNormalizer   │  ← Sprint 1
└─────────────────────┘
         │
         ▼
    NormalizedDocument
    (sections, headings, paragraphs)
         │
         ▼
┌─────────────────────┐
│   SectionRouter     │  ← Sprint 1
│  (SHORT/MED/LONG)   │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ StructureAware      │  ← Sprint 1
│ RecursiveChunker    │
└─────────────────────┘
         │
         ▼
    HybridChunkResult[]
    (with semantic_candidate flags)
         │
         ▼
┌─────────────────────┐
│ SemanticRefiner     │  ← Sprint 2
│ (for flagged chunks)│
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ ContextEnricher     │  ← Sprint 3
└─────────────────────┘
         │
         ▼
    Final Chunks → ChunkStorage
```

---

## Change Log

| Date | Sprint | Change |
|------|--------|--------|
| 2026-02-03 | 1 | Sprint 1 started - Hybrid chunking pipeline |
| 2026-02-03 | 1 | Sprint 1 complete - All modules implemented |
