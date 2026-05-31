# Phase 2 Requirements: Intelligence — LangGraph Pipeline + RAG

## Scope

Phase 2 delivers the intelligence layer. The Streamlit shell and Chroma vector store from Phase 1 are prerequisites and must not be broken. This phase adds:

1. A typed pipeline state definition (`PipelineState`)
2. A validated output schema (`ComplianceReport`)
3. Five LangGraph nodes that transform raw loan text into a structured report
4. A compiled `StateGraph` with a public `run_pipeline()` entry point
5. Updated Streamlit UI that calls the pipeline and renders the report

**Explicitly out of scope for this phase:**
- Human review button wiring (Phase 3)
- Error handling UI (Phase 3)
- PII detection (Phase 3)
- Confidence score color coding (Phase 3)
- Audit trail fields on the report (Phase 3)
- Persistent storage of any kind

---

## Decisions

### LLM Interaction Pattern: Tool Use / Structured Output

Claude is called using the `tools` parameter in the Anthropic SDK. Each node that requires LLM output defines an explicit JSON schema for the tool. Claude returns a `tool_use` block, which is parsed and validated.

**Rationale:**
- Forces Claude to return structured data rather than free-form text
- Makes extraction failures explicit (missing fields vs. absent key)
- Aligns with the project's "structured output, never silent failure" principle
- Easier to mock in tests (tool response is a deterministic dict)

**Model:** Use `claude-opus-4-6` unless a lighter model proves sufficient during development.

### State Pattern: TypedDict (Not Pydantic)

`PipelineState` uses `typing.TypedDict`. This is LangGraph's native pattern — nodes return partial dicts that LangGraph merges into state. Pydantic is reserved for the final `ComplianceReport` output only.

### Partial Extraction Handling

Missing fields are never silently dropped. The contract is:
- LLM could not extract a field → field is `None` in `extracted_metadata`
- Field is `None` → compliance check for that item is `"unable_to_verify"`
- `is_partial` flag on `ComplianceReport` is `True` if any required field is `None`
- UI displays a visible warning when `is_partial` is `True`

### No Retry Logic in This Phase

If Claude returns a malformed tool response, the node logs the error to `PipelineState.errors` and continues with `None` for that field. Retry logic is a Phase 3 concern.

---

## Context

### What Phase 1 Delivered

| Artifact | Location | Notes |
|---|---|---|
| Streamlit shell | `app/main.py` | File upload works; report area is placeholder |
| Chroma vector store | `chroma_db/` | Populated with credit policy chunks |
| Retriever utility | `pipeline/retriever.py` | `query_policy(text, n_results)` is the public API |
| Ingestion script | `pipeline/ingest.py` | Run once; already executed |
| Synthetic credit policy | `data/credit_policy.txt` | Source for Chroma embeddings |
| Sample loan package | `data/sample_loan_package.txt` | Primary test input for Phase 2 |

### Key Interfaces to Preserve

- `pipeline/retriever.py` exports `query_policy(query: str, n_results: int = 5) -> list[str]`
- `app/main.py` must still run with `streamlit run app/main.py`
- `requirements.txt` is the single source of dependencies; update it for new imports

### Environment

- `ANTHROPIC_API_KEY` loaded from `.env` via `python-dotenv`
- Python 3.11+
- All dependencies managed via `pip` + `requirements.txt`

---

## Constraints

| Constraint | Detail |
|---|---|
| No borrower data persistence | Raw loan text and extracted fields live only in `st.session_state` and pipeline state during a single run |
| No automated loan decisions | `ComplianceReport` surfaces findings only; never emits approve/reject |
| Graceful partial results | Pipeline must complete and return a report even when extraction is incomplete |
| Chroma is read-only in Phase 2 | Policy ingestion was a Phase 1 concern; no re-ingestion logic needed |
