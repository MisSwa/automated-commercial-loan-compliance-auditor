# Roadmap

Three phases of work, each building on the last. No phase is "done" until its acceptance criteria are met.

---

## Phase 1: Core — Scaffolding & UI

**Goal:** A running Streamlit app with project structure, environment wiring, and synthetic test data ready. No AI yet.

### Tasks

- [ ] Initialize project directory structure (`app/`, `specs/`, `data/`, `pipeline/`, `tests/`)
- [ ] Create `requirements.txt` with all dependencies
- [ ] Set up `.env` loading via `python-dotenv`
- [ ] Build Streamlit UI shell:
  - File upload widget (accepts `.txt`)
  - Placeholder report display area
  - Human review panel (Approve / Reject / Request More Info buttons, disabled until report is ready)
- [ ] Generate synthetic **credit policy** document covering:
  - Minimum DSCR (Debt Service Coverage Ratio) thresholds
  - Maximum LTV (Loan-to-Value) ratios
  - Required document checklist
  - Borrower creditworthiness criteria
  - Industry/sector restrictions
- [ ] Generate synthetic **sample loan package** text file (unstructured) covering:
  - Borrower profile
  - Loan request details
  - Financial statements summary
  - Collateral description
  - Document list
- [ ] Ingest credit policy into **Chroma** vector store using `sentence-transformers` embeddings
- [ ] Verify Chroma retrieval returns relevant chunks for sample queries

### Acceptance Criteria

- App runs locally with `streamlit run app/main.py`
- File upload works and displays raw text
- Chroma store is populated and queryable
- Synthetic data files exist in `data/`

---

## Phase 2: Intelligence — LangGraph Pipeline + RAG

**Goal:** End-to-end LangGraph pipeline that extracts metadata, retrieves policy, checks compliance, and scores confidence.

### Tasks

- [ ] Define `PipelineState` as a `TypedDict` (typed state passed between LangGraph nodes — native LangGraph pattern)
- [ ] Implement LangGraph graph with nodes:
  1. **`extract_metadata`** — Claude extracts structured fields from raw loan text (borrower name, loan amount, DSCR, LTV, document list, etc.)
  2. **`retrieve_policy`** — Query Chroma with extracted fields to surface relevant credit policy sections
  3. **`check_compliance`** — Claude cross-references extracted data against retrieved policy chunks; produces list of violations and passes
  4. **`score_confidence`** — Assign a confidence score (0–100) based on extraction completeness and policy coverage
  5. **`generate_report`** — Assemble final structured `ComplianceReport` object
- [ ] Define `ComplianceReport` Pydantic schema:
  - Borrower metadata
  - Document checklist status
  - Covenant checks (pass/fail per item)
  - Violations list with policy references
  - Confidence score + rationale
  - Recommended next steps (informational only — no decision)
- [ ] Wire pipeline into Streamlit: run on file upload, pass raw text as initial state
- [ ] Handle partial extraction gracefully (missing fields → flagged as "unable to verify")

### Acceptance Criteria

- Uploading the sample loan package produces a populated `ComplianceReport`
- Each violation cites the relevant policy section
- Confidence score is present and justified
- Missing/unparseable fields are surfaced, not silently dropped
- Pipeline completes without unhandled exceptions on valid input

---

## Phase 3: Polish — Human Review, Error Handling & Privacy

**Goal:** Production-quality UX, complete error coverage, privacy controls, and a clean auditable report format.

### Tasks

- [ ] **Human-in-the-loop review UI:**
  - Render `ComplianceReport` in structured, readable format (sections, badges for pass/fail/warning)
  - Enable Approve / Reject / Request More Info buttons only after report is generated
  - Capture reviewer name, decision, and optional notes
  - Display final decision summary (reviewer-owned, not system-owned)
- [ ] **Graceful failure handling:**
  - Uploaded file is empty or unreadable → clear error message
  - LLM returns malformed output → retry once, then partial report with error flag
  - Chroma retrieval returns no results → report notes "policy section not found"
  - API key missing or invalid → startup warning, blocked upload
  - Network/API timeout → user-facing error with retry option
- [ ] **Privacy controls:**
  - No loan package text persisted beyond session state
  - Warn user if uploaded file appears to contain PII (names, SSNs, account numbers)
  - Session state cleared on browser refresh
- [ ] **Confidence score display:**
  - Visual indicator (color-coded: green ≥ 80, amber 50–79, red < 50)
  - Expandable rationale explaining what drove the score up or down
- [ ] **Audit trail:**
  - Each report includes: timestamp, model used, policy version queried, confidence score
  - Reviewer decision is appended to the report object before final display
- [ ] **Testing:**
  - Unit tests for each LangGraph node with mocked LLM responses
  - Integration test: full pipeline run on sample loan package
  - Edge case tests: empty file, truncated package, all-violations package

### Acceptance Criteria

- Human review buttons work correctly and capture decisions
- All identified failure modes are handled without unhandled exceptions
- PII warning fires on sample data containing sensitive identifiers
- Confidence score renders with correct color coding and rationale
- Audit fields present on every generated report
- All tests pass

---

## Out of Scope (This Prototype)

- User authentication / role-based access
- Cloud deployment or containerization
- Multi-file loan package support
- Integration with core banking systems
- Persistent audit log database
- Streaming LLM output
