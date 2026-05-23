from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagConfig:
    embedding_model: str = "future-embedding-model"
    vector_store: str = "chromadb"
    supported_languages: tuple[str, ...] = ("en", "hi", "mr")


def get_rag_config() -> RagConfig:
    return RagConfig()
