from pathlib import Path
from langchain_core.documents import Document


def load_markdown_files(knowledge_base_dir: str):
    docs = []
    root = Path(knowledge_base_dir)

    if not root.exists():
        print(f"Knowledge base folder not found: {root}")
        return docs

    md_files = list(root.rglob("*.md"))

    for file_path in md_files:
        try:
            text = file_path.read_text(encoding="utf-8").strip()

            if not text:
                print(f"Skipping empty markdown file: {file_path}")
                continue

            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": str(file_path),
                        "file_name": file_path.name,
                        "file_type": "markdown",
                        "category": str(file_path.parent.relative_to(root)),
                    },
                )
            )

        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="utf-8-sig").strip()

                if not text:
                    print(f"Skipping empty markdown file: {file_path}")
                    continue

                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(file_path),
                            "file_name": file_path.name,
                            "file_type": "markdown",
                            "category": str(file_path.parent.relative_to(root)),
                        },
                    )
                )

            except Exception as e:
                print(f"Failed to load markdown file {file_path}: {e}")

        except Exception as e:
            print(f"Failed to load markdown file {file_path}: {e}")

    print(f"Markdown ingestion completed files={len(md_files)} documents={len(docs)}")
    return docs