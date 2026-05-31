"""
pipeline/nodes/score_confidence.py

LangGraph node: score_confidence
Asks Claude to assign a confidence score (0–100) based on extraction
completeness and policy coverage quality.

Deterministic floor rule: if more than half of the required metadata
fields are None, the score is capped at 40 regardless of Claude's output.
"""

import os
import anthropic
from pipeline.state import PipelineState

_client: anthropic.Anthropic | None = None

_SCORING_TOOL = {
    "name": "score_pipeline_confidence",
    "description": (
        "Assign a confidence score (0–100) to this compliance pipeline run "
        "based on how complete the metadata extraction was and how thoroughly "
        "the policy was covered."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Confidence score from 0 (no confidence) to 100 (complete confidence)",
            },
            "rationale": {
                "type": "string",
                "description": "Concise explanation of what drove the score up or down",
            },
            "factors": {
                "type": "array",
                "description": "Specific factors that affected the score",
                "items": {"type": "string"},
            },
        },
        "required": ["score", "rationale", "factors"],
    },
}

_REQUIRED_FIELDS = ["borrower_name", "loan_amount", "dscr", "ltv", "industry"]


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def score_confidence(state: PipelineState) -> dict:
    errors = list(state.get("errors", []))
    metadata = state.get("extracted_metadata") or {}
    compliance = state.get("compliance_results") or {}

    none_count = sum(1 for f in _REQUIRED_FIELDS if metadata.get(f) is None)
    floor_active = none_count > len(_REQUIRED_FIELDS) / 2  # >50% missing

    metadata_summary = "\n".join(
        f"  {f}: {'MISSING' if metadata.get(f) is None else metadata[f]}"
        for f in _REQUIRED_FIELDS
    )
    compliance_summary = (
        f"  Covenant checks: {len(compliance.get('covenant_checks', []))}\n"
        f"  Violations: {len(compliance.get('violations', []))}"
    )
    error_summary = "\n".join(errors) if errors else "None"

    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            tools=[_SCORING_TOOL],
            tool_choice={"type": "any"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Assess the confidence of this compliance pipeline run.\n\n"
                        f"METADATA EXTRACTION:\n{metadata_summary}\n\n"
                        f"COMPLIANCE RESULTS:\n{compliance_summary}\n\n"
                        f"PIPELINE ERRORS:\n{error_summary}\n\n"
                        "Score 0–100. Higher scores mean the extraction was complete "
                        "and policy was well-covered. Use the score_pipeline_confidence tool."
                    ),
                }
            ],
        )

        tool_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )

        if tool_block is None:
            errors.append("score_confidence: Claude returned no tool_use block")
            return {
                "confidence": {"score": 0, "rationale": "Score unavailable", "factors": []},
                "errors": errors,
            }

        result: dict = dict(tool_block.input)
        result.setdefault("score", 0)
        result.setdefault("rationale", "")
        result.setdefault("factors", [])

        # Clamp to valid range before applying floor
        result["score"] = max(0, min(100, int(result["score"])))

        if floor_active:
            if result["score"] > 40:
                result["score"] = 40
            result["factors"] = list(result["factors"]) + [
                f"Score capped at 40: {none_count} of {len(_REQUIRED_FIELDS)} "
                "required fields could not be extracted"
            ]

        return {"confidence": result, "errors": errors}

    except Exception as exc:
        errors.append(f"score_confidence: exception — {exc}")
        return {
            "confidence": {"score": 0, "rationale": "Score unavailable", "factors": []},
            "errors": errors,
        }
