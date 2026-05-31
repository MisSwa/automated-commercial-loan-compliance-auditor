# Requirements — Phase 1: Core — Scaffolding & UI

Branch: `phase1/core-scaffolding`
Date: 2026-05-31

Scope, decisions, and context strictly as defined in `specs/Roadmap.md` Phase 1. No additions.

---

## Scope

Phase 1 delivers a working application skeleton with no AI or LLM calls. The deliverables are:

| Deliverable | Description |
|---|---|
| Project structure | All directories and stub files in place |
| `requirements.txt` | All dependencies declared |
| Streamlit UI shell | Running app with upload, report area, and review panel |
| `data/credit_policy.txt` | Synthetic credit policy document |
| `data/sample_loan_package.txt` | Synthetic unstructured loan package |
| Chroma vector store | Credit policy ingested and queryable at `chroma_db/` |
| `pipeline/ingest.py` | Script to (re)build the Chroma index |
| `pipeline/retriever.py` | Function to query the Chroma index |

---

## What Is Explicitly Out of Scope for This Phase

- No LLM calls — Claude is not invoked in Phase 1
- No LangGraph graph or nodes
- No `PipelineState` TypedDict
- No `ComplianceReport` Pydantic schema
- No compliance logic or violation detection
- No confidence scoring
- No human review functionality (buttons are present but disabled)
- No error handling beyond basic Streamlit defaults
- No tests (test stubs may exist but no assertions)

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | As specified in `specs/Techstack.md` |
| Dependency management | `pip` + `requirements.txt` | Simple, portable for prototype |
| Embeddings model | `sentence-transformers` `all-MiniLM-L6-v2` | Lightweight, local, no API key required |
| Chroma persistence | Local directory `chroma_db/` at project root | No external service; persistent across script runs |
| Synthetic data format | Plain `.txt` files | Matches the unstructured input requirement from `specs/Mission.md` |
| UI entry point | `app/main.py` | Standard Streamlit convention; matches roadmap acceptance criteria |

---

## Constraints

- **Privacy:** `data/sample_loan_package.txt` must use entirely fictional entities — no real company names, real people, or real financial data.
- **No `.env` in version control:** `.env` is gitignored. Only `.env.example` is committed.
- **`chroma_db/` is gitignored:** The vector store is a build artifact, not source. It is always regeneratable by running `pipeline/ingest.py`.
- **Synthetic data is intentional:** `data/sample_loan_package.txt` must contain at least one deliberate policy violation so Phase 2 compliance checking has something to flag.

---

## Context from Mission

This phase has no user-facing compliance value on its own. Its purpose is to establish the foundation that Phases 2 and 3 build on. The core principles from `specs/Mission.md` that Phase 1 lays groundwork for:

- **Structured output** — the UI layout reserves space for the structured report Phase 2 will produce
- **Human oversight** — the review panel is present from day one, enforcing the principle that human controls are a first-class part of the UI, not bolted on later
- **Privacy first** — synthetic data uses fictional entities; `.env` and borrower data are gitignored from the start
