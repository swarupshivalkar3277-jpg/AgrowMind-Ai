from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.deps import get_current_user
from rag.services.rag_service import answer_question
from routes.marketplace import recommended_products

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    crop: str | None = Field(default=None, max_length=40)
    disease: str | None = Field(default=None, max_length=120)


@router.post("/query")
async def query_rag(payload: RAGQueryRequest, user=Depends(get_current_user)):
    result = await answer_question(payload.question, user=user, save_history=True)
    products: list[dict] = []
    if payload.crop and payload.disease:
        try:
            products = await recommended_products(payload.crop, payload.disease, limit=6)
        except HTTPException:
            raise
        except Exception:
            products = []

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "recommended_products": products,
        "provider": result.get("provider"),
    }

