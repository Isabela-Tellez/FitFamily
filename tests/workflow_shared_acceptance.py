"""Aceptación explícita pendiente de Isabella: NO se recoge en pytest por defecto.

Ejecutar: python -m pytest tests/workflow_shared_acceptance.py -vv
En dev 6d38f55 estos casos fallan por conexiones pendientes conocidas.
No utilizar xfail ni simular la revisión para ocultar esos resultados.
"""
from dataclasses import asdict
from unittest.mock import patch
from src.analysis.contracts import CalculatedMetric
from src.graph.state import create_initial_state
from src.graph.workflow import analysis_node, writing_node, review_node
from src.reporting.models import ReportDraft
from tests.test_shared_report_integration import make_shared_case, build_shared


def test_analysis_retains_originals_and_produces_contextual_break_even():
    brief, _, _ = make_shared_case()
    brief.assumed_params = dict(expected_clients=100, monthly_fee=50, fixed_costs=1000,
                               variable_cost_per_client=10)
    result = analysis_node(create_initial_state("shared-test", brief.model_dump(mode="json")))
    analysis = result["analysis_result"]
    assert len(analysis["scenarios"][0]["calculations"]) == 4
    metrics = [CalculatedMetric.model_validate(m) for m in analysis["calculated_metrics"]]
    matching = [m for m in metrics if m.metric_id == "scenario_intermediate.break_even_clients"]
    assert len(matching) == 1, "Falta la métrica obtenida con el adaptador compartido."
    assert matching[0].context is not None
    assert matching[0].context.calculation_result.calculation_type == "break_even"


def test_writing_node_includes_numeric_claim_from_shared_metrics():
    brief, research, metrics = make_shared_case()
    state = create_initial_state("shared-test", brief.model_dump(mode="json"))
    state.update(research_result=research.model_dump(mode="json"),
                 analysis_result={"calculated_metrics": [m.model_dump(mode="json") for m in metrics]})
    # Sustituye únicamente el proveedor LLM, incluido el alias del workflow antiguo.
    def fake_llm(*args, **kwargs):
        return ReportDraft(title="Informe ficticio", study_area=brief.study_area)
    with patch("src.agents.strategic_writer.run_writing", side_effect=fake_llm), patch(
        "src.graph.workflow.run_writing", side_effect=fake_llm, create=True
    ):
        result = writing_node(state)
    claims = result["report_draft"]["claims"]
    assert any(c["metric_id"] == metrics[0].metric_id for c in claims), "El nodo debe usar build_report con las métricas."


def test_review_node_reconstructs_nested_claims_and_checks_real_draft():
    brief, _, _ = make_shared_case()
    draft, research, metrics = build_shared()
    state = create_initial_state("shared-test", brief.model_dump(mode="json"))
    state.update(report_draft=asdict(draft), research_result=research.model_dump(mode="json"),
                 analysis_result={"calculated_metrics": [m.model_dump(mode="json") for m in metrics]})
    result = review_node(state)
    assert not result["review_result"]["issues"]
    assert "calculation_context" in result["review_result"]["checks_performed"]
    assert result["status"] == "awaiting_approval"
