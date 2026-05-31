"""
pipeline/nodes/check_compliance.py

LangGraph node: check_compliance
Claude cross-references extracted loan metadata against retrieved policy chunks
and returns structured covenant checks, violations, and recommended next steps.
Fields that could not be extracted are automatically marked 'unable_to_verify'.
"""

import os
import anthropic
from pipeline.state import PipelineState

_client: anthropic.Anthropic | None = None

_COMPLIANCE_TOOL = {
    "name": "check_loan_compliance",
    "description": (
        "Cross-reference loan metadata against credit policy sections. "
        "Return every applicable covenant check, all violations found, "
        "and recommended next steps for the human reviewer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "covenant_checks": {
                "type": "array",
                "description": "All applicable policy covenant checks",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "The covenant or policy requirement being checked",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pass", "fail", "unable_to_verify"],
                            "description": "Result of the check",
                        },
                        "policy_reference": {
                            "type": "string",
                            "description": "Specific policy section (e.g., 'Section 1.1')",
                        },
                    },
                    "required": ["item", "status", "policy_reference"],
                },
            },
            "violations": {
                "type": "array",
                "description": "Policy violations identified",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Clear description of the violation",
                        },
                        "policy_reference": {
                            "type": "string",
                            "description": "The policy section that is violated",
                        },
                    },
                    "required": ["description", "policy_reference"],
                },
            },
            "recommended_next_steps": {
                "type": "array",
                "description": (
                    "Informational next steps for the human reviewer. "
                    "These are suggestions only — not decisions."
                ),
                "items": {"type": "string"},
            },
        },
        "required": ["covenant_checks", "violations", "recommended_next_steps"],
    },
}

_REQUIRED_FIELDS = ["borrower_name", "loan_amount", "dscr", "ltv", "industry"]

_EMPTY_RESULTS: dict = {
    "covenant_checks": [],
    "violations": [],
    "recommended_next_steps": [],
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def check_compliance(state: PipelineState) -> dict:
    errors = list(state.get("errors", []))
    metadata = state.get("extracted_metadata") or {}
    policy_chunks = state.get("policy_chunks") or []

    # Identify fields that were not extractable — these must be unable_to_verify
    none_fields = [
        f for f in _REQUIRED_FIELDS if metadata.get(f) is None
    ]

    policy_text = (
        "\n\n---\n\n".join(policy_chunks)
        if policy_chunks
        else "No policy sections retrieved."
    )

    metadata_lines = "\n".join(
        f"  {k}: {'MISSING — unable to verify' if v is None else v}"
        for k, v in metadata.items()
        if k != "document_list"
    )

    doc_list = metadata.get("document_list") or []
    doc_lines = (
        "\n".join(f"  - {d['name']}: {d['status']}" for d in doc_list)
        if doc_list
        else "  No document list available."
    )

    client = _get_client()

    try:
        _kwargs = dict(
            model="claude-opus-4-6",
            max_tokens=2048,
            tools=[_COMPLIANCE_TOOL],
            tool_choice={"type": "any"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a commercial lending compliance officer. "
                        "Cross-reference the loan metadata below against the credit policy sections "
                        "and identify all violations and covenant checks.\n\n"
                        f"LOAN METADATA:\n{metadata_lines}\n\n"
                        f"SUBMITTED DOCUMENTS:\n{doc_lines}\n\n"
                        f"CREDIT POLICY SECTIONS:\n{policy_text}\n\n"
                        "Instructions:\n"
                        "- For each covenant in the policy, produce a check with pass/fail/unable_to_verify.\n"
                        "- Any metadata field marked MISSING must be 'unable_to_verify'.\n"
                        "- Every violation must cite the specific policy section number.\n"
                        "- Recommended next steps are informational only — no loan decisions.\n"
                        "Use the check_loan_compliance tool."
                    ),
                }
            ],
        )

        response = client.messages.create(**_kwargs)
        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )

        if tool_block is None:
            # Retry once before falling back
            response = client.messages.create(**_kwargs)
            tool_block = next(
                (b for b in response.content if b.type == "tool_use"), None
            )

        if tool_block is None:
            errors.append("check_compliance: Claude returned no tool_use block after retry")
            return {"compliance_results": dict(_EMPTY_RESULTS), "errors": errors}

        results: dict = dict(tool_block.input)
        results.setdefault("covenant_checks", [])
        results.setdefault("violations", [])
        results.setdefault("recommended_next_steps", [])

        # Guarantee unable_to_verify entries for all None fields
        existing_items_lower = {
            c["item"].lower() for c in results["covenant_checks"]
        }
        for field in none_fields:
            label = field.replace("_", " ").upper()
            if not any(field.lower() in item for item in existing_items_lower):
                results["covenant_checks"].append(
                    {
                        "item": f"{label} check",
                        "status": "unable_to_verify",
                        "policy_reference": "N/A — field could not be extracted",
                    }
                )

        return {"compliance_results": results, "errors": errors}

    except Exception as exc:
        errors.append(f"check_compliance: exception — {exc}")
        return {"compliance_results": dict(_EMPTY_RESULTS), "errors": errors}
