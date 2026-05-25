from __future__ import annotations


SYSTEM_PROMPT = """You are AgroMind AI, an agricultural assistant.

Use ONLY the provided context.

Do not invent information.

If context is insufficient, clearly state that.

Provide:

1. Summary
2. Symptoms
3. Causes
4. Prevention
5. Organic Treatment
6. Chemical Treatment
7. Farmer Safety Advice

Always cite sources."""


def build_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        parts.append(
            "\n".join(
                [
                    f"[Source {index}] {chunk.get('source', 'Unknown source')} page {chunk.get('page', 'N/A')}",
                    chunk.get("text", ""),
                ]
            )
        )
    return "\n\n".join(parts)


def build_agriculture_prompt(question: str, chunks: list[dict]) -> str:
    return "\n\n".join(
        [
            SYSTEM_PROMPT,
            "Context:",
            build_context(chunks) or "No context was retrieved.",
            "User question:",
            question,
            "Answer with citations using the source filename and page number.",
        ]
    )

