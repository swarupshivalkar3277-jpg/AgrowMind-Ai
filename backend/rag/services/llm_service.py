import os
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger("agromind.rag.llm")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


LLM_ENABLED = _env_bool("LLM_ENABLED", default=False)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))


async def generate_llm_answer(prompt: str) -> Optional[str]:
    if not LLM_ENABLED:
        logger.info("LLM disabled by LLM_ENABLED=false")
        return None

    if not LLM_BASE_URL or not LLM_API_KEY or not LLM_MODEL:
        logger.warning(
            "LLM config missing. LLM_BASE_URL=%s LLM_API_KEY_present=%s LLM_MODEL=%s",
            bool(LLM_BASE_URL),
            bool(LLM_API_KEY),
            bool(LLM_MODEL),
        )
        return None

    url = f"{LLM_BASE_URL}/chat/completions"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are AgroMind AI, an agriculture assistant for Indian farmers. "
                    "Use only the provided knowledge-base context. "
                    "Give practical, safe, farmer-friendly answers."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.exception("LLM generation failed: %s", e)
        return None