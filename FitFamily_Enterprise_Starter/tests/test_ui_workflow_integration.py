"""Pruebas de integración del workflow que consume la UI."""
from dataclasses import asdict

from src.graph.state import create_initial_state
from src.graph.workflow import analysis_node, review_node, writing_node
from src.schemas import Evidence, ResearchResult


def _brief(assumptions=None):
    return {
        "business_type": "gimnasio con ludoteca",
        "location": "Madrid",
        "study_area": "El Cañaveral",
        "questions": ["Competidores y servicios"],
        "assumed_params": assumptions,
    }


def test_analysis_node_marks_user_inputs_as_assumptions_and_keeps_break_even_context():
    state = create_initial_state("run-ui-test-1", _brief({
        "expected_clients": 120,
        "monthly_fee": 45.0,
        "fixed_costs": 5000.0,
        "variable_cost_per_client": 8.0,
    }))
    result = analysis_node(state)
    metrics = result["analysis_result"]["calculated_metrics"]
    assert len(metrics) == 4
    break_even = next(item for item in metrics if item["metric_id"].endswith("break_even_clients"))
    assert break_even["context"] is not None
    assert break_even["context"]["calculation_result"]["calculation_type"] == "break_even"
    assert all(
        item["input_type"] == "assumption"
        for item in break_even["context"]["calculation_result"]["inputs"]
    )


def test_analysis_node_does_not_invent_values_when_assumptions_are_missing():
    state = create_initial_state("run-ui-test-2", _brief())
    result = analysis_node(state)
    assert result["analysis_result"]["calculated_metrics"] == []
    assert any("Faltan supuestos" in item for item in result["analysis_result"]["limitations"])


def test_writing_node_includes_only_supported_break_even_claim_contract():
    research = ResearchResult(evidences=[Evidence(
        evidence_id="e1",
        claim="Página de negocio consultada.",
        source_url="https://example.org",
        snippet="Información pública del negocio.",
    )])
    initial = create_initial_state("run-ui-test-3", _brief({
        "expected_clients": 120,
        "monthly_fee": 45.0,
        "fixed_costs": 5000.0,
        "variable_cost_per_client": 8.0,
    }))
    initial["research_result"] = research.model_dump(mode="json")
    initial["analysis_result"] = analysis_node(initial)["analysis_result"]
    initial["writer_mode"] = "deterministic"
    written = writing_node(initial)
    report = written["report_draft"]
    assert any(claim.get("metric_id", "").endswith("break_even_clients") for claim in report["claims"])
    assert any("Supuesto de cálculo" in note for note in report["limitations"])


def test_review_node_blocks_approval_when_research_has_no_evidence():
    draft_state = {
        "title": "Estudio",
        "study_area": "El Cañaveral",
        "sections": [],
        "sources": [],
        "limitations": [],
        "draft_id": "draft-test",
        "version": 1,
        "claims": [],
    }
    state = {
        "brief": _brief(),
        "research_result": ResearchResult().model_dump(mode="json"),
        "analysis_result": {"calculated_metrics": []},
        "report_draft": draft_state,
    }
    result = review_node(state)
    assert result["status"] == "failed"
    assert any(item["code"] == "no_research_evidence" for item in result["review_result"]["issues"])
