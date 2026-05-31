import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def main():
    st.set_page_config(
        page_title="Loan Compliance Auditor",
        page_icon=None,
        layout="wide",
    )

    with st.sidebar:
        st.markdown("## Loan Compliance Auditor")
        st.markdown("---")
        st.markdown("**Phase 1 — UI Shell**")
        st.info("No AI active in this phase. Pipeline wires up in Phase 2.")
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

    raw_text = None
    if uploaded_file is not None:
        raw_text = uploaded_file.read().decode("utf-8")
        st.success(f"File received: **{uploaded_file.name}** ({len(raw_text):,} characters)")
        with st.expander("View raw loan package", expanded=False):
            st.text(raw_text)

    st.divider()

    # ------------------------------------------------------------------ #
    # Section 2: Compliance Report
    # ------------------------------------------------------------------ #
    st.header("2. Compliance Report")

    report_ready = False  # Phase 2 will populate this from pipeline state

    if not report_ready:
        st.info("No report generated yet. Upload a loan package to begin.")

        # Reserved layout — Phase 2 fills these sections
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
