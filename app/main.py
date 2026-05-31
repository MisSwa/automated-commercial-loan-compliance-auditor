import os
import re
import streamlit as st
from datetime import datetime, timezone
from dotenv import load_dotenv

from pipeline.schemas import ComplianceReport

load_dotenv()


# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    (re.compile(r"\d{3}-\d{2}-\d{4}"), "SSN pattern"),
    (re.compile(r"\b\d{10,17}\b"), "account number (10–17 digits)"),
    (re.compile(r"\b(SSN|Account\s*#|EIN)\s*:", re.IGNORECASE), "sensitive identifier label"),
]


def _detect_pii(text: str) -> list[str]:
    """Return list of PII type descriptions found in text."""
    if not isinstance(text, str):
        return []
    return [label for pattern, label in _PII_PATTERNS if pattern.search(text)]


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------

def _validate_upload_text(raw_text: str) -> str | None:
    """Return an error message if raw_text is invalid, else None."""
    if not raw_text or not raw_text.strip():
        return "Uploaded file is empty."
    return None


# ---------------------------------------------------------------------------
# API key check
# ---------------------------------------------------------------------------

def _upload_disabled() -> bool:
    """Return True if file upload should be disabled (API key missing or empty)."""
    return not os.environ.get("ANTHROPIC_API_KEY", "").strip()


# ---------------------------------------------------------------------------
# Confidence color
# ---------------------------------------------------------------------------

def _confidence_color(score: int) -> str:
    """Return 'green', 'amber', or 'red' based on score thresholds."""
    if score >= 80:
        return "green"
    if score >= 50:
        return "amber"
    return "red"


# ---------------------------------------------------------------------------
# Review panel helpers
# ---------------------------------------------------------------------------

def _review_panel_disabled(report) -> bool:
    """Return True if review panel should be disabled (no valid report yet)."""
    return not isinstance(report, ComplianceReport)


def _build_reviewer_decision(name: str, decision: str, notes: str) -> dict:
    """Build a reviewer decision dict with a UTC timestamp."""
    return {
        "name": name,
        "decision": decision,
        "notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Status label
# ---------------------------------------------------------------------------

def _status_label(status: str) -> str:
    return {
        "pass": "[PASS]",
        "fail": "[FAIL]",
        "unable_to_verify": "[UNVERIFIED]",
        "present": "[PRESENT]",
        "missing": "[MISSING]",
        "pending": "[PENDING]",
    }.get(status, f"[{status.upper()}]")


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(report: ComplianceReport) -> None:
    """Render a ComplianceReport in the Streamlit UI."""
    if report.is_partial:
        missing = [e for e in report.pipeline_errors if "could not extract" in e]
        warning_msg = (
            "Partial extraction — some fields could not be determined from the loan package."
        )
        if missing:
            fields = ", ".join(e.split("'")[1] for e in missing if "'" in e)
            warning_msg += f" Affected fields: **{fields}**."
        st.warning(warning_msg)

    # Borrower + Loan Summary
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Borrower Information")
        st.write(f"**Name:** {report.borrower_name or '_Unable to extract_'}")
        st.write(f"**Industry:** {report.industry or '_Unable to extract_'}")
    with col2:
        st.subheader("Loan Summary")
        loan_amt = (
            f"${report.loan_amount:,.0f}"
            if report.loan_amount is not None
            else "_Unable to extract_"
        )
        dscr_val = (
            f"{report.dscr:.2f}x" if report.dscr is not None else "_Unable to extract_"
        )
        ltv_val = (
            f"{report.ltv:.1f}%" if report.ltv is not None else "_Unable to extract_"
        )
        st.write(f"**Loan Amount:** {loan_amt}")
        st.write(f"**DSCR (pro forma):** {dscr_val}")
        st.write(f"**LTV (effective):** {ltv_val}")

    st.divider()

    # Document Checklist
    st.subheader("Document Checklist")
    if report.documents:
        for doc in report.documents:
            st.write(f"{_status_label(doc.status)} {doc.name}")
    else:
        st.caption("No document information extracted.")

    st.divider()

    # Covenant Checks
    st.subheader("Covenant Checks")
    if report.covenant_checks:
        for check in report.covenant_checks:
            st.write(
                f"{_status_label(check.status)} **{check.item}** | _{check.policy_reference}_"
            )
    else:
        st.caption("No covenant checks available.")

    st.divider()

    # Violations
    st.subheader("Violations")
    if report.violations:
        for v in report.violations:
            st.error(f"**{v.description}** | Policy ref: _{v.policy_reference}_")
    else:
        st.success("No violations identified.")

    st.divider()

    # Confidence Score — color-coded
    st.subheader("Confidence Score")
    score = report.confidence_score
    color = _confidence_color(score)
    score_label = f"Confidence Score: {score}/100"
    if color == "green":
        st.success(score_label)
    elif color == "amber":
        st.warning(score_label)
    else:
        st.error(score_label)

    with st.expander("Score rationale", expanded=False):
        if report.confidence_rationale:
            st.write(report.confidence_rationale)
        if report.confidence_factors:
            st.write("**Factors:**")
            for factor in report.confidence_factors:
                st.write(f"- {factor}")
        if report.is_partial:
            st.caption(
                "Note: partial extraction was detected and may have reduced the confidence score."
            )

    # Recommended Next Steps
    if report.recommended_next_steps:
        st.divider()
        st.subheader("Recommended Next Steps")
        st.caption("Informational only — all decisions are made by the human reviewer.")
        for step in report.recommended_next_steps:
            st.write(f"- {step}")

    # Pipeline diagnostic messages (collapsed)
    if report.pipeline_errors:
        with st.expander("Pipeline diagnostic messages", expanded=False):
            for err in report.pipeline_errors:
                st.caption(err)

    # Audit info (collapsed)
    st.divider()
    with st.expander("Audit info", expanded=False):
        if report.generated_at:
            st.write(
                f"**Generated at:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
        st.write(f"**Model used:** {report.model_used}")
        st.write(f"**Policy version:** {report.policy_version}")
        st.write(f"**Confidence score:** {report.confidence_score}/100")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Loan Compliance Auditor",
        page_icon=None,
        layout="wide",
    )

    upload_disabled = _upload_disabled()

    with st.sidebar:
        st.markdown("## Loan Compliance Auditor")
        st.markdown("---")
        if upload_disabled:
            st.warning(
                "ANTHROPIC_API_KEY is not set. File upload is disabled. "
                "Add it to your .env file and restart the app."
            )
        st.markdown("**Phase 3 — Polish**")
        st.info(
            "Upload a loan package to run the compliance pipeline. "
            "Claude extracts metadata and checks it against the credit policy."
        )
        st.markdown("---")
        st.caption("Meridian Commercial Bank | Internal Use Only")
        st.markdown("---")
        if st.button("Clear Session", help="Reset all session state and start over."):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.title("Automated Commercial Loan Compliance Auditor")
    st.caption(
        "Pre-screening tool for underwriting compliance review. "
        "This system surfaces findings only — all final decisions are made by a human reviewer."
    )

    st.divider()

    # ------------------------------------------------------------------ #
    # Section 1: Upload
    # ------------------------------------------------------------------ #
    st.header("1. Upload Loan Package")

    uploaded_file = st.file_uploader(
        "Upload a loan package (.txt)",
        type=["txt"],
        disabled=upload_disabled,
        help="Upload the borrower's unstructured loan submission as a plain-text file.",
    )

    if uploaded_file is not None:
        # Decode — catch encoding errors
        try:
            raw_text: str | None = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            st.error(
                "Uploaded file is empty or could not be read. "
                "Please upload a valid UTF-8 plain-text file."
            )
            raw_text = None

        # Validate content
        if raw_text is not None:
            error_msg = _validate_upload_text(raw_text)
            if error_msg:
                st.error(error_msg)
                raw_text = None

        if raw_text:
            # PII warning (non-blocking)
            pii_hits = _detect_pii(raw_text)
            if pii_hits:
                st.warning(
                    "This file may contain sensitive personal information (PII): "
                    f"{', '.join(pii_hits)}. "
                    "It will not be stored beyond this session."
                )

            st.success(
                f"File received: **{uploaded_file.name}** ({len(raw_text):,} characters)"
            )
            with st.expander("View raw loan package", expanded=False):
                st.text(raw_text)

            # Run pipeline — cache by file identity so Streamlit re-renders don't re-run
            cache_key = f"{uploaded_file.name}:{len(raw_text)}"
            if st.session_state.get("_report_cache_key") != cache_key:
                with st.spinner("Running compliance pipeline — this may take a moment..."):
                    import anthropic
                    from pipeline.graph import run_pipeline
                    try:
                        result = run_pipeline(raw_text)
                        st.session_state["_report"] = result
                        st.session_state["_report_cache_key"] = cache_key
                        st.session_state["_pipeline_error"] = None
                    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
                        st.session_state["_pipeline_error"] = (
                            f"LLM call timed out or connection failed: {exc}. "
                            "Check your network connection and retry."
                        )
                        st.session_state["_report"] = None
                        st.session_state["_report_cache_key"] = None
                    except Exception as exc:
                        st.session_state["_pipeline_error"] = f"Pipeline error: {exc}"
                        st.session_state["_report"] = None
                        st.session_state["_report_cache_key"] = None

            if st.session_state.get("_pipeline_error"):
                st.error(st.session_state["_pipeline_error"])
                if st.button("Retry", help="Re-run the compliance pipeline on this file."):
                    st.session_state["_pipeline_error"] = None
                    st.rerun()

    st.divider()

    # ------------------------------------------------------------------ #
    # Section 2: Compliance Report
    # ------------------------------------------------------------------ #
    st.header("2. Compliance Report")

    report = st.session_state.get("_report")

    if isinstance(report, ComplianceReport):
        render_report(report)
    else:
        st.info("No report generated yet. Upload a loan package to begin.")

        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Borrower Information")
                st.caption("_Awaiting pipeline output_")
            with col2:
                st.subheader("Loan Summary")
                st.caption("_Awaiting pipeline output_")

        st.subheader("Document Checklist")
        st.caption("_Awaiting pipeline output_")
        st.subheader("Covenant Checks")
        st.caption("_Awaiting pipeline output_")
        st.subheader("Violations")
        st.caption("_Awaiting pipeline output_")
        st.subheader("Confidence Score")
        st.caption("_Awaiting pipeline output_")

    st.divider()

    # ------------------------------------------------------------------ #
    # Section 3: Human Review
    # ------------------------------------------------------------------ #
    st.header("3. Human Review")

    panel_disabled = _review_panel_disabled(report)

    if panel_disabled:
        st.caption(
            "Awaiting compliance report before review is available. "
            "The system never approves or rejects a loan — this decision belongs to the reviewer."
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button(
                "Approve",
                disabled=True,
                use_container_width=True,
                help="Available after compliance report is generated.",
            )
        with col2:
            st.button(
                "Reject",
                disabled=True,
                use_container_width=True,
                help="Available after compliance report is generated.",
            )
        with col3:
            st.button(
                "Request More Info",
                disabled=True,
                use_container_width=True,
                help="Available after compliance report is generated.",
            )

    elif st.session_state.get("_review_submitted"):
        decision = st.session_state["_review_decision"]
        st.success("**Reviewer decision recorded.**")
        st.write(f"**Reviewer:** {decision['name']}")
        st.write(f"**Decision:** {decision['decision']}")
        if decision.get("notes"):
            st.write(f"**Notes:** {decision['notes']}")
        st.write(f"**Timestamp:** {decision['timestamp']}")
        st.caption(
            "Reviewer decision: this determination was made by the human reviewer. "
            "The system does not approve or reject loan applications."
        )

    else:
        st.caption(
            "Review the compliance report above, then record your decision below. "
            "The system never approves or rejects a loan — this decision belongs to you."
        )
        reviewer_name = st.text_input(
            "Reviewer name (required)",
            placeholder="Enter your full name",
            help="Your name is required before a decision can be submitted.",
        )
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Add any observations or context for the record.",
        )

        name_provided = bool(reviewer_name and reviewer_name.strip())
        button_help = "Enter your name above to enable this button." if not name_provided else ""

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Approve",
                disabled=not name_provided,
                use_container_width=True,
                help=button_help,
            ):
                dec = _build_reviewer_decision(reviewer_name, "Approve", notes)
                st.session_state["_review_decision"] = dec
                st.session_state["_review_submitted"] = True
                report.reviewer_decision = dec
                st.rerun()
        with col2:
            if st.button(
                "Reject",
                disabled=not name_provided,
                use_container_width=True,
                help=button_help,
            ):
                dec = _build_reviewer_decision(reviewer_name, "Reject", notes)
                st.session_state["_review_decision"] = dec
                st.session_state["_review_submitted"] = True
                report.reviewer_decision = dec
                st.rerun()
        with col3:
            if st.button(
                "Request More Info",
                disabled=not name_provided,
                use_container_width=True,
                help=button_help,
            ):
                dec = _build_reviewer_decision(reviewer_name, "Request More Info", notes)
                st.session_state["_review_decision"] = dec
                st.session_state["_review_submitted"] = True
                report.reviewer_decision = dec
                st.rerun()


main()
