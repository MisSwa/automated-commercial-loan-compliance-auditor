"""
tests/test_phase2.py

Full test suite for Phase 2: Intelligence — LangGraph Pipeline + RAG.
All LLM calls are mocked — no real API calls are made.

Run from the project root:
    pytest tests/test_phase2.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.state import PipelineState
from pipeline.schemas import ComplianceReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (PROJECT_ROOT / "data" / "sample_loan_package.txt").read_text(encoding="utf-8")

_FULL_METADATA = {
    "borrower_name": "Hartfield Logistics Partners, LLC",
    "loan_amount": 4_200_000.0,
    "dscr": 1.10,
    "ltv": 84.0,
    "industry": "Logistics / Warehousing",
    "document_list": [
        {"name": "Business tax returns", "status": "present"},
        {"name": "Phase I Environmental Site Assessment", "status": "pending"},
    ],
}

_FULL_COMPLIANCE = {
    "covenant_checks": [
        {"item": "DSCR minimum 1.25x", "status": "fail", "policy_reference": "Section 1.1"},
        {"item": "LTV maximum 75%", "status": "fail", "policy_reference": "Section 2.1"},
        {"item": "Borrower credit score", "status": "pass", "policy_reference": "Section 4.1"},
    ],
    "violations": [
        {
            "description": "Combined pro forma DSCR of 1.10x is below the 1.15x eligibility floor",
            "policy_reference": "Section 1.3",
        },
        {
            "description": "Effective LTV of 84.0% exceeds the 75% maximum for industrial collateral",
            "policy_reference": "Section 2.1",
        },
    ],
    "recommended_next_steps": [
        "Return to borrower for revised financials",
        "Obtain Phase I Environmental Site Assessment",
    ],
}

_FULL_CONFIDENCE = {
    "score": 85,
    "rationale": "All required metadata fields extracted; policy coverage is thorough.",
    "factors": ["Complete metadata extraction", "Multiple policy sections retrieved"],
}


def _make_state(**overrides) -> PipelineState:
    base: PipelineState = {
        "raw_text": SAMPLE_TEXT,
        "extracted_metadata": None,
        "policy_chunks": [],
        "compliance_results": None,
        "confidence": None,
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


# ---------------------------------------------------------------------------
# Unit tests — extract_metadata node
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def test_happy_path(self):
        """Node correctly maps a valid tool_use response into extracted_metadata."""
        from pipeline.nodes.extract_metadata import extract_metadata

        with patch("pipeline.nodes.extract_metadata._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(_FULL_METADATA)
            result = extract_metadata(_make_state())

        meta = result["extracted_metadata"]
        assert meta["borrower_name"] == "Hartfield Logistics Partners, LLC"
        assert meta["dscr"] == 1.10
        assert meta["ltv"] == 84.0
        assert isinstance(meta["document_list"], list)
        assert result["errors"] == []

    def test_partial_extraction(self):
        """When Claude omits a field, it is None in state and errors is non-empty."""
        from pipeline.nodes.extract_metadata import extract_metadata

        partial_input = {
            "borrower_name": "Hartfield Logistics Partners, LLC",
            "loan_amount": 4_200_000.0,
            # dscr, ltv, industry intentionally omitted
            "document_list": [],
        }
        with patch("pipeline.nodes.extract_metadata._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(partial_input)
            result = extract_metadata(_make_state())

        meta = result["extracted_metadata"]
        assert meta["dscr"] is None
        assert meta["ltv"] is None
        assert meta["industry"] is None
        assert len(result["errors"]) >= 3  # at least dscr, ltv, industry


# ---------------------------------------------------------------------------
# Unit tests — retrieve_policy node
# ---------------------------------------------------------------------------

class TestRetrievePolicy:
    def test_returns_chunks(self):
        """Node populates policy_chunks when Chroma returns results."""
        from pipeline.nodes.retrieve_policy import retrieve_policy

        chunks = ["Section 1.1: DSCR minimum 1.25x...", "Section 2.1: LTV limits..."]
        with patch("pipeline.nodes.retrieve_policy.retrieve_policy_chunks", return_value=chunks):
            result = retrieve_policy(_make_state(extracted_metadata=_FULL_METADATA))

        assert result["policy_chunks"] == chunks
        assert result["errors"] == []

    def test_no_results(self):
        """When Chroma returns empty, 'policy section not found' appears in errors."""
        from pipeline.nodes.retrieve_policy import retrieve_policy

        with patch("pipeline.nodes.retrieve_policy.retrieve_policy_chunks", return_value=[]):
            result = retrieve_policy(_make_state(extracted_metadata=_FULL_METADATA))

        assert result["policy_chunks"] == []
        assert any("policy section not found" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Unit tests — check_compliance node
# ---------------------------------------------------------------------------

class TestCheckCompliance:
    def test_violations_mapped(self):
        """Node correctly maps a tool_use response into compliance_results."""
        from pipeline.nodes.check_compliance import check_compliance

        state = _make_state(
            extracted_metadata=_FULL_METADATA,
            policy_chunks=["Section 1.1: DSCR minimum 1.25x"],
        )
        with patch("pipeline.nodes.check_compliance._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(_FULL_COMPLIANCE)
            result = check_compliance(state)

        cr = result["compliance_results"]
        assert len(cr["violations"]) == 2
        assert any("Section 1.3" in v["policy_reference"] for v in cr["violations"])
        assert result["errors"] == []

    def test_unable_to_verify_for_none_fields(self):
        """Fields that were None in extracted_metadata produce unable_to_verify without LLM."""
        from pipeline.nodes.check_compliance import check_compliance

        partial_meta = dict(_FULL_METADATA)
        partial_meta["dscr"] = None
        partial_meta["ltv"] = None

        # LLM returns checks that don't mention dscr or ltv
        llm_result = {
            "covenant_checks": [
                {"item": "Borrower credit score", "status": "pass", "policy_reference": "Section 4.1"}
            ],
            "violations": [],
            "recommended_next_steps": [],
        }

        state = _make_state(
            extracted_metadata=partial_meta,
            policy_chunks=["Section 1.1: DSCR minimum 1.25x"],
        )
        with patch("pipeline.nodes.check_compliance._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(llm_result)
            result = check_compliance(state)

        statuses = {c["item"].lower(): c["status"] for c in result["compliance_results"]["covenant_checks"]}
        # The node should have appended unable_to_verify entries for dscr and ltv
        assert any("dscr" in item for item in statuses)
        assert any("ltv" in item for item in statuses)
        assert statuses[next(k for k in statuses if "dscr" in k)] == "unable_to_verify"


# ---------------------------------------------------------------------------
# Unit tests — score_confidence node
# ---------------------------------------------------------------------------

class TestScoreConfidence:
    def test_score_returned(self):
        """Node returns confidence dict with score, rationale, factors."""
        from pipeline.nodes.score_confidence import score_confidence

        state = _make_state(
            extracted_metadata=_FULL_METADATA,
            compliance_results=_FULL_COMPLIANCE,
        )
        with patch("pipeline.nodes.score_confidence._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(_FULL_CONFIDENCE)
            result = score_confidence(state)

        conf = result["confidence"]
        assert conf["score"] == 85
        assert isinstance(conf["rationale"], str)
        assert isinstance(conf["factors"], list)

    def test_floor_rule_applied(self):
        """When >50% of required fields are None, score is capped at 40."""
        from pipeline.nodes.score_confidence import score_confidence

        # 3 of 5 required fields are None (>50%)
        sparse_meta = {
            "borrower_name": None,
            "loan_amount": None,
            "dscr": None,
            "ltv": 84.0,
            "industry": "Logistics",
            "document_list": [],
        }
        high_score_input = {"score": 90, "rationale": "Great extraction", "factors": []}

        state = _make_state(
            extracted_metadata=sparse_meta,
            compliance_results=_FULL_COMPLIANCE,
        )
        with patch("pipeline.nodes.score_confidence._get_client") as mock_get:
            mock_get.return_value.messages.create.return_value = _tool_response(high_score_input)
            result = score_confidence(state)

        assert result["confidence"]["score"] <= 40
        assert any("capped" in f.lower() for f in result["confidence"]["factors"])


# ---------------------------------------------------------------------------
# Unit tests — generate_report node
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_valid_report(self):
        """Full state produces a valid ComplianceReport with is_partial=False."""
        from pipeline.nodes.generate_report import generate_report

        state = _make_state(
            extracted_metadata=_FULL_METADATA,
            compliance_results=_FULL_COMPLIANCE,
            confidence=_FULL_CONFIDENCE,
        )
        result = generate_report(state)

        report = result["report"]
        assert isinstance(report, ComplianceReport)
        assert report.is_partial is False
        assert report.borrower_name == "Hartfield Logistics Partners, LLC"
        assert report.confidence_score == 85
        assert len(report.violations) == 2

    def test_partial_flag_set(self):
        """State with None metadata fields produces ComplianceReport with is_partial=True."""
        from pipeline.nodes.generate_report import generate_report

        partial_meta = dict(_FULL_METADATA)
        partial_meta["dscr"] = None

        state = _make_state(
            extracted_metadata=partial_meta,
            compliance_results=_FULL_COMPLIANCE,
            confidence=_FULL_CONFIDENCE,
        )
        result = generate_report(state)

        assert result["report"].is_partial is True


# ---------------------------------------------------------------------------
# Integration test — full pipeline end-to-end (mocked LLM + real Chroma)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_full_pipeline_sample_loan(self):
        """
        End-to-end: run_pipeline(sample_loan_text) with mocked LLM returns
        a populated ComplianceReport.

        Chroma retrieval is NOT mocked — it uses the real vector store built
        in Phase 1.  Only the three Anthropic API calls are mocked.
        """
        from pipeline.graph import run_pipeline, _build_graph
        import pipeline.graph as graph_module

        # Reset the compiled graph so our test gets a fresh one
        graph_module._compiled = None

        # We mock the three node-level clients independently
        extract_response = _tool_response(_FULL_METADATA)
        compliance_response = _tool_response(_FULL_COMPLIANCE)
        confidence_response = _tool_response(_FULL_CONFIDENCE)

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return extract_response
            elif call_count == 2:
                return compliance_response
            else:
                return confidence_response

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = fake_create

        with (
            patch("pipeline.nodes.extract_metadata._get_client", return_value=mock_client),
            patch("pipeline.nodes.check_compliance._get_client", return_value=mock_client),
            patch("pipeline.nodes.score_confidence._get_client", return_value=mock_client),
        ):
            report = run_pipeline(SAMPLE_TEXT)

        # Core assertions — roadmap acceptance criteria
        assert report is not None, "run_pipeline returned None"
        assert isinstance(report, ComplianceReport)
        assert isinstance(report.violations, list), "violations should be a list"
        assert isinstance(report.confidence_score, int), "confidence_score should be int"
        assert 0 <= report.confidence_score <= 100, "confidence_score out of range"
        assert isinstance(report.is_partial, bool)
        # Chroma was live — should have retrieved chunks → covenant_checks present
        assert isinstance(report.covenant_checks, list)
        # Sample loan has deliberate violations
        assert len(report.violations) > 0, "Expected at least one violation on the sample loan"
        # Each violation must cite a policy reference
        for v in report.violations:
            assert v.policy_reference, f"Violation missing policy_reference: {v.description}"
