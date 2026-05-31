"""
pipeline/nodes/generate_report.py

LangGraph node: generate_report
Assembles all pipeline state into a validated ComplianceReport Pydantic object.
Sets is_partial=True if any required metadata field is None.
On Pydantic ValidationError, returns a minimal partial report rather than raising.
"""

from datetime import datetime, timezone
from pydantic import ValidationError
from pipeline.state import PipelineState
from pipeline.schemas import ComplianceReport, CovenantCheck, DocumentStatus, Violation

_REQUIRED_FIELDS = ["borrower_name", "loan_amount", "dscr", "ltv", "industry"]
_MODEL_USED = "claude-opus-4-6"
_POLICY_VERSION = "2.1"


def generate_report(state: PipelineState) -> dict:
    errors = list(state.get("errors", []))
    metadata = state.get("extracted_metadata") or {}
    compliance = state.get("compliance_results") or {}
    confidence = state.get("confidence") or {}

    is_partial = any(metadata.get(f) is None for f in _REQUIRED_FIELDS)

    documents = [
        DocumentStatus(name=d["name"], status=d["status"])
        for d in (metadata.get("document_list") or [])
    ]

    covenant_checks = [
        CovenantCheck(
            item=c["item"],
            status=c["status"],
            policy_reference=c["policy_reference"],
        )
        for c in (compliance.get("covenant_checks") or [])
    ]

    violations = [
        Violation(
            description=v["description"],
            policy_reference=v["policy_reference"],
        )
        for v in (compliance.get("violations") or [])
    ]

    try:
        report = ComplianceReport(
            borrower_name=metadata.get("borrower_name"),
            loan_amount=metadata.get("loan_amount"),
            dscr=metadata.get("dscr"),
            ltv=metadata.get("ltv"),
            industry=metadata.get("industry"),
            documents=documents,
            covenant_checks=covenant_checks,
            violations=violations,
            confidence_score=int(confidence.get("score", 0)),
            confidence_rationale=confidence.get("rationale", ""),
            confidence_factors=list(confidence.get("factors", [])),
            recommended_next_steps=compliance.get("recommended_next_steps") or [],
            is_partial=is_partial,
            pipeline_errors=errors,
            generated_at=datetime.now(timezone.utc),
            model_used=_MODEL_USED,
            policy_version=_POLICY_VERSION,
        )
        return {"report": report, "errors": errors}

    except ValidationError as exc:
        errors.append(f"generate_report: validation error — {exc}")
        partial = ComplianceReport(
            borrower_name=metadata.get("borrower_name"),
            is_partial=True,
            pipeline_errors=errors,
            generated_at=datetime.now(timezone.utc),
            model_used=_MODEL_USED,
            policy_version=_POLICY_VERSION,
        )
        return {"report": partial, "errors": errors}
