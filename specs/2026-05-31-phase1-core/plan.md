# Plan — Phase 1: Core — Scaffolding & UI

Branch: `phase1/core-scaffolding`
Date: 2026-05-31

Tasks are grouped by concern. Complete each group in order — later groups depend on earlier ones.

---

## Group 1: Project Setup & Environment

Establish the repository structure, dependency file, and environment variable loading. Nothing runs until this is done.

- [ ] Create top-level directory structure:
  ```
  app/
  pipeline/
  data/
  specs/
  tests/
  ```
- [ ] Create `requirements.txt` with all Phase 1 + future dependencies:
  ```
  streamlit
  langgraph
  langchain-core
  anthropic
  chromadb
  sentence-transformers
  pydantic
  python-dotenv
  pytest
  ```
- [ ] Create `.env.example` with placeholder keys (no real values):
  ```
  ANTHROPIC_API_KEY=your_key_here
  ```
- [ ] Create `.gitignore` covering: `.env`, `__pycache__`, `*.pyc`, `chroma_db/`, `.venv/`
- [ ] Add `app/__init__.py`, `pipeline/__init__.py`, `tests/__init__.py` (empty stubs)
- [ ] Verify: `python -c "import streamlit, chromadb, sentence_transformers, anthropic"` runs without error

---

## Group 2: Streamlit UI Shell

Build the full UI skeleton with no backend logic. All interactive elements present but non-functional until Phase 2 wires them up.

- [ ] Create `app/main.py` as the Streamlit entry point
- [ ] Implement file upload section:
  - `st.file_uploader` accepting `.txt` files only
  - On upload: read and display raw file text in an expander ("View raw loan package")
- [ ] Implement placeholder report display area:
  - Static "No report generated yet" message
  - Structured layout reserved for future report rendering (sections for Borrower Info, Document Checklist, Covenant Checks, Violations, Confidence Score)
- [ ] Implement human review panel:
  - Three buttons: **Approve**, **Reject**, **Request More Info**
  - All buttons disabled (`disabled=True`) until a report is present
  - Static label: "Awaiting compliance report before review is available"
- [ ] Add page config: title, layout, sidebar with phase indicator ("Phase 1 — UI Shell")
- [ ] Verify: `streamlit run app/main.py` launches without error and all UI elements render

---

## Group 3: Synthetic Data Generation

Create realistic synthetic files in `data/` that will serve as the fixed test inputs for all three phases.

- [ ] Create `data/credit_policy.txt` — structured plain-text credit policy document covering:
  - Minimum DSCR threshold (e.g. ≥ 1.25x)
  - Maximum LTV ratio (e.g. ≤ 75% for commercial real estate)
  - Required document checklist (e.g. 3 years financials, appraisal, environmental report, borrower personal financial statement)
  - Borrower creditworthiness criteria (minimum credit score, years in business, net worth requirements)
  - Industry/sector restrictions (excluded SIC codes or flagged sectors)
  - Loan size limits by property type
- [ ] Create `data/sample_loan_package.txt` — unstructured plain-text loan submission covering:
  - Borrower profile (business name, structure, years in operation, principals)
  - Loan request (amount, purpose, term, requested rate)
  - Financial summary (revenue, EBITDA, existing debt, DSCR calculation)
  - Collateral description (property type, appraised value, LTV calculation)
  - Document list (what has been provided vs. what is missing)
  - At least one intentional policy violation to test compliance flagging later
- [ ] Verify: both files exist, are non-empty, and are human-readable plain text

---

## Group 4: Chroma Ingestion & Verification

Ingest the credit policy into Chroma so Phase 2 can retrieve relevant policy chunks during compliance checking.

- [ ] Create `pipeline/ingest.py`:
  - Load `data/credit_policy.txt`
  - Chunk the document (by section or fixed-size with overlap)
  - Embed chunks using `sentence-transformers` (`all-MiniLM-L6-v2`)
  - Persist to a local Chroma collection (`chroma_db/` directory)
- [ ] Create `pipeline/retriever.py`:
  - Function `retrieve_policy_chunks(query: str, n_results: int = 3) -> list[str]`
  - Loads the persisted Chroma collection
  - Returns top-n matching policy chunks for a given query string
- [ ] Run ingestion: `python pipeline/ingest.py` — verify `chroma_db/` is created and populated
- [ ] Verify retrieval: a sample query (e.g. `"DSCR requirement"`) returns relevant policy text
