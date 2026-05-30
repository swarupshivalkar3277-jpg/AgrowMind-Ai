from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


VECTORSTORE_DIR = "rag/vectorstore/faiss_md_index"


def search(query: str, k: int = 5):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    db = FAISS.load_local(
        VECTORSTORE_DIR,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    results = db.similarity_search(query, k=k)

    print("\n" + "=" * 100)
    print("QUERY:", query)
    print("=" * 100)

    for i, doc in enumerate(results, start=1):
        print(f"\n--- RESULT {i} ---")
        print("SOURCE:", doc.metadata.get("source"))
        print("CATEGORY:", doc.metadata.get("category"))
        print("FILE:", doc.metadata.get("file_name"))
        print("-" * 80)
        print(doc.page_content[:800])


if __name__ == "__main__":
    search("How to manage tomato fruit borer?")
    search("What is PM Kisan eligibility?")
    search("How to use copper oxychloride safely?")
    search("What causes calcium deficiency in tomato?")
    search("What are pre-emergence herbicides?")