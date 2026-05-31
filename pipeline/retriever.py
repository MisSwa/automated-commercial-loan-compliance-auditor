"""
pipeline/retriever.py

Provides retrieve_policy_chunks(), the single public interface for querying
the credit policy Chroma vector store.  Called by LangGraph nodes in Phase 2.
"""

from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "credit_policy"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Module-level singletons — lazy-loaded on first call
_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve_policy_chunks(query: str, n_results: int = 3) -> list[str]:
    """
    Query the credit policy vector store and return the top-n matching chunks.

    Args:
        query:     Natural-language query string (e.g. "DSCR requirement").
        n_results: Number of chunks to return (default 3).

    Returns:
        List of policy text chunks most relevant to the query.
        Returns an empty list if the collection is empty or unreachable.

    Raises:
        RuntimeError: If the Chroma store has not been built yet
                      (run pipeline/ingest.py first).
    """
    if not CHROMA_PATH.exists():
        raise RuntimeError(
            f"Chroma store not found at {CHROMA_PATH}. "
            "Run `python pipeline/ingest.py` to build it."
        )

    model = _get_model()
    collection = _get_collection()

    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count()),
    )

    documents: Optional[list[list[str]]] = results.get("documents")
    if not documents or not documents[0]:
        return []

    return documents[0]
