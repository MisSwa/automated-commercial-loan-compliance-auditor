"""
pipeline/state.py

PipelineState — the typed dictionary passed between every LangGraph node.
Each node receives the full state and returns a partial update dict.
"""

from typing import TypedDict


class PipelineState(TypedDict):
    """State passed between LangGraph nodes in the compliance pipeline."""

    # Input
    raw_text: str

    # Set by extract_metadata
    extracted_metadata: dict | None  # keys: borrower_name, loan_amount, dscr, ltv, industry, document_list

    # Set by retrieve_policy
    policy_chunks: list[str]

    # Set by check_compliance
    compliance_results: dict | None  # keys: covenant_checks, violations, recommended_next_steps

    # Set by score_confidence
    confidence: dict | None  # keys: score, rationale, factors

    # Set by generate_report
    report: object | None  # ComplianceReport instance

    # Accumulated by any node that encounters a problem
    errors: list[str]
