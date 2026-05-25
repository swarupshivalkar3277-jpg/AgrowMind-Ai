from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from rag.config import KNOWLEDGE_BASE_DIR

logger = logging.getLogger("agromind.rag.ingestion.pdf_loader")


def _extract_with_pymupdf(pdf_path: Path) -> list[dict]:
    import fitz

    pages: list[dict] = []
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if not text:
                logger.info("Skipping empty PDF page source=%s page=%s", pdf_path.name, index)
                continue
            pages.append({"text": text, "page": index})
    return pages


def _extract_with_pypdf(pdf_path: Path) -> list[dict]:
    from pypdf import PdfReader

    pages: list[dict] = []
    reader = PdfReader(str(pdf_path))
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            logger.info("Skipping empty PDF page source=%s page=%s", pdf_path.name, index)
            continue
        pages.append({"text": text, "page": index})
    return pages


def pdf_category(pdf_path: Path, knowledge_base_dir: Path) -> str:
    try:
        relative = pdf_path.relative_to(knowledge_base_dir)
    except ValueError:
        return "general_agriculture"
    return relative.parts[0] if len(relative.parts) > 1 else "general_agriculture"


def iter_pdf_files(knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR) -> Iterable[Path]:
    if not knowledge_base_dir.exists():
        logger.warning("Knowledge base directory does not exist: %s", knowledge_base_dir)
        return []
    return sorted(path for path in knowledge_base_dir.rglob("*.pdf") if path.is_file())


def load_pdf(pdf_path: Path, knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR) -> tuple[list[dict], str | None]:
    category = pdf_category(pdf_path, knowledge_base_dir)
    try:
        try:
            extracted_pages = _extract_with_pymupdf(pdf_path)
        except ImportError:
            extracted_pages = _extract_with_pypdf(pdf_path)
    except Exception as exc:
        logger.exception("Failed to read PDF source=%s category=%s", pdf_path, category)
        return [], str(exc)

    documents = [
        {
            "text": page["text"],
            "source": pdf_path.name,
            "page": page["page"],
            "category": category,
        }
        for page in extracted_pages
    ]
    return documents, None


def load_pdfs(knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR) -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    failures: list[dict] = []

    for pdf_path in iter_pdf_files(knowledge_base_dir):
        page_documents, error = load_pdf(pdf_path, knowledge_base_dir)
        if error:
            failures.append({"source": str(pdf_path), "error": error})
            continue
        documents.extend(page_documents)

    logger.info(
        "PDF ingestion completed files=%s pages=%s failures=%s",
        len(list(iter_pdf_files(knowledge_base_dir))),
        len(documents),
        len(failures),
    )
    return documents, failures

