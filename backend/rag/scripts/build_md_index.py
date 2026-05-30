from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from rag.ingestion.markdown_loader import load_markdown_files


KNOWLEDGE_BASE_DIR = "knowledge_base"
VECTORSTORE_DIR = "rag/vectorstore/faiss_md_index"


def main():
    print("========== STEP 1: LOADING MARKDOWN FILES ==========")
    docs = load_markdown_files(KNOWLEDGE_BASE_DIR)

    if not docs:
        raise ValueError("No markdown documents found in knowledge_base folder.")

    print("Markdown documents loaded:", len(docs))

    print("\n========== STEP 2: CHUNKING ==========")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=[
            "\n# ",
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    chunks = splitter.split_documents(docs)
    print("Chunks created:", len(chunks))

    print("\n========== STEP 3: INITIALIZING EMBEDDER ==========")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print("\n========== STEP 4: CREATING FAISS INDEX ==========")
    db = FAISS.from_documents(chunks, embeddings)

    Path(VECTORSTORE_DIR).mkdir(parents=True, exist_ok=True)
    db.save_local(VECTORSTORE_DIR)

    print("\n========== DONE ==========")
    print("Markdown FAISS index saved at:", VECTORSTORE_DIR)


if __name__ == "__main__":
    main()