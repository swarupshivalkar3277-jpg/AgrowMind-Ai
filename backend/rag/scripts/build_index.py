from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.config import KNOWLEDGE_BASE_DIR
from rag.embeddings.embedder import get_embedder
from rag.ingestion.chunker import chunk_documents
from rag.ingestion.pdf_loader import load_pdfs
from rag.vectorstore.chroma_store import get_chroma_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("agromind.rag.build_index")


def build_index(reset: bool = True) -> dict:
    documents, failures = load_pdfs(KNOWLEDGE_BASE_DIR)
    chunks = chunk_documents(documents)
    store = get_chroma_store()

    if reset:
        store.delete_collection()

    embeddings = get_embedder().embed_documents([chunk["chunk"] for chunk in chunks])
    vectors_stored = store.add_documents(chunks, embeddings)
    summary = {
        "files_processed": len({document["source"] for document in documents}),
        "pages_loaded": len(documents),
        "chunks_created": len(chunks),
        "vectors_stored": vectors_stored,
        "failures": failures,
    }
    logger.info("RAG index build summary=%s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build AgroMind RAG ChromaDB index")
    parser.add_argument("--append", action="store_true", help="Append/upsert documents without deleting the collection first")
    args = parser.parse_args()

    summary = build_index(reset=not args.append)
    print("AgroMind RAG index build complete")
    print(f"Files processed: {summary['files_processed']}")
    print(f"Pages loaded: {summary['pages_loaded']}")
    print(f"Chunks created: {summary['chunks_created']}")
    print(f"Vectors stored: {summary['vectors_stored']}")
    print(f"Failures: {len(summary['failures'])}")
    for failure in summary["failures"]:
        print(f"- {failure['source']}: {failure['error']}")


if __name__ == "__main__":
    main()

