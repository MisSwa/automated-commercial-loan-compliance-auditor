"""
pipeline/ingest.py

Ingests data/credit_policy.txt into a local persistent Chroma vector store.
Run from the project root:
    python pipeline/ingest.py

The script is idempotent: running it multiple times rebuilds the collection
from scratch, ensuring the store always reflects the current policy document.
"""

import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = PROJECT_ROOT / "data" / "credit_policy.txt"
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "credit_policy"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_policy(text: str) -> list[str]:
    """
    Split the credit policy into chunks by section.

    Each chunk starts at a SECTION header line (e.g. 'SECTION 1: ...') and
    runs until the next section header or the end of the document.  Sub-section
    content (1.1, 1.2 …) is kept together with its parent section so each
    chunk contains a complete, coherent policy area.
    """
    section_pattern = re.compile(r"^={10,}.*?^SECTION \d+:.*?(?=^={10,}|\Z)", re.MULTILINE | re.DOTALL)
    chunks = section_pattern.findall(text)

    if not chunks:
        # Fallback: split on double-newline paragraphs if no section markers found
        chunks = [p.strip() for p in re.split(r"\n{3,}", text) if p.strip()]

    return [c.strip() for c in chunks if len(c.strip()) > 50]


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def ingest() -> None:
    print(f"Loading policy from: {POLICY_PATH}")
    if not POLICY_PATH.exists():
        raise FileNotFoundError(f"Credit policy file not found: {POLICY_PATH}")

    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    chunks = chunk_policy(policy_text)
    print(f"Split into {len(chunks)} chunks")

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    print(f"Connecting to Chroma at: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Drop and recreate for idempotency
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Dropped existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )

    print(f"Ingested {collection.count()} chunks into collection '{COLLECTION_NAME}'")
    print("Done.")


if __name__ == "__main__":
    ingest()
