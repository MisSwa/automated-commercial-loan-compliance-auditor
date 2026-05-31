"""
pipeline/schemas.py

Pydantic models for the final ComplianceReport output.
This is the single validated output artifact produced by the pipeline.
Pipeline state uses plain TypedDict; Pydantic is reserved for this schema only.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentStatus(BaseModel):
    name: str
    status: str  # "present" | "missing" | "pending"


class CovenantCheck(BaseModel):
    item: str
    status: str  # "pass" | "fail" | "unable_to_verify"
    policy_reference: str


class Violation(BaseModel):
    description: str
    policy_reference: str


class ComplianceReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    # Borrower metadata
    borrower_name: Optional[str] = None
    loan_amount: Optional[float] = None
    dscr: Optional[float] = None
    ltv: Optional[float] = None
    industry: Optional[str] = None

    # Checklist and covenant findings
    documents: list[DocumentStatus] = []
    covenant_checks: list[CovenantCheck] = []
    violations: list[Violation] = []

    # Confidence
    confidence_score: int = 0
    confidence_rationale: str = ""
    confidence_factors: list[str] = []

    # Recommended next steps (informational only — not a decision)
    recommended_next_steps: list[str] = []

    # Partial extraction flag — True if any required metadata field is None
    is_partial: bool = False

    # Errors accumulated during the pipeline run (for transparency)
    pipeline_errors: list[str] = []

    # Audit trail
    generated_at: Optional[datetime] = None
    model_used: str = "claude-opus-4-6"
    policy_version: str = "2.1"
    reviewer_decision: Optional[dict] = None
