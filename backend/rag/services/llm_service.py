from __future__ import annotations

import logging
import os

import httpx
from fastapi import HTTPException

from rag.config import GEMINI_MODEL, LLM_PROVIDER, OPENAI_MODEL, RAG_REQUIRE_LLM
from rag.prompts.agriculture_prompt import build_agriculture_prompt

logger = logging.getLogger("agromind.rag.llm")
RAG_LLM_HTTP_TIMEOUT_SECONDS = max(5, int(os.getenv("RAG_LLM_HTTP_TIMEOUT_SECONDS", "30")))
RAG_LLM_MAX_OUTPUT_TOKENS = max(256, int(os.getenv("RAG_LLM_MAX_OUTPUT_TOKENS", "700")))
RAG_PROMPT_MAX_CHARS = max(2000, int(os.getenv("RAG_PROMPT_MAX_CHARS", "6000")))


class LLMService:
    def provider(self) -> str:
        if LLM_PROVIDER:
            return LLM_PROVIDER
        if os.getenv("GEMINI_API_KEY"):
            return "gemini"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        return "extractive"

    async def generate_answer(self, question: str, chunks: list[dict]) -> dict:
        prompt = build_agriculture_prompt(question, chunks[:3])
        if len(prompt) > RAG_PROMPT_MAX_CHARS:
            prompt = prompt[:RAG_PROMPT_MAX_CHARS]
        provider = self.provider()

        if provider == "gemini":
            return {"answer": await self._generate_with_gemini(prompt), "provider": provider}
        if provider == "openai":
            return {"answer": await self._generate_with_openai(prompt), "provider": provider}
        if RAG_REQUIRE_LLM:
            raise HTTPException(status_code=503, detail="RAG LLM provider is not configured")

        logger.warning("No RAG LLM key configured; using extractive grounded fallback")
        return {"answer": self._extractive_fallback(question, chunks), "provider": "extractive"}

    async def _generate_with_gemini(self, prompt: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": RAG_LLM_MAX_OUTPUT_TOKENS},
        }
        logger.info("Gemini request started model=%s prompt_chars=%s", GEMINI_MODEL, len(prompt))
        try:
            async with httpx.AsyncClient(timeout=RAG_LLM_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, params={"key": api_key}, json=payload)
        except httpx.RequestError as exc:
            logger.exception("Gemini request failed before response model=%s", GEMINI_MODEL)
            raise HTTPException(status_code=502, detail="Gemini is unreachable from the backend") from exc
        if response.status_code >= 400:
            logger.error("Gemini RAG request failed status=%s body=%s", response.status_code, response.text[:500])
            raise HTTPException(status_code=502, detail="Gemini RAG generation failed")

        data = response.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        answer = "".join(part.get("text", "") for part in parts).strip()
        if not answer:
            raise HTTPException(status_code=502, detail="Gemini returned an empty RAG answer")
        logger.info("Gemini response received model=%s answer_chars=%s", GEMINI_MODEL, len(answer))
        return answer

    async def _generate_with_openai(self, prompt: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

        payload = {
            "model": OPENAI_MODEL,
            "input": prompt,
            "temperature": 0.2,
            "max_output_tokens": RAG_LLM_MAX_OUTPUT_TOKENS,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=RAG_LLM_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
        if response.status_code >= 400:
            logger.error("OpenAI RAG request failed status=%s body=%s", response.status_code, response.text[:500])
            raise HTTPException(status_code=502, detail="OpenAI RAG generation failed")

        data = response.json()
        answer = data.get("output_text")
        if answer:
            return answer.strip()

        output = data.get("output", [])
        text_parts: list[str] = []
        for item in output:
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text_parts.append(content.get("text", ""))
        answer = "\n".join(part for part in text_parts if part).strip()
        if not answer:
            raise HTTPException(status_code=502, detail="OpenAI returned an empty RAG answer")
        return answer

    def _extractive_fallback(self, question: str, chunks: list[dict]) -> str:
        if not chunks:
            return "The knowledge base has no indexed sources for this question, so AgroMind AI cannot provide a grounded answer."

        citations = ", ".join(
            f"{chunk.get('source', 'Unknown source')} page {chunk.get('page', 'N/A')}"
            for chunk in chunks[:3]
        )
        evidence = "\n\n".join(chunk.get("text", "")[:700] for chunk in chunks[:3])
        return (
            "1. Summary\n"
            "The retrieved agricultural references contain the following relevant guidance. Review the cited pages before field application.\n\n"
            "2. Symptoms\n"
            "See the cited context for crop-specific symptom descriptions.\n\n"
            "3. Causes\n"
            "The likely causes should be confirmed from the cited source material and local field conditions.\n\n"
            "4. Prevention\n"
            "Use resistant/healthy planting material, sanitation, field monitoring, proper spacing, and moisture management when supported by the cited documents.\n\n"
            "5. Organic Treatment\n"
            "Prefer approved biological controls and cultural practices when supported by the cited documents.\n\n"
            "6. Chemical Treatment\n"
            "Use only locally approved pesticides/fungicides at label rates, and confirm recommendations with an agriculture officer.\n\n"
            "7. Farmer Safety Advice\n"
            "Wear gloves, mask, eye protection, and avoid spraying in windy conditions. Follow label pre-harvest intervals.\n\n"
            f"Relevant context:\n{evidence}\n\nSources: {citations}"
        )


def get_llm_service() -> LLMService:
    return LLMService()
