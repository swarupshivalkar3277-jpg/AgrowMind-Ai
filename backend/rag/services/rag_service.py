from rag.retrieval.retriever import retrieve_context


def build_rag_prompt(user_query: str, context: str) -> str:
    return f"""
You are AgroMind AI, an agriculture assistant for Indian farmers.

Use ONLY the provided knowledge base context to answer the farmer's question.

Rules:
- Give practical, farmer-friendly guidance.
- Do not invent pesticide doses, subsidy amounts, scheme deadlines, or legal rules.
- For pesticides, always advise checking the product label and local agriculture officer guidance.
- For fertilizers, recommend soil-test-based application.
- For government schemes, advise checking official portal, CSC, bank, or agriculture office.
- If context is not enough, say: "My knowledge base does not contain enough information about this."
- Answer in the same language as the user's question when possible.
- Include source file names at the end.

KNOWLEDGE BASE CONTEXT:
{context}

FARMER QUESTION:
{user_query}

ANSWER:
"""


def prepare_rag_answer(user_query: str, k: int = 5):
    context, docs = retrieve_context(user_query, k=k)
    prompt = build_rag_prompt(user_query, context)

    sources = [
        {
            "source": doc.metadata.get("source"),
            "category": doc.metadata.get("category"),
            "file_name": doc.metadata.get("file_name"),
        }
        for doc in docs
    ]

    return {
        "query": user_query,
        "prompt": prompt,
        "sources": sources,
    }


def simple_context_answer(user_query: str, docs) -> str:
    """
    Temporary fallback answer until LLM is connected.
    This returns retrieved knowledge-base content directly.
    """

    if not docs:
        return "My knowledge base does not contain enough information about this."

    answer_parts = [
        "Based on AgroMind knowledge base, here is the relevant guidance:\n"
    ]

    for i, doc in enumerate(docs, start=1):
        file_name = doc.metadata.get("file_name", "unknown")
        content = doc.page_content.strip()

        answer_parts.append(
            f"\nSource {i}: {file_name}\n"
            f"{content[:1200]}\n"
        )

    source_files = sorted(
        set(doc.metadata.get("file_name", "unknown") for doc in docs)
    )

    answer_parts.append("\nSources: " + ", ".join(source_files))

    return "\n".join(answer_parts)


async def answer_question(
    question: str,
    user: dict | None = None,
    save_history: bool = False,
    k: int = 5,
):
    """
    Async-compatible function used by rag/api/routes.py.
    Currently returns retrieval-based answer.
    Later this can call your real LLM using the generated prompt.
    """

    context, docs = retrieve_context(question, k=k)
    prompt = build_rag_prompt(question, context)

    sources = [
        {
            "source": doc.metadata.get("source"),
            "category": doc.metadata.get("category"),
            "file_name": doc.metadata.get("file_name"),
        }
        for doc in docs
    ]

    # Temporary answer without LLM.
    # Replace this with llm_service call later.
    answer = simple_context_answer(question, docs)

    return {
        "answer": answer,
        "sources": sources,
        "provider": "faiss_md_retrieval",
        "prompt": prompt,
    }
async def answer_disease_question(
    question: str,
    crop: str | None = None,
    disease: str | None = None,
    user: dict | None = None,
    save_history: bool = False,
    k: int = 5,
):
    """
    Compatibility wrapper for main.py.
    Uses the same Markdown FAISS RAG pipeline.
    """

    final_question = question

    if crop:
        final_question = f"Crop: {crop}\n{final_question}"

    if disease:
        final_question = f"Disease/Pest/Problem: {disease}\n{final_question}"

    return await answer_question(
        final_question,
        user=user,
        save_history=save_history,
        k=k,
    )


def rag_health_status():
    """
    Compatibility health check for main.py.
    """

    try:
        context, docs = retrieve_context("tomato fruit borer", k=1)

        return {
            "status": "ok",
            "provider": "faiss_md_retrieval",
            "vectorstore": "rag/vectorstore/faiss_md_index",
            "retrieval_test_docs": len(docs),
        }

    except Exception as e:
        return {
            "status": "error",
            "provider": "faiss_md_retrieval",
            "error": str(e),
        }


async def warmup_rag():
    """
    Compatibility warmup function for main.py.
    Loads FAISS index and embedding model once.
    """

    try:
        context, docs = retrieve_context("tomato fruit borer", k=1)

        return {
            "status": "warmed_up",
            "provider": "faiss_md_retrieval",
            "docs": len(docs),
        }

    except Exception as e:
        return {
            "status": "warmup_failed",
            "provider": "faiss_md_retrieval",
            "error": str(e),
        }