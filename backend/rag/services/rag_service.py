from __future__ import annotations

import logging
import gc
import asyncio
import os
import time
from datetime import datetime, timezone

from fastapi import HTTPException

from database.mongodb import db
from rag.embeddings.embedder import cleanup_embedder
from rag.retrieval.retriever import get_retriever
from rag.services.llm_service import get_llm_service
from rag.vectorstore.chroma_store import get_chroma_store

logger = logging.getLogger("agromind.rag.service")
RAG_RETRIEVAL_TIMEOUT_SECONDS = max(3, int(os.getenv("RAG_RETRIEVAL_TIMEOUT_SECONDS", "12")))
RAG_GENERATION_TIMEOUT_SECONDS = max(5, int(os.getenv("RAG_GENERATION_TIMEOUT_SECONDS", "35")))
RAG_TOTAL_TIMEOUT_SECONDS = max(10, int(os.getenv("RAG_TOTAL_TIMEOUT_SECONDS", "45")))
RAG_CONCURRENCY = max(1, int(os.getenv("RAG_CONCURRENCY", "1")))
rag_semaphore = asyncio.Semaphore(RAG_CONCURRENCY)


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
        started_at = time.perf_counter()
        clean_question = question.strip()
        if not clean_question:
            raise HTTPException(status_code=400, detail="Question is required")

        try:
            async with rag_semaphore:
                chunks = await asyncio.wait_for(
                    asyncio.to_thread(self.retriever.retrieve, clean_question),
                    timeout=RAG_RETRIEVAL_TIMEOUT_SECONDS,
                )
            sources = unique_sources(chunks)
            if not sources:
                return self.fallback_response(
                    "The AgroMind knowledge index is not ready yet. I can still help with general crop safety: isolate affected leaves, avoid spraying during wind or heat, use clean tools, and confirm treatment with a local agriculture officer.",
                    provider="fallback_empty_index",
                )

            generated = await asyncio.wait_for(
                self.llm.generate_answer(clean_question, chunks),
                timeout=RAG_GENERATION_TIMEOUT_SECONDS,
            )
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
        except asyncio.TimeoutError:
            logger.warning(
                "RAG request timed out question_chars=%s duration_ms=%.2f",
                len(clean_question),
                (time.perf_counter() - started_at) * 1000,
            )
            return self.fallback_response(
                "The assistant is warming up or the knowledge index is slow right now. Please try again shortly. For urgent crop care, remove badly affected leaves, avoid overwatering, and use only label-approved treatments.",
                provider="fallback_timeout",
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception("RAG request failed")
            return self.fallback_response(
                "The assistant is temporarily unavailable. Your prediction can still be used with the disease recommendations shown on the diagnosis page.",
                provider="fallback_error",
            )
        finally:
            cleanup_embedder(reason="after_rag_query")
            gc.collect()
            logger.info("RAG request finished duration_ms=%.2f", (time.perf_counter() - started_at) * 1000)

    def fallback_response(self, answer: str, provider: str) -> dict:
        return {
            "answer": answer,
            "sources": [],
            "chunks": [],
            "provider": provider,
        }

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
    return await asyncio.wait_for(
        get_rag_service().answer_question(question, user=user, save_history=save_history),
        timeout=RAG_TOTAL_TIMEOUT_SECONDS,
    )


async def answer_disease_question(crop: str, disease: str, user: dict | None = None) -> dict:
    readable_disease = (disease or "crop disease").replace("_", " ")
    query = (
        f"Explain {crop.title()} {readable_disease} including symptoms, causes, prevention, "
        "organic treatment, chemical treatment, and farmer safety advice."
    )
    return await answer_question(query, user=user, save_history=False)


async def rag_health_status() -> dict:
    try:
        count = await asyncio.wait_for(
            asyncio.to_thread(get_chroma_store().count_documents),
            timeout=RAG_RETRIEVAL_TIMEOUT_SECONDS,
        )
        return {
            "success": True,
            "ready": count > 0,
            "vector_documents": count,
            "timeouts": {
                "retrieval_seconds": RAG_RETRIEVAL_TIMEOUT_SECONDS,
                "generation_seconds": RAG_GENERATION_TIMEOUT_SECONDS,
                "total_seconds": RAG_TOTAL_TIMEOUT_SECONDS,
            },
            "concurrency": RAG_CONCURRENCY,
        }
    except Exception as exc:
        logger.exception("RAG health check failed")
        return {
            "success": False,
            "ready": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
