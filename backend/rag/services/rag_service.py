from __future__ import annotations

import logging
import gc
from datetime import datetime, timezone

from fastapi import HTTPException

from database.mongodb import db
from rag.embeddings.embedder import cleanup_embedder
from rag.retrieval.retriever import get_retriever
from rag.services.llm_service import get_llm_service

logger = logging.getLogger("agromind.rag.service")


def unique_sources(chunks: list[dict]) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    sources: list[dict] = []
    for chunk in chunks:
        key = (chunk.get("source", ""), int(chunk.get("page", 0) or 0))
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source": key[0], "page": key[1]})
    return sources


def ensure_answer_citations(answer: str, sources: list[dict]) -> str:
    if not sources:
        return answer
    source_lines = [f"Source: {source['source']} page {source['page']}" for source in sources]
    if all(line.lower() in answer.lower() for line in source_lines[:2]):
        return answer
    return f"{answer.rstrip()}\n\n" + "\n".join(source_lines)


class RAGService:
    def __init__(self):
        self.retriever = get_retriever()
        self.llm = get_llm_service()

    async def answer_question(self, question: str, user: dict | None = None, save_history: bool = True) -> dict:
        clean_question = question.strip()
        if not clean_question:
            raise HTTPException(status_code=400, detail="Question is required")

        try:
            chunks = self.retriever.retrieve(clean_question)
            sources = unique_sources(chunks)
            if not sources:
                raise HTTPException(status_code=503, detail="RAG knowledge index is empty. Run rag/scripts/build_index.py first.")

            generated = await self.llm.generate_answer(clean_question, chunks)
            answer = ensure_answer_citations(generated["answer"], sources)
            response = {
                "answer": answer,
                "sources": sources,
                "chunks": chunks,
                "provider": generated["provider"],
            }
            if save_history and user:
                await self.save_chat(user, clean_question, response)
            return response
        finally:
            cleanup_embedder(reason="after_rag_query")
            gc.collect()

    async def save_chat(self, user: dict, question: str, response: dict) -> None:
        try:
            await db.rag_chats.insert_one(
                {
                    "user_id": str(user["_id"]),
                    "email": user.get("email"),
                    "question": question,
                    "answer": response["answer"],
                    "sources": response["sources"],
                    "provider": response.get("provider"),
                    "created_at": datetime.now(timezone.utc),
                }
            )
        except Exception:
            logger.exception("Failed to store RAG chat history user=%s", user.get("email"))


def get_rag_service() -> RAGService:
    return RAGService()


async def answer_question(question: str, user: dict | None = None, save_history: bool = True) -> dict:
    return await get_rag_service().answer_question(question, user=user, save_history=save_history)


async def answer_disease_question(crop: str, disease: str, user: dict | None = None) -> dict:
    readable_disease = (disease or "crop disease").replace("_", " ")
    query = (
        f"Explain {crop.title()} {readable_disease} including symptoms, causes, prevention, "
        "organic treatment, chemical treatment, and farmer safety advice."
    )
    return await answer_question(query, user=user, save_history=False)
