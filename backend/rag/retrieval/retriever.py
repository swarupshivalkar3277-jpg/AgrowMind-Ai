from functools import lru_cache

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


VECTORSTORE_DIR = "rag/vectorstore/faiss_md_index"


@lru_cache(maxsize=1)
def get_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    return FAISS.load_local(
        VECTORSTORE_DIR,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def retrieve_context(query: str, k: int = 5):
    db = get_vectorstore()
    docs = db.similarity_search(query, k=k)

    context_parts = []

    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        category = doc.metadata.get("category", "unknown")
        file_name = doc.metadata.get("file_name", "unknown")

        context_parts.append(
            f"[Source {i}]\n"
            f"File: {source}\n"
            f"Category: {category}\n"
            f"File Name: {file_name}\n"
            f"Content:\n{doc.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)
    return context, docs