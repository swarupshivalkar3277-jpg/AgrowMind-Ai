from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from rag.config import COLLECTION_NAME, VECTOR_DB_DIR

logger = logging.getLogger("agromind.rag.vectorstore")


class ChromaStore:
    def __init__(self, persist_path: Path = VECTOR_DB_DIR, collection_name: str = COLLECTION_NAME):
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=str(self.persist_path))
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _document_id(self, document: dict) -> str:
        raw = "|".join(
            [
                str(document.get("source", "")),
                str(document.get("page", "")),
                str(document.get("category", "")),
                str(document.get("chunk_index", "")),
                str(document.get("chunk", ""))[:80],
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def add_documents(self, documents: list[dict], embeddings: list[list[float]]) -> int:
        if not documents:
            return 0
        if len(documents) != len(embeddings):
            raise ValueError("documents and embeddings must have the same length")

        ids = [self._document_id(document) for document in documents]
        metadatas = [
            {
                "source": document.get("source", ""),
                "page": int(document.get("page", 0) or 0),
                "category": document.get("category", "general_agriculture"),
                "crop": document.get("crop", document.get("category", "general_agriculture")),
                "chunk_index": int(document.get("chunk_index", 0) or 0),
            }
            for document in documents
        ]
        self.collection.upsert(
            ids=ids,
            documents=[document.get("chunk", "") for document in documents],
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Stored RAG vectors count=%s collection=%s", len(documents), self.collection_name)
        return len(documents)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        if self.count_documents() == 0:
            return []
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        matches: list[dict] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            similarity = max(0.0, 1.0 - float(distance))
            matches.append(
                {
                    "text": text,
                    "source": metadata.get("source", ""),
                    "page": metadata.get("page", 0),
                    "category": metadata.get("category", ""),
                    "crop": metadata.get("crop", ""),
                    "score": similarity,
                }
            )
        return matches

    def delete_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            logger.info("RAG collection did not exist before delete name=%s", self.collection_name)
        self._collection = None

    def count_documents(self) -> int:
        return int(self.collection.count())


def get_chroma_store() -> ChromaStore:
    return ChromaStore()

