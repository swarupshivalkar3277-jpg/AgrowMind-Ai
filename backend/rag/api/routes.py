from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import logging
import asyncio

from auth.deps import get_current_user
from rag.services.rag_service import answer_question
from routes.marketplace import recommended_products

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = logging.getLogger("agromind.rag.api")


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    crop: str | None = Field(default=None, max_length=40)
    disease: str | None = Field(default=None, max_length=120)


@router.post("/query")
async def query_rag(payload: RAGQueryRequest, user=Depends(get_current_user)):
    logger.info("RAG request received user=%s question_chars=%s crop=%s disease=%s", user.get("email"), len(payload.question), payload.crop, payload.disease)
    try:
        result = await answer_question(payload.question, user=user, save_history=True)
    except asyncio.TimeoutError:
        logger.warning("RAG request exceeded total timeout user=%s", user.get("email"))
        result = {
            "answer": "The assistant is still warming up. Please try again shortly; diagnosis and marketplace features remain available.",
            "sources": [],
            "provider": "fallback_total_timeout",
        }
    products: list[dict] = []
    if payload.crop and payload.disease:
        try:
            products = await recommended_products(payload.crop, payload.disease, limit=6)
        except HTTPException:
            raise
        except Exception:
            products = []

    return {
        "success": True,
        "answer": result["answer"],
        "sources": result["sources"],
        "recommended_products": products,
        "provider": result.get("provider"),
    }
