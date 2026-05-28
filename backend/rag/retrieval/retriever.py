from __future__ import annotations

import logging
import time
from threading import Lock

from rag.config import DEFAULT_TOP_K, MIN_SIMILARITY
from rag.embeddings.embedder import get_embedder
from rag.vectorstore.chroma_store import get_chroma_store

logger = logging.getLogger("agromind.rag.retriever")


class Retriever:
    def __init__(self):
        self.embedder = get_embedder()
        self.store = get_chroma_store()

    def retrieve(self, question: str, top_k: int = DEFAULT_TOP_K, min_similarity: float = MIN_SIMILARITY) -> list[dict]:
        started_at = time.perf_counter()
        query_embedding = self.embedder.embed_text(question)
        matches = self.store.search(query_embedding, top_k=top_k)
        if not matches:
            logger.warning(
                "RAG retrieval returned no chunks; vector store may be empty duration_ms=%.2f",
                (time.perf_counter() - started_at) * 1000,
            )
            return []

        strong_matches = [match for match in matches if float(match.get("score", 0)) >= min_similarity]
        if strong_matches:
            logger.info(
                "RAG retrieval completed question_chars=%s returned=%s strong=%s best_score=%s duration_ms=%.2f",
                len(question),
                min(len(strong_matches), top_k),
                True,
                strong_matches[0].get("score"),
                (time.perf_counter() - started_at) * 1000,
            )
            return strong_matches[:top_k]

        logger.info(
            "RAG retrieval below threshold; returning fallback top_k question=%s best_score=%s threshold=%s duration_ms=%.2f",
            question[:120],
            matches[0].get("score"),
            min_similarity,
            (time.perf_counter() - started_at) * 1000,
        )
        return matches[:top_k]


def get_retriever() -> Retriever:
    global _retriever

    if _retriever is None:
        with _retriever_lock:
            if _retriever is None:
                _retriever = Retriever()
    return _retriever


_retriever: Retriever | None = None
_retriever_lock = Lock()
