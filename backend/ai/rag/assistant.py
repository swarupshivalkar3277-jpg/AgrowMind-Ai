from __future__ import annotations


class RagAssistantNotReady(RuntimeError):
    pass


async def answer_farmer_question(*, question: str, language: str = "en") -> dict:
    raise RagAssistantNotReady(
        "RAG assistant architecture is prepared, but LangChain/ChromaDB pipelines are not implemented yet."
    )
