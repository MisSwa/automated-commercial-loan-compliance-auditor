# Automated Commercial Loan Compliance Auditor

A Streamlit prototype that ingests an unstructured commercial loan package, extracts key metadata using Claude, cross-references it against the bank's credit policy using RAG, and produces a structured compliance report — with a confidence score — for human review.

> **The system never approves or rejects a loan.** All findings are surfaced to a named human reviewer who records the final decision.

## At a glance

| | |
|---|---|
| **Problem** | Credit analysts manually check unstructured loan packages against bank credit policy |
| **What it does** | Extracts loan metadata (DSCR, LTV, amount), retrieves relevant policy via RAG, flags violations, and scores confidence 0–100 |
| **How** | Five-node LangGraph pipeline using Claude structured tool use and a Chroma vector store; output validated with Pydantic |
| **Safety** | Never approves or rejects; PII detection, no borrower data persisted, explicit handling for every failure mode |
| **Stack** | Python · LangGraph · Claude · Chroma · sentence-transformers · Pydantic · Streamlit · LangSmith · pytest (50 tests) |

---

## What it does

1. Accepts a `.txt` loan package uploaded through the browser
2. Runs PII detection and warns before any processing begins
3. Passes the raw text through a five-node LangGraph pipeline:
   - **Extract** — Claude pulls structured metadata (borrower name, loan amount, DSCR, LTV, industry, document list)
   - **Retrieve** — relevant credit policy sections are fetched from a local Chroma vector store
   - **Check** — Claude cross-references metadata against policy and identifies violations
   - **Score** — a confidence score (0–100) is assigned based on extraction completeness and policy coverage
   - **Report** — a validated `ComplianceReport` object is assembled
4. Renders the report with color-coded confidence, cited violations, and an audit trail
5. Prompts a human reviewer to record Approve / Reject / Request More Info with their name and optional notes

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- The credit policy must be ingested into Chroma before the first run (one-time setup, see below)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/MisSwa/automated-commercial-loan-compliance-auditor.git
cd automated-commercial-loan-compliance-auditor

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here
```

---

## First-time setup: ingest the credit policy

The Chroma vector store must be built before the pipeline can retrieve policy sections. Run this once (and again any time `data/credit_policy.txt` changes):

```bash
python pipeline/ingest.py
```

This reads `data/credit_policy.txt`, chunks it by section, embeds it with `sentence-transformers/all-MiniLM-L6-v2`, and persists the store to `chroma_db/`.

---

## Running the app

```bash
streamlit run app/main.py
```

Open the URL shown in the terminal (default: `http://localhost:8501`).

Upload `data/sample_loan_package.txt` to see a full end-to-end run with deliberate policy violations built in.

---

## Project structure

```
.
├── app/
│   └── main.py                  # Streamlit UI — upload, report rendering, human review
├── pipeline/
│   ├── state.py                 # PipelineState TypedDict (shared between nodes)
│   ├── schemas.py               # ComplianceReport Pydantic model
│   ├── graph.py                 # LangGraph StateGraph + run_pipeline() entry point
│   ├── ingest.py                # One-time credit policy ingestion script
│   ├── retriever.py             # Chroma query interface
│   └── nodes/
│       ├── extract_metadata.py  # Node 1: Claude extracts loan fields
│       ├── retrieve_policy.py   # Node 2: Chroma fetches relevant policy chunks
│       ├── check_compliance.py  # Node 3: Claude checks metadata against policy
│       ├── score_confidence.py  # Node 4: Claude scores extraction confidence
│       └── generate_report.py  # Node 5: assembles ComplianceReport
├── data/
│   ├── credit_policy.txt        # Meridian Commercial Bank Credit Policy v2.1
│   └── sample_loan_package.txt  # Synthetic loan with intentional violations
├── tests/
│   ├── test_phase1.py           # Scaffolding and ingestion tests
│   ├── test_phase2.py           # Pipeline node unit + integration tests
│   └── test_phase3.py           # UI logic, failure handling, privacy, audit tests
├── specs/                       # Feature specs (plan, requirements, evaluation) per phase
├── chroma_db/                   # Persisted vector store (created by ingest.py, gitignored)
├── requirements.txt
├── .env.example
└── stakeholder-overview.html    # One-page non-technical project overview
```

---

## Architecture

```
┌─────────────────────────────────────┐
│           Streamlit UI              │  File upload · report display · human review
└────────────────┬────────────────────┘
                 │  raw text
┌────────────────▼────────────────────┐
│         LangGraph Pipeline          │
│                                     │
│  [1] extract_metadata               │  Claude (tool use) → structured fields
│         ↓                           │
│  [2] retrieve_policy  ←──────────── │─── Chroma (credit policy vector store)
│         ↓                           │
│  [3] check_compliance               │  Claude (tool use) → violations + checks
│         ↓                           │
│  [4] score_confidence               │  Claude (tool use) → 0–100 score + rationale
│         ↓                           │
│  [5] generate_report                │  Pydantic → ComplianceReport
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         Claude (Anthropic)          │  claude-opus-4-6
└─────────────────────────────────────┘
```

**State** flows as a `TypedDict` between nodes. Each node returns a partial update; LangGraph merges it into the running state. Claude is called at nodes 1, 3, and 4 using structured tool use — no free-form parsing.

---

## ComplianceReport schema

The final output is a validated Pydantic object with these top-level fields:

| Field | Type | Description |
|---|---|---|
| `borrower_name` | `str \| None` | Extracted borrower entity name |
| `loan_amount` | `float \| None` | Requested loan amount in dollars |
| `dscr` | `float \| None` | Pro forma combined DSCR |
| `ltv` | `float \| None` | Effective LTV percentage |
| `industry` | `str \| None` | Borrower industry / sector |
| `documents` | `list[DocumentStatus]` | Each required doc with present / missing / pending status |
| `covenant_checks` | `list[CovenantCheck]` | Pass / fail / unable\_to\_verify per policy item, with policy citation |
| `violations` | `list[Violation]` | Each violation with description and policy section reference |
| `confidence_score` | `int` | 0–100; capped at 40 if >50% of required fields could not be extracted |
| `confidence_rationale` | `str` | Explanation of the score |
| `confidence_factors` | `list[str]` | Specific factors that drove the score up or down |
| `recommended_next_steps` | `list[str]` | Informational only — not a decision |
| `is_partial` | `bool` | True if any required metadata field could not be extracted |
| `pipeline_errors` | `list[str]` | Diagnostic messages from every node |
| `generated_at` | `datetime` | UTC timestamp of report assembly |
| `model_used` | `str` | Claude model ID used |
| `policy_version` | `str` | Credit policy version queried |
| `reviewer_decision` | `dict \| None` | Set after human review: name, decision, notes, timestamp |

---

## Failure handling

Every failure mode is handled explicitly — no unhandled exceptions reach the UI.

| Failure | Behavior |
|---|---|
| Empty or unreadable file | Error shown; pipeline does not run |
| Missing `ANTHROPIC_API_KEY` | Sidebar warning on startup; upload widget disabled |
| Malformed LLM response (no tool-use block) | Node retries once; second failure → partial report with error logged |
| No Chroma results | Error appended to state; pipeline continues |
| API timeout or connection error | User-facing error message with a Retry button |
| Pydantic validation error on report assembly | Minimal partial report returned; error logged |

Fields Claude could not extract appear as `None` in metadata and `unable_to_verify` in covenant checks — never silently dropped.

---

## Privacy controls

- Borrower data is **never written to disk**. `chroma_db/` contains only the credit policy.
- PII detection runs on every upload before the pipeline starts. Triggers on SSN patterns (`\d{3}-\d{2}-\d{4}`), long digit sequences (10–17 digits), and labeled identifiers (`SSN:`, `Account #:`, `EIN:`). A warning is shown; the upload is not blocked.
- Session state is cleared on browser refresh. A **Clear Session** button in the sidebar provides an explicit reset.
- Raw loan text is never printed to stdout or logged anywhere in the pipeline.

---

## Running the tests

```bash
pytest tests/ -v
```

All 50 tests pass. No live API key required — all Claude calls are mocked.

| Suite | Tests | Covers |
|---|---|---|
| `test_phase1.py` | 13 | Directory structure, data files, Chroma ingestion, retrieval, app importability |
| `test_phase2.py` | 11 | Each pipeline node (unit) + full end-to-end integration test |
| `test_phase3.py` | 26 | Human review logic, failure handling, PII detection, confidence color, audit trail, edge cases |

---

## LangSmith tracing

The pipeline is automatically traced in [LangSmith](https://smith.langchain.com/) when the following variables are set in `.env`. No code changes are required — LangGraph picks them up at runtime.

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_PROJECT=loan-compliance-auditor
```

Get a LangSmith API key at [smith.langchain.com](https://smith.langchain.com/). The free tier is sufficient for development.

Each `run_pipeline()` call will appear as a trace in your LangSmith project, showing:
- Inputs and outputs for every LangGraph node
- Claude API calls with full prompts and responses
- Token counts and latency per node
- Any errors accumulated in `PipelineState.errors`

To disable tracing, remove the three variables from `.env` or set `LANGCHAIN_TRACING_V2=false`.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key. Get one at [console.anthropic.com](https://console.anthropic.com/). |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing. |
| `LANGCHAIN_API_KEY` | No | Your LangSmith API key. Required when tracing is enabled. |
| `LANGCHAIN_PROJECT` | No | LangSmith project name. Defaults to `"default"` if omitted. |

Loaded from `.env` via `python-dotenv`. Never commit `.env` to version control — it is listed in `.gitignore`.

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Pipeline orchestration | LangGraph |
| LLM | Claude (`claude-opus-4-6`) via Anthropic SDK |
| Vector store | Chroma (local persistent) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Output schema | Pydantic v2 |
| Language | Python 3.11+ |

---

## Out of scope (this prototype)

- User authentication or role-based access
- Cloud deployment or containerization
- Persistent audit log database
- Multi-file loan package support
- Streaming LLM output
- Integration with core banking systems
