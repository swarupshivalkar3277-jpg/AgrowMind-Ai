from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
from pathlib import Path
from threading import Lock

from rag.config import COLLECTION_NAME, VECTOR_DB_DIR

os.environ["ANONYMIZED_TELEMETRY"] = os.getenv("ANONYMIZED_TELEMETRY", "False")
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
            from chromadb.config import Settings

            started_at = time.perf_counter()
            logger.info("Loading Chroma persistent client path=%s", self.persist_path)
            try:
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_path),
                    settings=Settings(anonymized_telemetry=False),
                )
            except Exception as exc:
                logger.warning("Chroma client init failed; recreating vector DB path=%s error=%s", self.persist_path, exc)
                self._recreate_persist_path()
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_path),
                    settings=Settings(anonymized_telemetry=False),
                )
            logger.info(
                "Chroma persistent client loaded path=%s duration_ms=%.2f",
                self.persist_path,
                (time.perf_counter() - started_at) * 1000,
            )
        return self._client

    def _recreate_persist_path(self) -> None:
        resolved = self.persist_path.resolve()
        backend_dir = Path(__file__).resolve().parents[2]
        if backend_dir not in resolved.parents and resolved != backend_dir:
            raise RuntimeError(f"Refusing to recreate Chroma path outside backend: {resolved}")
        if self.persist_path.exists():
            shutil.rmtree(self.persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)

    @property
    def collection(self):
        if self._collection is None:
            started_at = time.perf_counter()
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "Chroma collection loaded name=%s path=%s documents=%s duration_ms=%.2f",
                self.collection_name,
                self.persist_path,
                self._collection.count(),
                (time.perf_counter() - started_at) * 1000,
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
        started_at = time.perf_counter()
        if self.count_documents() == 0:
            logger.warning(
                "Chroma retrieval skipped empty collection=%s duration_ms=%.2f",
                self.collection_name,
                (time.perf_counter() - started_at) * 1000,
            )
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
        logger.info(
            "Chroma retrieval completed collection=%s requested_top_k=%s returned=%s duration_ms=%.2f",
            self.collection_name,
            top_k,
            len(matches),
            (time.perf_counter() - started_at) * 1000,
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
    global _store

    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ChromaStore()
    return _store


def chroma_status() -> dict:
    try:
        store = get_chroma_store()
        vector_documents = store.count_documents()
        return {
            "persist_path": str(store.persist_path),
            "collection_name": store.collection_name,
            "client_loaded": store._client is not None,
            "collection_loaded": store._collection is not None,
            "vector_documents": vector_documents,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Chroma status unavailable error=%s", exc)
        return {
            "persist_path": str(VECTOR_DB_DIR),
            "collection_name": COLLECTION_NAME,
            "client_loaded": False,
            "collection_loaded": False,
            "vector_documents": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }


_store: ChromaStore | None = None
_store_lock = Lock()
