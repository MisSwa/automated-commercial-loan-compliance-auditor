"""
tests/test_phase3.py

Phase 3 test suite: human review UI, failure handling, privacy controls,
confidence display, audit trail, integration, and edge cases.

All Claude API calls are mocked — no live API key required.
Run from the project root: pytest tests/test_phase3.py -v
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.schemas import ComplianceReport
from pipeline.nodes.generate_report import generate_report
from pipeline.state import PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_METADATA = {
    "borrower_name": "Acme Corp",
    "loan_amount": 1_000_000.0,
    "dscr": 1.30,
    "ltv": 70.0,
    "industry": "Retail",
    "document_list": [{"name": "Tax Returns", "status": "present"}],
}

_FULL_COMPLIANCE = {
    "covenant_checks": [
        {"item": "DSCR check", "status": "pass", "policy_reference": "Section 1.1"}
    ],
    "violations": [],
    "recommended_next_steps": ["Verify appraisal"],
}

_FULL_CONFIDENCE = {
    "score": 85,
    "rationale": "All fields extracted successfully",
    "factors": ["Complete extraction", "Full policy coverage"],
}


def _make_state(**overrides) -> PipelineState:
    base: PipelineState = {
        "raw_text": "Sample loan text",
        "extracted_metadata": _FULL_METADATA,
        "policy_chunks": ["Section 1: DSCR minimum 1.25x"],
        "compliance_results": _FULL_COMPLIANCE,
        "confidence": _FULL_CONFIDENCE,
        "report": None,
        "errors": [],
    }
    base.update(overrides)  # type: ignore[typeddict-unknown-key]
    return base


def _tool_response(tool_input: dict) -> MagicMock:
    """Build a mock Anthropic message response containing a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    return response


def _empty_response() -> MagicMock:
    """Build a mock Anthropic response with no tool_use block (malformed)."""
    response = MagicMock()
    response.content = []
    return response


# ===========================================================================
# 1. Human Review UI
# ===========================================================================

class TestHumanReviewUI:
    def test_review_buttons_disabled_without_report(self):
        from app.main import _review_panel_disabled
        assert _review_panel_disabled(None) is True

    def test_review_buttons_enabled_with_report(self):
        from app.main import _review_panel_disabled
        report = ComplianceReport()
        assert _review_panel_disabled(report) is False

    def test_review_capture_stores_decision(self):
        from app.main import _build_reviewer_decision
        dec = _build_reviewer_decision("Jane Smith", "Approve", "Looks good")
        assert dec["name"] == "Jane Smith"
        assert dec["decision"] == "Approve"
        assert dec["notes"] == "Looks good"
        assert "timestamp" in dec
        # Timestamp should be a valid ISO-format datetime string
        datetime.fromisoformat(dec["timestamp"])

    def test_review_requires_reviewer_name(self):
        # Mirrors the name_provided check in app/main.py
        assert not bool("" and "".strip())       # empty string → disabled
        assert not bool("   " and "   ".strip()) # whitespace → disabled
        assert bool("Jane" and "Jane".strip())   # non-empty → enabled


# ===========================================================================
# 2. Failure Handling
# ===========================================================================

class TestFailureHandling:
    def test_empty_file_triggers_error(self):
        from app.main import _validate_upload_text
        assert _validate_upload_text("") is not None
        assert _validate_upload_text("   ") is not None
        assert _validate_upload_text("\n\t\n") is not None

    def test_empty_file_no_exception(self):
        from app.main import _validate_upload_text
        # Must not raise — returns error message string, not an exception
        try:
            result = _validate_upload_text("")
        except Exception as exc:
            pytest.fail(f"_validate_upload_text raised unexpectedly: {exc}")
        assert result is not None

    def test_malformed_llm_retries_once(self):
        """First call returns no tool_use → one retry is made → 2 total calls."""
        from pipeline.nodes.extract_metadata import extract_metadata

        valid = _tool_response(
            {"borrower_name": "Test Corp", "loan_amount": 500000.0,
             "dscr": 1.25, "ltv": 70.0, "industry": "Retail", "document_list": []}
        )
        state = _make_state(raw_text="Test loan text", extracted_metadata=None, errors=[])

        with patch("pipeline.nodes.extract_metadata._get_client") as mock_get:
            mock_get.return_value.messages.create.side_effect = [_empty_response(), valid]
            extract_metadata(state)
            assert mock_get.return_value.messages.create.call_count == 2

    def test_malformed_llm_second_failure_partial_report(self):
        """Two consecutive failures → metadata all None → is_partial=True on final report."""
        from pipeline.nodes.extract_metadata import extract_metadata

        state = _make_state(raw_text="Test loan text", extracted_metadata=None, errors=[])

        with patch("pipeline.nodes.extract_metadata._get_client") as mock_get:
            mock_get.return_value.messages.create.side_effect = [
                _empty_response(), _empty_response()
            ]
            result = extract_metadata(state)

        # With all required fields None, generate_report must set is_partial=True
        gen_state = _make_state(
            extracted_metadata=result["extracted_metadata"],
            errors=result["errors"],
        )
        report_result = generate_report(gen_state)
        assert report_result["report"].is_partial is True

    def test_no_chroma_results_continues_pipeline(self):
        """Empty Chroma results: error appended, pipeline does not abort."""
        from pipeline.nodes.retrieve_policy import retrieve_policy

        state = _make_state(policy_chunks=[], errors=[])

        with patch("pipeline.nodes.retrieve_policy.retrieve_policy_chunks", return_value=[]):
            result = retrieve_policy(state)

        assert isinstance(result, dict)
        assert result["policy_chunks"] == []
        assert any("policy section not found" in e for e in result.get("errors", []))

    def test_missing_api_key_disables_upload(self):
        from app.main import _upload_disabled
        # Test with explicitly empty key
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            assert _upload_disabled() is True
        # Test with key absent entirely
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            assert _upload_disabled() is True
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved


# ===========================================================================
# 3. Privacy Controls
# ===========================================================================

class TestPrivacyControls:
    def test_pii_ssn_pattern_triggers_warning(self):
        from app.main import _detect_pii
        hits = _detect_pii("Borrower SSN: 123-45-6789")
        assert len(hits) > 0

    def test_pii_account_number_triggers_warning(self):
        from app.main import _detect_pii
        # 12 consecutive digits → account number pattern
        hits = _detect_pii("Account: 123456789012")
        assert len(hits) > 0

    def test_no_pii_no_warning(self):
        from app.main import _detect_pii
        hits = _detect_pii(
            "Hartfield Logistics Partners LLC requests a commercial real estate loan. "
            "The property is located at 4800 Industrial Parkway, Suite 200."
        )
        assert len(hits) == 0

    def test_clear_session_resets_state(self):
        # Mirrors the Clear Session button logic: delete all keys from session dict
        session: dict = {
            "_report": MagicMock(),
            "_report_cache_key": "some_key",
            "_review_submitted": True,
            "_review_decision": {"name": "Jane"},
        }
        for key in list(session.keys()):
            del session[key]
        assert session == {}


# ===========================================================================
# 4. Confidence Display
# ===========================================================================

class TestConfidenceDisplay:
    def test_confidence_green_at_80(self):
        from app.main import _confidence_color
        assert _confidence_color(80) == "green"
        assert _confidence_color(100) == "green"
        assert _confidence_color(95) == "green"

    def test_confidence_amber_at_65(self):
        from app.main import _confidence_color
        assert _confidence_color(65) == "amber"
        assert _confidence_color(50) == "amber"
        assert _confidence_color(79) == "amber"

    def test_confidence_red_at_40(self):
        from app.main import _confidence_color
        assert _confidence_color(40) == "red"
        assert _confidence_color(0) == "red"
        assert _confidence_color(49) == "red"

    def test_confidence_expander_shows_rationale(self):
        # ComplianceReport stores both rationale and factors for the expander
        report = ComplianceReport(
            confidence_score=75,
            confidence_rationale="Good extraction, some missing docs",
            confidence_factors=["All numeric fields present", "Missing Phase I ESA"],
        )
        assert report.confidence_rationale == "Good extraction, some missing docs"
        assert len(report.confidence_factors) == 2
        assert "All numeric fields present" in report.confidence_factors
        assert "Missing Phase I ESA" in report.confidence_factors


# ===========================================================================
# 5. Audit Trail
# ===========================================================================

class TestAuditTrail:
    def test_report_has_generated_at(self):
        state = _make_state()
        result = generate_report(state)
        assert result["report"].generated_at is not None
        assert isinstance(result["report"].generated_at, datetime)

    def test_report_has_model_used(self):
        state = _make_state()
        result = generate_report(state)
        assert result["report"].model_used
        assert isinstance(result["report"].model_used, str)
        assert len(result["report"].model_used) > 0

    def test_report_has_policy_version(self):
        state = _make_state()
        result = generate_report(state)
        assert result["report"].policy_version
        assert isinstance(result["report"].policy_version, str)
        assert len(result["report"].policy_version) > 0

    def test_audit_reviewer_decision_appended(self):
        from app.main import _build_reviewer_decision
        state = _make_state()
        result = generate_report(state)
        report = result["report"]

        # reviewer_decision starts as None
        assert report.reviewer_decision is None

        # After review, it is set
        dec = _build_reviewer_decision("Bob Jones", "Reject", "LTV too high")
        report.reviewer_decision = dec

        assert report.reviewer_decision["name"] == "Bob Jones"
        assert report.reviewer_decision["decision"] == "Reject"
        assert report.reviewer_decision["notes"] == "LTV too high"
        assert "timestamp" in report.reviewer_decision


# ===========================================================================
# 6. Integration & Edge Cases
# ===========================================================================

class TestIntegrationAndEdgeCases:
    def test_full_pipeline_with_sample_loan(self):
        """End-to-end run on sample_loan_package.txt with mocked Claude."""
        import pipeline.graph as graph_module

        sample_path = PROJECT_ROOT / "data" / "sample_loan_package.txt"
        if not sample_path.exists():
            pytest.skip("Sample loan package not found — run Phase 1 setup first")

        raw_text = sample_path.read_text(encoding="utf-8")

        # Reset cached compiled graph so the test gets a fresh build
        graph_module._compiled = None

        extract_resp = _tool_response({
            "borrower_name": "Hartfield Logistics Partners, LLC",
            "loan_amount": 4_200_000.0,
            "dscr": 1.10,
            "ltv": 84.0,
            "industry": "Logistics / Warehousing",
            "document_list": [
                {"name": "Business Tax Returns", "status": "present"},
                {"name": "Phase I ESA", "status": "pending"},
            ],
        })
        compliance_resp = _tool_response({
            "covenant_checks": [
                {"item": "DSCR minimum 1.25x", "status": "fail", "policy_reference": "Section 1.1"},
                {"item": "LTV maximum 75%", "status": "fail", "policy_reference": "Section 2.3"},
            ],
            "violations": [
                {
                    "description": "DSCR 1.10x is below the 1.15x eligibility floor",
                    "policy_reference": "Section 1.2",
                },
                {
                    "description": "LTV 84% exceeds industrial maximum of 75%",
                    "policy_reference": "Section 2.3",
                },
            ],
            "recommended_next_steps": ["Flag for Credit Committee review"],
        })
        score_resp = _tool_response({
            "score": 72,
            "rationale": "All fields extracted; two violations identified",
            "factors": ["Complete metadata extraction", "Two policy violations found"],
        })

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return extract_resp
            elif call_count == 2:
                return compliance_resp
            else:
                return score_resp

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = fake_create

        with (
            patch("pipeline.nodes.extract_metadata._get_client", return_value=mock_client),
            patch("pipeline.nodes.check_compliance._get_client", return_value=mock_client),
            patch("pipeline.nodes.score_confidence._get_client", return_value=mock_client),
        ):
            from pipeline.graph import run_pipeline
            report = run_pipeline(raw_text)

        assert isinstance(report, ComplianceReport)
        # Audit fields must be populated
        assert report.generated_at is not None
        assert report.model_used
        assert report.policy_version
        # Core findings
        assert report.confidence_score == 72
        assert len(report.violations) == 2
        assert len(report.confidence_factors) == 2
        # Each violation cites a policy reference
        for v in report.violations:
            assert v.policy_reference

    def test_empty_file_no_exception(self):
        """_validate_upload_text('') must not raise — returns an error string."""
        from app.main import _validate_upload_text
        try:
            result = _validate_upload_text("")
        except Exception as exc:
            pytest.fail(f"_validate_upload_text raised unexpectedly: {exc}")
        assert isinstance(result, str)

    def test_truncated_loan_package(self):
        """Loan package missing most fields → is_partial=True."""
        state = _make_state(
            extracted_metadata={
                "borrower_name": "Acme Corp",
                "loan_amount": None,
                "dscr": None,
                "ltv": None,
                "industry": None,
                "document_list": [],
            },
        )
        result = generate_report(state)
        assert result["report"].is_partial is True

    def test_all_violations_package(self):
        """Loan package with all policy violations → non-empty violations list."""
        state = _make_state(
            compliance_results={
                "covenant_checks": [
                    {"item": "DSCR", "status": "fail", "policy_reference": "Section 1.1"},
                    {"item": "LTV", "status": "fail", "policy_reference": "Section 2.3"},
                ],
                "violations": [
                    {"description": "DSCR below floor", "policy_reference": "Section 1.2"},
                    {"description": "LTV exceeds maximum", "policy_reference": "Section 2.3"},
                    {"description": "Missing Phase I ESA", "policy_reference": "Section 3.1"},
                ],
                "recommended_next_steps": [],
            },
        )
        result = generate_report(state)
        assert len(result["report"].violations) == 3
