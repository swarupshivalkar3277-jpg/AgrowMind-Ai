from __future__ import annotations

import os
from pathlib import Path

from utils.env import env_bool


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _backend_relative_path(env_name: str, default: Path) -> Path:
    configured = os.getenv(env_name)
    if not configured:
        return default
    path = Path(configured)
    return path if path.is_absolute() else BACKEND_DIR / path


KNOWLEDGE_BASE_DIR = _backend_relative_path("RAG_KNOWLEDGE_BASE_DIR", BACKEND_DIR / "knowledge_base")
VECTOR_DB_DIR = _backend_relative_path("RAG_VECTOR_DB_PATH", BACKEND_DIR / "vector_db")

COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "agromind_knowledge")
EMBEDDING_MODEL_NAME = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.2"))

LLM_PROVIDER = os.getenv("RAG_LLM_PROVIDER", "").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
RAG_REQUIRE_LLM = env_bool("RAG_REQUIRE_LLM")
