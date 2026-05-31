"""
pipeline/nodes/extract_metadata.py

LangGraph node: extract_metadata
Calls Claude with a structured tool to extract loan package fields.
Missing fields are recorded as None and appended to errors.
"""

import os
import anthropic
from pipeline.state import PipelineState

_client: anthropic.Anthropic | None = None

_EXTRACTION_TOOL = {
    "name": "extract_loan_metadata",
    "description": (
        "Extract structured metadata from a commercial loan package. "
        "Omit any field that cannot be found in the document."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "borrower_name": {
                "type": "string",
                "description": "Legal name of the borrower entity",
            },
            "loan_amount": {
                "type": "number",
                "description": "Requested loan amount in dollars (e.g., 4200000)",
            },
            "dscr": {
                "type": "number",
                "description": (
                    "Pro forma or most recent combined DSCR as a decimal "
                    "(e.g., 1.10 for 1.10x). Use the combined pro forma figure "
                    "when available."
                ),
            },
            "ltv": {
                "type": "number",
                "description": (
                    "Effective LTV as a percentage. Per policy, use the lesser of "
                    "appraised value or purchase price as the denominator "
                    "(e.g., 84.0 for 84%)."
                ),
            },
            "industry": {
                "type": "string",
                "description": "Industry or sector of the borrower business",
            },
            "document_list": {
                "type": "array",
                "description": "Documents referenced in the loan package",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Document name"},
                        "status": {
                            "type": "string",
                            "enum": ["present", "missing", "pending"],
                            "description": "Whether the document is present, missing, or pending",
                        },
                    },
                    "required": ["name", "status"],
                },
            },
        },
    },
}

_REQUIRED_FIELDS = ["borrower_name", "loan_amount", "dscr", "ltv", "industry"]


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def extract_metadata(state: PipelineState) -> dict:
    errors = list(state.get("errors", []))
    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            tools=[_EXTRACTION_TOOL],
            tool_choice={"type": "any"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract all available loan package metadata from the document below. "
                        "Use the extract_loan_metadata tool. Omit any field you cannot find.\n\n"
                        f"{state['raw_text']}"
                    ),
                }
            ],
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )

        if tool_block is None:
            errors.append("extract_metadata: Claude returned no tool_use block")
            extracted: dict = {}
        else:
            extracted = dict(tool_block.input)

        # Ensure all required fields are present; mark absent ones as None
        for field in _REQUIRED_FIELDS:
            if field not in extracted or extracted[field] is None:
                errors.append(f"extract_metadata: could not extract '{field}'")
                extracted[field] = None

        if "document_list" not in extracted:
            extracted["document_list"] = []

        return {"extracted_metadata": extracted, "errors": errors}

    except Exception as exc:
        errors.append(f"extract_metadata: exception — {exc}")
        return {
            "extracted_metadata": {f: None for f in _REQUIRED_FIELDS} | {"document_list": []},
            "errors": errors,
        }
