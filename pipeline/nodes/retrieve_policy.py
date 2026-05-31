"""
pipeline/nodes/retrieve_policy.py

LangGraph node: retrieve_policy
Builds a query from extracted metadata and retrieves the most relevant
credit policy chunks from the Chroma vector store.
"""

from pipeline.state import PipelineState
from pipeline.retriever import retrieve_policy_chunks


def retrieve_policy(state: PipelineState) -> dict:
    errors = list(state.get("errors", []))
    metadata = state.get("extracted_metadata") or {}

    # Build a composite natural-language query from available metadata
    parts: list[str] = []
    if metadata.get("dscr") is not None:
        parts.append(f"DSCR requirement {metadata['dscr']}")
    if metadata.get("ltv") is not None:
        parts.append(f"LTV limit {metadata['ltv']}%")
    if metadata.get("industry"):
        parts.append(f"industry sector restrictions {metadata['industry']}")
    parts.append("required document checklist")
    parts.append("borrower creditworthiness criteria")

    query = " ".join(parts)

    try:
        chunks = retrieve_policy_chunks(query, n_results=5)
        if not chunks:
            errors.append("retrieve_policy: no policy chunks returned — policy section not found")
            return {"policy_chunks": [], "errors": errors}
        return {"policy_chunks": chunks, "errors": errors}

    except Exception as exc:
        errors.append(f"retrieve_policy: exception — {exc}")
        return {"policy_chunks": [], "errors": errors}
