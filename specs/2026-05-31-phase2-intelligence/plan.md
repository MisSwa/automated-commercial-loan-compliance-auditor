# Phase 2 Plan: Intelligence — LangGraph Pipeline + RAG

## Overview

Build the end-to-end LangGraph pipeline that transforms a raw loan package text into a structured `ComplianceReport`. Phase 1's Chroma store and Streamlit shell are the foundation; this phase wires in the intelligence layer.

---

## Task Groups

### Group 1 — State & Schema Definitions

**Goal:** Define the typed contracts that all nodes depend on before any node is implemented.

- [ ] Create `pipeline/state.py` — define `PipelineState` as a `TypedDict` with all fields passed between nodes:
  - `raw_text: str`
  - `extracted_metadata: dict | None`
  - `policy_chunks: list[str]`
  - `compliance_results: dict | None`
  - `confidence: dict | None`
  - `report: ComplianceReport | None`
  - `errors: list[str]`
- [ ] Create `pipeline/schemas.py` — define `ComplianceReport` as a Pydantic model:
  - Borrower metadata (name, loan amount, DSCR, LTV, industry)
  - Document checklist status (present / missing per required doc)
  - Covenant checks (pass / fail per policy item, with policy reference)
  - Violations list (description + policy section cited)
  - Confidence score (0–100) + rationale string
  - Recommended next steps (informational only)
  - Partial extraction flag (`is_partial: bool`)

---

### Group 2 — `extract_metadata` Node

**Goal:** Claude reads raw loan text and returns structured metadata using tool use / structured output.

- [ ] Create `pipeline/nodes/extract_metadata.py`
- [ ] Define extraction tool schema (JSON schema for Claude tool use): borrower name, loan amount, DSCR, LTV, industry/sector, document list
- [ ] Call Claude with `tools` parameter; parse `tool_use` block from response
- [ ] Map extracted fields onto `PipelineState.extracted_metadata`
- [ ] For each field Claude could not extract: record as `None`; append a note to `PipelineState.errors`

---

### Group 3 — `retrieve_policy` Node

**Goal:** Use extracted metadata to query Chroma and surface the most relevant credit policy chunks.

- [ ] Create `pipeline/nodes/retrieve_policy.py`
- [ ] Build a natural-language query from extracted metadata (DSCR value, LTV value, industry, document list)
- [ ] Call the existing `pipeline/retriever.py` to query Chroma
- [ ] Store returned chunks in `PipelineState.policy_chunks`
- [ ] If no chunks returned: append `"policy section not found"` to `PipelineState.errors`; continue (do not abort)

---

### Group 4 — `check_compliance` Node

**Goal:** Claude cross-references extracted metadata against retrieved policy chunks and produces structured findings.

- [ ] Create `pipeline/nodes/check_compliance.py`
- [ ] Define compliance check tool schema: list of objects, each with `item`, `status` (`pass`/`fail`/`unable_to_verify`), and `policy_reference`
- [ ] Prompt Claude with extracted metadata + policy chunks; call with tools
- [ ] Parse `tool_use` response into `PipelineState.compliance_results`
- [ ] Any field that was `None` in `extracted_metadata` → automatically `"unable_to_verify"` in compliance results (no LLM call needed for those)

---

### Group 5 — `score_confidence` Node

**Goal:** Compute a confidence score based on extraction completeness and policy coverage quality.

- [ ] Create `pipeline/nodes/score_confidence.py`
- [ ] Define scoring tool schema: `score: int` (0–100), `rationale: str`, `factors: list[str]`
- [ ] Prompt Claude with the extraction results and compliance findings; request a confidence assessment
- [ ] Parse response into `PipelineState.confidence`
- [ ] Deterministic floor rule: if >50% of metadata fields are `None`, cap score at 40 regardless of LLM output

---

### Group 6 — `generate_report` Node

**Goal:** Assemble all pipeline state into a validated `ComplianceReport` Pydantic object.

- [ ] Create `pipeline/nodes/generate_report.py`
- [ ] Map `PipelineState` fields into `ComplianceReport` constructor
- [ ] Set `is_partial = True` if any required metadata field is `None`
- [ ] Validate via Pydantic; on `ValidationError`: store partial report with `is_partial = True` and log error
- [ ] Store the validated report in `PipelineState.report`

---

### Group 7 — Graph Assembly

**Goal:** Wire all nodes into a LangGraph `StateGraph` and expose a `run_pipeline(raw_text)` entry point.

- [ ] Create `pipeline/graph.py`
- [ ] Instantiate `StateGraph(PipelineState)`
- [ ] Add all five nodes in order
- [ ] Add edges: `extract_metadata → retrieve_policy → check_compliance → score_confidence → generate_report`
- [ ] Compile the graph
- [ ] Expose `run_pipeline(raw_text: str) -> ComplianceReport` as the public API

---

### Group 8 — Streamlit Integration

**Goal:** Replace the placeholder in `app/main.py` with a live pipeline call; render the `ComplianceReport`.

- [ ] Import `run_pipeline` from `pipeline/graph.py`
- [ ] On file upload: call `run_pipeline(raw_text)`, store result in `st.session_state`
- [ ] Render report sections: metadata, document checklist, covenant checks, violations, confidence score
- [ ] Pass/fail badges (text labels; visual styling is Phase 3)
- [ ] If `is_partial`: display a warning banner listing what could not be extracted
- [ ] Keep human review buttons visible but disabled (Phase 3 enables them)

---

## File Map

```
pipeline/
  state.py               ← PipelineState TypedDict
  schemas.py             ← ComplianceReport Pydantic model
  graph.py               ← StateGraph assembly + run_pipeline()
  nodes/
    __init__.py
    extract_metadata.py
    retrieve_policy.py
    check_compliance.py
    score_confidence.py
    generate_report.py
app/
  main.py                ← update: wire run_pipeline, render report
tests/
  test_phase2.py         ← unit + integration tests (see evaluation.md)
```
