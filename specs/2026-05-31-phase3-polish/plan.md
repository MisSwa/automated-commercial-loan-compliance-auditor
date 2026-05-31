# Plan — Phase 3: Polish — Human Review, Error Handling & Privacy

Branch: `phase3/polish`
Date: 2026-05-31

Tasks are grouped by concern. Complete each group in order — later groups depend on earlier ones.

---

## Group 1: Human-in-the-Loop Review UI

Activate the human review panel and render the `ComplianceReport` in a structured, readable format. Phase 2 left buttons disabled and report sections as placeholders; this group makes them functional.

- [ ] Render `ComplianceReport` in structured sections in `app/main.py`:
  - Borrower metadata block (name, loan amount, DSCR, LTV, industry)
  - Document checklist (table: document name | status)
  - Covenant checks (pass / fail / unable_to_verify badge per item, with policy reference citation)
  - Violations list (description + policy section, highlighted)
  - Confidence score block (deferred to Group 4 for full display; render score value here)
- [ ] Enable Approve / Reject / Request More Info buttons only after `st.session_state.report` is set
- [ ] Add reviewer input fields (visible only when a report is present):
  - Text input: reviewer name (required before decision is submitted)
  - Text area: optional notes
- [ ] On button click: capture `{reviewer_name, decision, notes, timestamp}` into `st.session_state.review_decision`
- [ ] Display final decision summary below the report:
  - Reviewer name, decision label, timestamp, notes (if any)
  - Static label clarifying this is the reviewer's decision, not a system determination
- [ ] Guard: disable submit if reviewer name field is empty

---

## Group 2: Graceful Failure Handling

Cover all identified failure modes. Each failure path must produce a user-facing message, not an unhandled exception or silent drop.

- [ ] **Empty or unreadable file:** If uploaded `.txt` is empty or cannot be decoded as UTF-8 → display `st.error("Uploaded file is empty or could not be read.")` and halt
- [ ] **Malformed LLM output:** If Claude returns a response that cannot be parsed as the expected tool-use block:
  - Retry the call once (same prompt, new API call)
  - On second failure: assemble a partial report with `is_partial = True`, log the raw response to `PipelineState.errors`, continue to report display
- [ ] **No Chroma results:** If `retrieve_policy` returns an empty list → append `"No matching policy sections found for this query"` to `PipelineState.errors`; continue pipeline (do not abort)
- [ ] **Missing or invalid API key:** On app startup, check `ANTHROPIC_API_KEY` is set and non-empty; if missing → display a persistent `st.warning` in the sidebar and disable the file upload widget
- [ ] **Network / API timeout:** Wrap all Claude API calls in a try/except for `anthropic.APITimeoutError` and `anthropic.APIConnectionError` → display `st.error("LLM call timed out. Please retry.")` with a retry button that re-runs the pipeline
- [ ] Verify no failure path results in an unhandled Python exception surfacing to the Streamlit UI

---

## Group 3: Privacy Controls

Enforce session-only data handling and warn users when uploaded content appears to contain PII.

- [ ] **No persistence beyond session:** Confirm that no loan text, extracted metadata, or report data is written to disk at any point in the pipeline (chroma_db/ stores only the credit policy, never loan data)
- [ ] **PII detection on upload:** After reading uploaded file text, scan for common PII patterns before passing to the pipeline:
  - SSN pattern: `\d{3}-\d{2}-\d{4}`
  - Account number pattern: sequences of 10–17 consecutive digits
  - Common name + identifier combinations (e.g. "SSN:", "Account #", "EIN:")
  - If any pattern matches → display `st.warning("This file may contain sensitive personal information (PII). It will not be stored beyond this session.")` before proceeding
- [ ] **Session clear on refresh:** Verify via Streamlit's default behavior that `st.session_state` is cleared on browser refresh; add a manual "Clear Session" button in the sidebar that resets `st.session_state` to empty
- [ ] Do not log or print raw loan text to stdout at any point in the pipeline

---

## Group 4: Confidence Score Display

Upgrade the confidence score from a plain value (Group 1) to a color-coded visual indicator with an expandable rationale.

- [ ] Color-code the confidence score display:
  - ≥ 80 → green (`st.success`)
  - 50–79 → amber (`st.warning`)
  - < 50 → red (`st.error`)
- [ ] Display score as: `[COLOR INDICATOR] Confidence Score: {score}/100`
- [ ] Add an `st.expander("Score rationale")` below the score:
  - Show `confidence.rationale` string
  - Show `confidence.factors` as a bulleted list
- [ ] If `is_partial = True`: add a note inside the expander explaining that partial extraction caps or reduces the score

---

## Group 5: Audit Trail

Ensure every generated report carries a complete, immutable audit record of what produced it.

- [ ] Add audit fields to `ComplianceReport` Pydantic schema in `pipeline/schemas.py`:
  - `generated_at: datetime` — UTC timestamp at report generation
  - `model_used: str` — model ID used for Claude calls (e.g. `"claude-opus-4-6"`)
  - `policy_version: str` — a fixed identifier for the credit policy document (e.g. hash of `data/credit_policy.txt`, or a static version string)
  - `confidence_score: int` — copied from `PipelineState.confidence.score` for top-level access
- [ ] Populate audit fields in `pipeline/nodes/generate_report.py` at report assembly time
- [ ] Append reviewer decision to the report object in `app/main.py` after the reviewer submits:
  - Add `reviewer_decision: dict | None` field to `ComplianceReport` (default `None`)
  - On submission: set `report.reviewer_decision = {name, decision, notes, timestamp}`
- [ ] Display audit metadata at the bottom of the report UI in a collapsed `st.expander("Audit info")`:
  - Timestamp, model used, policy version, confidence score

---

## Group 6: Testing

Write the full test suite. All tests use mocked LLM responses — no live API calls in tests.

- [ ] Create `tests/test_phase3.py`
- [ ] **Unit tests — human review UI logic:**
  - `test_review_buttons_disabled_without_report` — buttons remain disabled when `session_state.report` is `None`
  - `test_review_buttons_enabled_with_report` — buttons are enabled after report is set
  - `test_review_capture_stores_decision` — submitting a decision stores `review_decision` in session state
  - `test_review_requires_reviewer_name` — submission blocked when reviewer name is empty
- [ ] **Unit tests — failure handling:**
  - `test_empty_file_triggers_error` — empty file upload produces error, no pipeline call
  - `test_malformed_llm_retries_once` — malformed LLM response triggers exactly one retry
  - `test_malformed_llm_second_failure_partial_report` — two consecutive failures yield `is_partial = True` report
  - `test_no_chroma_results_continues_pipeline` — empty retrieval appends error but does not abort
  - `test_missing_api_key_disables_upload` — missing `ANTHROPIC_API_KEY` disables the upload widget
- [ ] **Unit tests — privacy:**
  - `test_pii_ssn_pattern_triggers_warning` — file with SSN pattern fires PII warning
  - `test_pii_account_number_triggers_warning` — file with 12-digit account number fires PII warning
  - `test_no_pii_no_warning` — clean file produces no PII warning
  - `test_clear_session_resets_state` — clear session button resets `st.session_state`
- [ ] **Unit tests — confidence display:**
  - `test_confidence_green_at_80` — score ≥ 80 renders with `st.success`
  - `test_confidence_amber_at_65` — score 65 renders with `st.warning`
  - `test_confidence_red_at_40` — score 40 renders with `st.error`
  - `test_confidence_expander_shows_rationale` — expander contains rationale and factors
- [ ] **Unit tests — audit trail:**
  - `test_report_has_generated_at` — `ComplianceReport` has non-null `generated_at`
  - `test_report_has_model_used` — `model_used` field is present and non-empty
  - `test_report_has_policy_version` — `policy_version` field is present
  - `test_audit_reviewer_decision_appended` — after submission, `reviewer_decision` is set on report
- [ ] **Integration test:**
  - `test_full_pipeline_with_sample_loan` — run full pipeline on `data/sample_loan_package.txt` with mocked Claude; verify `ComplianceReport` has all audit fields populated
- [ ] **Edge case tests:**
  - `test_empty_file_no_exception` — uploading empty file raises no unhandled exception
  - `test_truncated_loan_package` — loan package missing several fields yields `is_partial = True`
  - `test_all_violations_package` — loan package with all policy violations produces non-empty violations list
