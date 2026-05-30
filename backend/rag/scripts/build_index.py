from __future__ import annotations

import argparse
import logging
import sys
import time
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("agromind.rag.build_index")


def build_index(reset: bool = True) -> dict:
    start_time = time.time()

    print("\n========== STEP 1: LOADING PDFS ==========\n")

    documents, failures = load_pdfs(KNOWLEDGE_BASE_DIR)

    print(f"Documents loaded: {len(documents)}")
    print(f"Failures: {len(failures)}")

    print("\n========== STEP 2: CHUNKING ==========\n")

    chunks = chunk_documents(documents)

    print(f"Chunks created: {len(chunks)}")

    if not chunks:
        raise RuntimeError(
            "No chunks were created. Check PDF extraction and chunker configuration."
        )

    print("\n========== STEP 3: INITIALIZING CHROMA ==========\n")

    store = get_chroma_store()

    print("Chroma store initialized")

    if reset:
        print("Resetting collection...")
        store.delete_collection()
        print("Collection reset complete")

    print("\n========== STEP 4: INITIALIZING EMBEDDER ==========\n")

    embedder = get_embedder()

    print("Embedder initialized")

    texts = [chunk["chunk"] for chunk in chunks]

    print(f"Texts to embed: {len(texts)}")

    print("\n========== STEP 5: GENERATING EMBEDDINGS ==========\n")

    embed_start = time.time()

    embeddings = embedder.embed_documents(texts)

    embed_time = time.time() - embed_start

    print(f"Embeddings generated: {len(embeddings)}")
    print(f"Embedding time: {embed_time:.2f} sec")

    print("\n========== STEP 6: STORING IN CHROMA ==========\n")

    store_start = time.time()

    vectors_stored = store.add_documents(chunks, embeddings)

    store_time = time.time() - store_start

    print(f"Vectors stored: {vectors_stored}")
    print(f"Store time: {store_time:.2f} sec")

    total_time = time.time() - start_time

    summary = {
        "files_processed": len({doc["source"] for doc in documents}),
        "pages_loaded": len(documents),
        "chunks_created": len(chunks),
        "vectors_stored": vectors_stored,
        "failures": failures,
        "total_time_sec": round(total_time, 2),
    }

    logger.info("RAG index build summary=%s", summary)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build AgroMind RAG ChromaDB index"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild collection before indexing",
    )

    args = parser.parse_args()

    try:
        summary = build_index(reset=args.reset)

        print("\n========== BUILD COMPLETE ==========\n")

        print(f"Files processed : {summary['files_processed']}")
        print(f"Pages loaded    : {summary['pages_loaded']}")
        print(f"Chunks created  : {summary['chunks_created']}")
        print(f"Vectors stored  : {summary['vectors_stored']}")
        print(f"Failures        : {len(summary['failures'])}")
        print(f"Total time      : {summary['total_time_sec']} sec")

        if summary["failures"]:
            print("\nFailures:")
            for failure in summary["failures"]:
                print(f"- {failure['source']}: {failure['error']}")

    except Exception as exc:
        logger.exception("Index build failed")
        print(f"\nERROR: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()