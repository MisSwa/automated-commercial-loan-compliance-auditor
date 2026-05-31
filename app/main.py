import streamlit as st
from dotenv import load_dotenv

from pipeline.schemas import ComplianceReport

load_dotenv()


# ---------------------------------------------------------------------------
# Report rendering
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


def render_report(report) -> None:
    """Render a ComplianceReport in the Streamlit UI."""
    if report.is_partial:
        missing = [e for e in report.pipeline_errors if "could not extract" in e]
        warning_msg = "Partial extraction — some fields could not be determined from the loan package."
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
            f"${report.loan_amount:,.0f}" if report.loan_amount is not None else "_Unable to extract_"
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
            label = _status_label(doc.status)
            st.write(f"{label} {doc.name}")
    else:
        st.caption("No document information extracted.")

    st.divider()

    # Covenant Checks
    st.subheader("Covenant Checks")
    if report.covenant_checks:
        for check in report.covenant_checks:
            label = _status_label(check.status)
            st.write(f"{label} **{check.item}** | _{check.policy_reference}_")
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

    # Confidence Score
    st.subheader("Confidence Score")
    st.metric("Score", f"{report.confidence_score} / 100")
    if report.confidence_rationale:
        st.caption(report.confidence_rationale)

    # Recommended Next Steps
    if report.recommended_next_steps:
        st.divider()
        st.subheader("Recommended Next Steps")
        st.caption("Informational only — all decisions are made by the human reviewer.")
        for step in report.recommended_next_steps:
            st.write(f"- {step}")

    # Pipeline errors (collapsed, for transparency)
    if report.pipeline_errors:
        with st.expander("Pipeline diagnostic messages", expanded=False):
            for err in report.pipeline_errors:
                st.caption(err)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Loan Compliance Auditor",
        page_icon=None,
        layout="wide",
    )

    with st.sidebar:
        st.markdown("## Loan Compliance Auditor")
        st.markdown("---")
        st.markdown("**Phase 2 — LangGraph Pipeline + RAG**")
        st.info(
            "Upload a loan package to run the compliance pipeline. "
            "Claude extracts metadata and checks it against the credit policy."
        )
        st.markdown("---")
        st.caption("Meridian Commercial Bank | Internal Use Only")

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
        help="Upload the borrower's unstructured loan submission as a plain-text file.",
    )

    report = None

    if uploaded_file is not None:
        raw_text = uploaded_file.read().decode("utf-8")
        st.success(f"File received: **{uploaded_file.name}** ({len(raw_text):,} characters)")

        with st.expander("View raw loan package", expanded=False):
            st.text(raw_text)

        # Use a cache key so we don't re-run on every Streamlit re-render
        cache_key = f"{uploaded_file.name}:{len(raw_text)}"
        if st.session_state.get("_report_cache_key") != cache_key:
            with st.spinner("Running compliance pipeline — this may take a moment..."):
                from pipeline.graph import run_pipeline
                try:
                    result = run_pipeline(raw_text)
                    st.session_state["_report"] = result
                    st.session_state["_report_cache_key"] = cache_key
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")
                    st.session_state["_report"] = None
                    st.session_state["_report_cache_key"] = None

        report = st.session_state.get("_report")

    st.divider()

    # ------------------------------------------------------------------ #
    # Section 2: Compliance Report
    # ------------------------------------------------------------------ #
    st.header("2. Compliance Report")

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
    # Section 3: Human Review Panel
    # ------------------------------------------------------------------ #
    st.header("3. Human Review")
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


main()
