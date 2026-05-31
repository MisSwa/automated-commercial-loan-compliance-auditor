"""
pipeline/graph.py

Assembles the LangGraph StateGraph and exposes run_pipeline() as the
single entry point used by the Streamlit UI.

Graph topology:
  extract_metadata → retrieve_policy → check_compliance
                   → score_confidence → generate_report → END
"""

from langgraph.graph import StateGraph, END

from pipeline.state import PipelineState
from pipeline.nodes.extract_metadata import extract_metadata
from pipeline.nodes.retrieve_policy import retrieve_policy
from pipeline.nodes.check_compliance import check_compliance
from pipeline.nodes.score_confidence import score_confidence
from pipeline.nodes.generate_report import generate_report
from pipeline.schemas import ComplianceReport


def _build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("extract_metadata", extract_metadata)
    graph.add_node("retrieve_policy", retrieve_policy)
    graph.add_node("check_compliance", check_compliance)
    graph.add_node("score_confidence", score_confidence)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("extract_metadata")
    graph.add_edge("extract_metadata", "retrieve_policy")
    graph.add_edge("retrieve_policy", "check_compliance")
    graph.add_edge("check_compliance", "score_confidence")
    graph.add_edge("score_confidence", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


_compiled = None


def run_pipeline(raw_text: str) -> ComplianceReport:
    """
    Run the full compliance pipeline on raw loan package text.

    Args:
        raw_text: The full text content of the uploaded loan package.

    Returns:
        A validated ComplianceReport. Never raises — errors are recorded
        in report.pipeline_errors and is_partial is set when extraction
        was incomplete.
    """
    global _compiled
    if _compiled is None:
        _compiled = _build_graph()

    initial_state: PipelineState = {
        "raw_text": raw_text,
        "extracted_metadata": None,
        "policy_chunks": [],
        "compliance_results": None,
        "confidence": None,
        "report": None,
        "errors": [],
    }

    final_state = _compiled.invoke(initial_state)
    return final_state["report"]
