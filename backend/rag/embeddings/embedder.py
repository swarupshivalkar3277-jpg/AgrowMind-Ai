from __future__ import annotations

import gc
import logging
import os
import time
from threading import Lock

from rag.config import EMBEDDING_MODEL_NAME

logger = logging.getLogger("agromind.rag.embeddings")
UNLOAD_EMBEDDER_AFTER_QUERY = os.getenv("RAG_UNLOAD_EMBEDDER_AFTER_QUERY", "false").lower() in {"1", "true", "yes", "on"}


class SentenceTransformerEmbedder:
    _instance: "SentenceTransformerEmbedder | None" = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = None
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    started_at = time.perf_counter()
                    logger.info("Loading RAG embedding model=%s", EMBEDDING_MODEL_NAME)
                    self._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                    logger.info(
                        "RAG embedding model loaded model=%s duration_ms=%.2f",
                        EMBEDDING_MODEL_NAME,
                        (time.perf_counter() - started_at) * 1000,
                    )
        return self._model

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def embed_text(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        if not documents:
            return []
        embeddings = self.model.encode(documents, normalize_embeddings=True, batch_size=32)
        return [embedding.tolist() for embedding in embeddings]

    def unload(self, reason: str = "cleanup") -> None:
        if self._model is None:
            return
        try:
            del self._model
        finally:
            self._model = None
            gc.collect()
            logger.info("Unloaded RAG embedding model reason=%s", reason)


def get_embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()


def cleanup_embedder(reason: str = "cleanup") -> None:
    if UNLOAD_EMBEDDER_AFTER_QUERY:
        logger.warning("Ignoring RAG_UNLOAD_EMBEDDER_AFTER_QUERY=true; embedder stays cached reason=%s", reason)
