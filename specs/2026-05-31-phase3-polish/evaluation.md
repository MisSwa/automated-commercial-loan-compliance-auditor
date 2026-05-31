# Evaluation — Phase 3: Polish — Human Review, Error Handling & Privacy

Phase 3 is complete when every criterion below is met. No criterion is optional.

---

## 1. Human Review UI

**Observable behavior:**

- [ ] Uploading a loan package and running the pipeline renders a report with labeled sections: Borrower Info, Document Checklist, Covenant Checks, Violations, Confidence Score
- [ ] Approve / Reject / Request More Info buttons are disabled before the report is generated
- [ ] Approve / Reject / Request More Info buttons are enabled after the report is generated
- [ ] Submitting a review without entering a reviewer name is blocked (button inactive or error displayed)
- [ ] After submitting with a name and decision, a decision summary appears showing: reviewer name, decision, timestamp, and notes (if any)
- [ ] The decision summary includes language indicating the decision is reviewer-owned (e.g. "Reviewer decision:" prefix)

**Tests that must pass:**

- `test_review_buttons_disabled_without_report`
- `test_review_buttons_enabled_with_report`
- `test_review_capture_stores_decision`
- `test_review_requires_reviewer_name`

---

## 2. Graceful Failure Handling

**Observable behavior:**

- [ ] Uploading an empty `.txt` file displays a clear error message and does not trigger the pipeline
- [ ] Uploading an unreadable (non-UTF-8) file displays a clear error message and does not trigger the pipeline
- [ ] With `ANTHROPIC_API_KEY` unset: a warning appears in the sidebar and the file upload widget is disabled on startup
- [ ] A simulated API timeout surfaces a user-facing error message with a retry option — no Python traceback visible in the UI
- [ ] A simulated malformed LLM response (first call) triggers a retry; if the retry also fails, a partial report (`is_partial = True`) is displayed with an error note
- [ ] Chroma returning no results does not abort the pipeline; the report displays with a note that no policy sections were found

**Tests that must pass:**

- `test_empty_file_triggers_error`
- `test_malformed_llm_retries_once`
- `test_malformed_llm_second_failure_partial_report`
- `test_no_chroma_results_continues_pipeline`
- `test_missing_api_key_disables_upload`

---

## 3. Privacy Controls

**Observable behavior:**

- [ ] Uploading a file containing an SSN pattern (e.g. `123-45-6789`) displays a PII warning before the report is shown
- [ ] Uploading a file containing a 12-digit digit sequence displays a PII warning
- [ ] Uploading a file with no PII patterns displays no warning
- [ ] Clicking "Clear Session" in the sidebar resets all session state (report gone, buttons disabled, upload reset)
- [ ] No loan text appears in terminal stdout when running `streamlit run app/main.py` with a sample upload
- [ ] `chroma_db/` contains no loan package data (only credit policy chunks); verify by inspecting collection metadata after a full run

**Tests that must pass:**

- `test_pii_ssn_pattern_triggers_warning`
- `test_pii_account_number_triggers_warning`
- `test_no_pii_no_warning`
- `test_clear_session_resets_state`

---

## 4. Confidence Score Display

**Observable behavior:**

- [ ] A report with score ≥ 80 renders the score block with a green indicator (`st.success`)
- [ ] A report with score 50–79 renders the score block with an amber indicator (`st.warning`)
- [ ] A report with score < 50 renders the score block with a red indicator (`st.error`)
- [ ] An expandable "Score rationale" section is present and shows the rationale string and factors list
- [ ] A partial report (`is_partial = True`) includes a note in the rationale expander explaining the impact on the score

**Tests that must pass:**

- `test_confidence_green_at_80`
- `test_confidence_amber_at_65`
- `test_confidence_red_at_40`
- `test_confidence_expander_shows_rationale`

---

## 5. Audit Trail

**Observable behavior:**

- [ ] Every generated `ComplianceReport` has a non-null `generated_at` (UTC datetime)
- [ ] Every generated `ComplianceReport` has a non-empty `model_used` string
- [ ] Every generated `ComplianceReport` has a non-empty `policy_version` string
- [ ] After a reviewer submits a decision, `report.reviewer_decision` is set and contains name, decision, notes, and timestamp
- [ ] The UI displays an "Audit info" expander at the bottom of the report with: timestamp, model used, policy version, confidence score

**Tests that must pass:**

- `test_report_has_generated_at`
- `test_report_has_model_used`
- `test_report_has_policy_version`
- `test_audit_reviewer_decision_appended`

---

## 6. Integration & Edge Cases

**Tests that must pass:**

- `test_full_pipeline_with_sample_loan` — full pipeline run on `data/sample_loan_package.txt` with mocked Claude; `ComplianceReport` returned with all required fields populated
- `test_empty_file_no_exception` — uploading an empty file raises no unhandled exception anywhere in the call stack
- `test_truncated_loan_package` — a loan package missing several key fields yields a report with `is_partial = True`
- `test_all_violations_package` — a loan package with all policy thresholds violated produces a non-empty violations list

---

## How to Run the Test Suite

```bash
pytest tests/test_phase3.py -v
```

All tests must pass. No test may be skipped or marked `xfail` without an approved justification added to this file.

---

## Manual Smoke Test (Run After All Tests Pass)

1. `streamlit run app/main.py`
2. Upload `data/sample_loan_package.txt`
3. Confirm: report renders with all sections, confidence score is color-coded, audit expander is present
4. Enter a reviewer name and click Approve
5. Confirm: decision summary appears with name, decision, and timestamp
6. Click "Clear Session" in the sidebar
7. Confirm: UI resets to initial state with no report and disabled buttons

Phase 3 is ready to merge when all tests pass and the manual smoke test completes without error.
