from __future__ import annotations

import re

from rag.config import CHUNK_OVERLAP, CHUNK_SIZE


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_document(document: dict, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[dict]:
    text = normalize_text(document.get("text", ""))
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    safe_overlap = max(0, min(chunk_overlap, chunk_size - 1))
    step = max(1, chunk_size - safe_overlap)
    chunks: list[dict] = []

    for chunk_index, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start:start + chunk_size]
        if not chunk_words:
            continue
        chunks.append(
            {
                "chunk": " ".join(chunk_words),
                "source": document.get("source", ""),
                "page": int(document.get("page", 0) or 0),
                "category": document.get("category", "general_agriculture"),
                "crop": document.get("category", "general_agriculture"),
                "chunk_index": chunk_index,
            }
        )
        if start + chunk_size >= len(words):
            break

    return chunks


def chunk_documents(documents: list[dict], chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[dict]:
    chunks: list[dict] = []
    for document in documents:
        chunks.extend(chunk_document(document, chunk_size, chunk_overlap))
    return chunks

