"""Semantic chunk retrieval with configurable top-k, similarity threshold, and neighbor expansion.

Tuning levers
-------------
top_k               Candidate set size. Recommended values: 5, 8, 10, 20.
                    Start at 10; increase if answers feel incomplete, decrease if
                    the LLM context becomes noisy. Quality typically plateaus at ~10
                    for single-document queries and ~15-20 for cross-document ones.

similarity_threshold Cosine similarity floor (0.0 – 1.0).
                    0.0  = no filter (all chunks ranked, top-k returned).
                    0.3  = removes clearly off-topic chunks.
                    0.5  = stricter; useful when you have many documents and want
                           precision over recall.
                    Start at 0.0 and raise incrementally until you see irrelevant
                    hits drop without losing good ones.

neighbor_window     After scoring, also fetch ±window adjacent chunks from the same
                    document so key context just outside a chunk boundary is included.
                    0 = disabled, 1 = ±1 chunk (recommended default), 2 = ±2 chunks.

Environment overrides (take precedence over constructor defaults)
-----------------------------------------------------------------
RAG__TOP_K                 integer  (default 10)
RAG__SIMILARITY_THRESHOLD  float    (default 0.0)
RAG__NEIGHBOR_WINDOW       integer  (default 1)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Documented tuning options ────────────────────────────────────────────────
TOP_K_OPTIONS = [5, 8, 10, 20]
SIMILARITY_THRESHOLD_OPTIONS = [0.0, 0.3, 0.4, 0.5]
NEIGHBOR_WINDOW_OPTIONS = [0, 1, 2]


class ChunkRetriever:
    """Retrieve chunks by semantic similarity with ±N neighbor expansion."""

    def __init__(
        self,
        chunk_storage=None,
        embedding_manager=None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        neighbor_window: int = 1,
        db_path: str = "data/brain_mvp.db",
    ):
        from storage.chunk_storage import ChunkStorage
        from docforge.rag.embeddings import EmbeddingManager

        self.chunk_storage = chunk_storage or ChunkStorage(db_path=db_path)
        self.embedding_manager = embedding_manager or EmbeddingManager()

        # Env vars override constructor defaults so operators can tune without
        # redeploying code
        self.top_k = int(os.getenv("RAG__TOP_K", top_k))
        self.similarity_threshold = float(os.getenv("RAG__SIMILARITY_THRESHOLD", similarity_threshold))
        self.neighbor_window = int(os.getenv("RAG__NEIGHBOR_WINDOW", neighbor_window))

    # ── Public interface ──────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        neighbor_window: Optional[int] = None,
        doc_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve the most relevant chunks for *query*.

        Parameters
        ----------
        query                Natural language query string.
        top_k                Override instance default (see module docstring).
        similarity_threshold Override instance default (cosine, 0–1).
        neighbor_window      Override instance default (±N adjacent chunks).
        doc_filter           Restrict search to these doc_uuid values.

        Returns
        -------
        {
          "query":                 str,
          "top_k":                 int,
          "similarity_threshold":  float,
          "neighbor_window":       int,
          "top_k_options":         [5, 8, 10, 20],   # for UI tuning controls
          "hits": [                                   # top-k scored chunks
            {"chunk": {...}, "score": float, "rank": int}
          ],
          "context_chunks": [    # hits + neighbors, deduped, doc/index order
            {"chunk": {...}, "score": float, "is_neighbor": bool}
          ],
          "total_candidates":      int,
          "total_after_threshold": int,
        }
        """
        k = top_k if top_k is not None else self.top_k
        threshold = similarity_threshold if similarity_threshold is not None else self.similarity_threshold
        window = neighbor_window if neighbor_window is not None else self.neighbor_window

        # 1. Embed the query synchronously (SentenceTransformer.encode is sync)
        query_vec = np.array(self.embedding_manager.embedder.encode([query])[0], dtype=np.float32)

        # 2. Load all stored chunk embeddings (optionally doc-scoped)
        rows = self.chunk_storage.get_embeddings_for_search(doc_uuids=doc_filter)
        if not rows:
            logger.warning(
                "No embedded chunks found – documents may not have been processed yet "
                "or embeddings were not generated during Stage 4."
            )
            return self._empty_result(query, k, threshold, window)

        # 3. Build matrix and compute cosine similarity in one shot
        ids = [r["chunk_id"] for r in rows]
        doc_uuids = [r["doc_uuid"] for r in rows]
        chunk_indices = [r["chunk_index"] for r in rows]
        matrix = np.array([r["embedding"] for r in rows], dtype=np.float32)  # (N, D)

        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        matrix_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
        scores = (matrix_norms @ query_norm).tolist()           # list[float], length N

        total_candidates = len(scores)

        # 4. Apply similarity threshold
        filtered = [
            (ids[i], doc_uuids[i], chunk_indices[i], scores[i])
            for i in range(total_candidates)
            if scores[i] >= threshold
        ]
        total_after_threshold = len(filtered)

        # 5. Sort descending and take top-k
        filtered.sort(key=lambda x: x[3], reverse=True)
        top = filtered[:k]

        # 6. Fetch full chunk data for hits
        hits = []
        for rank, (chunk_id, _doc_uuid, _chunk_idx, score) in enumerate(top):
            chunk = self.chunk_storage.get_chunk_by_id(chunk_id)
            if chunk:
                hits.append({"chunk": chunk, "score": round(score, 4), "rank": rank + 1})

        # 7. Expand with ±window neighbors, preserving document reading order
        seen_ids = {h["chunk"]["chunk_id"] for h in hits}
        context_chunks = [
            {"chunk": h["chunk"], "score": h["score"], "is_neighbor": False}
            for h in hits
        ]

        if window > 0:
            for _chunk_id, doc_uuid, chunk_index, _score in top:
                neighbors = self.chunk_storage.get_neighbor_chunks(doc_uuid, chunk_index, window)
                for neighbor in neighbors:
                    nid = neighbor["chunk_id"]
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        context_chunks.append({"chunk": neighbor, "score": 0.0, "is_neighbor": True})

        # Sort by document then sequential position for coherent LLM context
        context_chunks.sort(key=lambda x: (x["chunk"]["doc_uuid"], x["chunk"]["chunk_index"]))

        logger.info(
            "Retrieval | k=%d threshold=%.2f window=%d | "
            "candidates=%d after_threshold=%d hits=%d context=%d",
            k, threshold, window,
            total_candidates, total_after_threshold, len(hits), len(context_chunks),
        )

        return {
            "query": query,
            "top_k": k,
            "similarity_threshold": threshold,
            "neighbor_window": window,
            "top_k_options": TOP_K_OPTIONS,
            "similarity_threshold_options": SIMILARITY_THRESHOLD_OPTIONS,
            "neighbor_window_options": NEIGHBOR_WINDOW_OPTIONS,
            "hits": hits,
            "context_chunks": context_chunks,
            "total_candidates": total_candidates,
            "total_after_threshold": total_after_threshold,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _empty_result(query: str, k: int, threshold: float, window: int) -> Dict[str, Any]:
        return {
            "query": query,
            "top_k": k,
            "similarity_threshold": threshold,
            "neighbor_window": window,
            "top_k_options": TOP_K_OPTIONS,
            "similarity_threshold_options": SIMILARITY_THRESHOLD_OPTIONS,
            "neighbor_window_options": NEIGHBOR_WINDOW_OPTIONS,
            "hits": [],
            "context_chunks": [],
            "total_candidates": 0,
            "total_after_threshold": 0,
        }


# ── Module-level singleton (avoids reloading the ~90 MB embedding model) ─────
_retriever: Optional[ChunkRetriever] = None


def get_retriever(db_path: str = "data/brain_mvp.db") -> ChunkRetriever:
    """Return (or create) the shared ChunkRetriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = ChunkRetriever(db_path=db_path)
    return _retriever
