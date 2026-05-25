from __future__ import annotations

import logging
from threading import Lock

from rag.config import EMBEDDING_MODEL_NAME

logger = logging.getLogger("agromind.rag.embeddings")


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
            from sentence_transformers import SentenceTransformer

            logger.info("Loading RAG embedding model=%s", EMBEDDING_MODEL_NAME)
            self._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        if not documents:
            return []
        embeddings = self.model.encode(documents, normalize_embeddings=True, batch_size=32)
        return [embedding.tolist() for embedding in embeddings]


def get_embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()

