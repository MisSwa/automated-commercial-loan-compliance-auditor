# Phase 2 Evaluation: How to Know It's Ready to Merge

## Merge Gate

All of the following must be true before this branch is merged:

1. All automated tests pass (`pytest tests/test_phase2.py`)
2. All roadmap acceptance criteria are covered by a test (listed below)
3. Phase 1 tests still pass (`pytest tests/test_phase1.py`)
4. `streamlit run app/main.py` runs without errors with `ANTHROPIC_API_KEY` set

---

## Automated Test Requirements

Tests live in `tests/test_phase2.py`. The LLM is always mocked — no real API calls in the test suite.

### Unit Tests (one per node, mocked LLM)

| Test | What It Verifies |
|---|---|
| `test_extract_metadata_happy_path` | Node correctly parses a valid Claude tool_use response into `extracted_metadata` |
| `test_extract_metadata_partial` | When Claude returns `None` for a field, `errors` list is non-empty and field is `None` in state |
| `test_retrieve_policy_returns_chunks` | Node calls `query_policy` and populates `policy_chunks` |
| `test_retrieve_policy_no_results` | When Chroma returns empty list, `"policy section not found"` appears in `errors` |
| `test_check_compliance_violations` | Node correctly maps a tool_use response into `compliance_results` with fail items |
| `test_check_compliance_unable_to_verify` | Fields that were `None` in `extracted_metadata` produce `"unable_to_verify"` results without an LLM call |
| `test_score_confidence_floor_rule` | If >50% of metadata fields are `None`, score is capped at 40 regardless of LLM output |
| `test_generate_report_valid` | Full state with all fields populated produces a valid `ComplianceReport` with `is_partial = False` |
| `test_generate_report_partial` | State with `None` fields produces `ComplianceReport` with `is_partial = True` |

### Integration Test

| Test | What It Verifies |
|---|---|
| `test_full_pipeline_sample_loan` | End-to-end: `run_pipeline(sample_loan_text)` with mocked LLM returns a `ComplianceReport`. Checks: report is not `None`, `violations` is a list, `confidence.score` is an int 0–100, `is_partial` is a bool |

### Roadmap Acceptance Criteria Coverage

Each acceptance criterion from the roadmap must map to at least one test:

| Roadmap Criterion | Covered By |
|---|---|
| Uploading sample loan package produces a populated `ComplianceReport` | `test_full_pipeline_sample_loan` |
| Each violation cites the relevant policy section | `test_check_compliance_violations` |
| Confidence score is present and justified | `test_score_confidence_floor_rule`, `test_generate_report_valid` |
| Missing/unparseable fields are surfaced, not silently dropped | `test_extract_metadata_partial`, `test_generate_report_partial` |
| Pipeline completes without unhandled exceptions on valid input | `test_full_pipeline_sample_loan` |

---

## Manual Smoke Test (run before opening PR)

1. Set `ANTHROPIC_API_KEY` in `.env`
2. Run `streamlit run app/main.py`
3. Upload `data/sample_loan_package.txt`
4. Verify:
   - Report renders without a Python traceback
   - At least one covenant check appears in the UI
   - At least one violation appears (the sample package is designed to have violations)
   - Confidence score is visible with a numeric value
   - If any field could not be extracted, a warning banner is visible

---

## What a Passing State Looks Like

```
pytest tests/test_phase1.py tests/test_phase2.py
...
15 passed in X.XXs
```

No skipped tests, no xfail, no warnings about unhandled exceptions.

---

## Not Required for This Phase

The following are tracked in Phase 3 and are **not** blocking for merge:

- Confidence score color coding
- Human review button functionality
- PII detection warnings
- Retry logic on malformed LLM output
- Audit trail fields (timestamp, model version, policy version)
- Edge case tests (empty file, truncated package, all-violations package)
