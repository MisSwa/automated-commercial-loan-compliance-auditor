# Requirements — Phase 3: Polish — Human Review, Error Handling & Privacy

## Scope

Phase 3 brings the prototype to production-quality readiness within the constraints of a local, session-only tool. No cloud deployment, no authentication, no persistent storage of borrower data.

This phase adds:
- A functional human review workflow with decision capture
- Complete error handling across all identified failure modes
- Privacy controls enforced at upload time and throughout the session
- Visual confidence score display with rationale
- Audit trail fields on every generated report
- A full test suite covering units, integration, and edge cases

---

## In Scope

### Human Review

- The compliance report must be rendered in a structured, readable format before the reviewer can act
- Review buttons (Approve / Reject / Request More Info) activate only after a report is present in session state
- The reviewer must supply their name before a decision can be submitted
- Decision capture stores: reviewer name, decision label, optional notes, and a timestamp
- The final display makes clear the decision is reviewer-owned, not system-generated
- No automated approval or rejection is emitted at any point

### Failure Handling

All failure modes identified in the roadmap must be handled explicitly:

| Failure | Behavior |
|---|---|
| Empty or unreadable file | `st.error` message; pipeline does not run |
| Malformed LLM output | Retry once; on second failure, partial report with error flag |
| No Chroma results | Error appended to state; pipeline continues |
| Missing/invalid API key | Startup warning in sidebar; upload widget disabled |
| API timeout or connection error | User-facing error with retry option |

No failure path may produce an unhandled Python exception visible in the Streamlit UI.

### Privacy Controls

- No loan package text is written to disk at any point
- The Chroma store (`chroma_db/`) contains only the credit policy document, never loan data
- PII detection runs on the raw file text before it enters the pipeline:
  - Triggers on: SSN patterns (`\d{3}-\d{2}-\d{4}`), long digit sequences (10–17 consecutive digits), and labeled identifiers (`SSN:`, `Account #`, `EIN:`)
  - On match: display a warning before proceeding — do not block the upload
- Session state is cleared on browser refresh (Streamlit default behavior)
- A manual "Clear Session" button in the sidebar allows explicit reset
- Raw loan text is never printed to stdout or logged anywhere in the pipeline

### Confidence Score Display

- Score is color-coded: green (≥ 80), amber (50–79), red (< 50)
- An expandable rationale section shows the score reasoning and contributing factors
- Partial extraction is noted in the rationale expander when `is_partial = True`

### Audit Trail

Every `ComplianceReport` object carries:

| Field | Description |
|---|---|
| `generated_at` | UTC datetime at report assembly |
| `model_used` | Claude model ID string used for LLM calls |
| `policy_version` | Fixed identifier for the credit policy document version queried |
| `confidence_score` | Integer score, top-level on the report for easy access |
| `reviewer_decision` | Set after reviewer submission; `None` until then |

Audit fields are immutable after report generation (only `reviewer_decision` is appended post-generation).

### Testing

- Unit tests for all five feature areas (review UI, failure handling, privacy, confidence display, audit trail)
- One integration test covering the full pipeline end-to-end with mocked LLM responses
- Edge case tests: empty file, truncated loan package, all-violations loan package
- No live API calls in any test — all Claude responses are mocked

---

## Out of Scope

These items are explicitly excluded from Phase 3 and must not be added:

- User authentication or role-based access
- Cloud deployment or containerization
- Persistent audit log database (report objects exist in session state only)
- Multi-file loan package support
- Streaming LLM output
- Styling beyond Streamlit's built-in `st.success` / `st.warning` / `st.error` components
- Any automated loan decision (approval or rejection) by the system

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| PII detection method | Regex pattern matching | Avoids an additional Claude call on every upload; patterns cover the primary identifiers in commercial loan packages |
| LLM retry strategy | Retry once on parse failure | Balances reliability against API cost; two consecutive failures are unlikely to resolve without user action |
| Policy version identifier | Static string or hash of `data/credit_policy.txt` | Policy document is fixed for this prototype; no versioning system needed |
| Reviewer decision storage | Appended to in-memory `ComplianceReport` | Session-only; no persistence required |
| Test isolation | Mock all Claude API calls | Tests must run without a live API key; mocking enforces this at the test boundary |

---

## Constraints

- Python 3.11+
- All dependencies already declared in `requirements.txt` from Phase 1
- `pytest` is the test runner; no additional test libraries beyond what is already in `requirements.txt`
- The tool runs locally only (`streamlit run app/main.py`)
- `ANTHROPIC_API_KEY` is the only required environment variable
