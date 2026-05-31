# Evaluation — Phase 1: Core — Scaffolding & UI

Branch: `phase1/core-scaffolding`
Date: 2026-05-31

Phase 1 is complete and ready to merge when **all manual checks pass** and **the automated verification script exits cleanly**. Both must pass — neither alone is sufficient.

---

## Manual Smoke Tests

Run these in order. Each must pass before moving to the next.

### 1. Environment

- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `python -c "import streamlit, chromadb, sentence_transformers, anthropic, langgraph, pydantic, dotenv"` exits with no errors
- [ ] `.env` is not tracked by git (`git status` does not show `.env`)
- [ ] `.env.example` is tracked and contains the `ANTHROPIC_API_KEY` placeholder

### 2. Project Structure

- [ ] All directories exist: `app/`, `pipeline/`, `data/`, `specs/`, `tests/`
- [ ] `app/__init__.py`, `pipeline/__init__.py`, `tests/__init__.py` are present
- [ ] `data/credit_policy.txt` exists and is non-empty
- [ ] `data/sample_loan_package.txt` exists and is non-empty
- [ ] `chroma_db/` directory is gitignored

### 3. Streamlit UI

- [ ] `streamlit run app/main.py` launches without errors
- [ ] Page title and layout render correctly
- [ ] File upload widget is visible and accepts `.txt` files
- [ ] Uploading `data/sample_loan_package.txt` displays the raw file content
- [ ] Report display area shows "No report generated yet" placeholder
- [ ] Approve, Reject, and Request More Info buttons are visible but disabled
- [ ] Review panel label reads "Awaiting compliance report before review is available"

### 4. Chroma Ingestion

- [ ] `python pipeline/ingest.py` runs without errors
- [ ] `chroma_db/` directory is created and non-empty after ingestion
- [ ] Running `python pipeline/ingest.py` a second time does not crash (idempotent)

### 5. Retrieval

- [ ] Manual Python check: calling `retrieve_policy_chunks("DSCR requirement")` returns at least one non-empty string containing relevant policy text
- [ ] Manual Python check: calling `retrieve_policy_chunks("LTV ratio")` returns at least one non-empty string containing relevant policy text

---

## Automated Verification Script

Create and run `tests/test_phase1.py`. The script must exit with code 0.

### What the script checks

```python
# 1. All required files exist
# 2. All required directories exist
# 3. data/credit_policy.txt and data/sample_loan_package.txt are non-empty
# 4. Chroma collection is populated (collection.count() > 0)
# 5. retrieve_policy_chunks("DSCR") returns at least 1 result
# 6. retrieve_policy_chunks("LTV") returns at least 1 result
# 7. app/main.py is importable without raising an exception
```

Run with: `pytest tests/test_phase1.py -v`

All assertions must pass with no errors or failures.

---

## Merge Criteria

| Check | Required |
|---|---|
| All manual smoke tests above pass | Yes |
| `pytest tests/test_phase1.py` exits green | Yes |
| No `.env` or real credentials in git history | Yes |
| `data/` files use only fictional entities | Yes |
| `chroma_db/` is absent from git tracking | Yes |
| Streamlit app launches cleanly on a clean install | Yes |

---

## What This Phase Does Not Need to Prove

These are intentionally deferred to Phase 2 evaluation:

- LLM calls work correctly
- LangGraph pipeline produces correct output
- Compliance violations are detected accurately
- Confidence scores are reasonable
- Human review captures decisions
