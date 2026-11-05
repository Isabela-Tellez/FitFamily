"""Integración real de Laura, Gema y María. Solo el límite LLM se simula."""
from dataclasses import asdict
from decimal import Decimal
import json
from unittest.mock import patch
import pytest
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_break_even, metric_context_notes
from src.analysis.contracts import CalculatedMetric
from src.reporting.models import ReportDraft, ReportClaim
from src.reporting.report_builder import build_report
from src.reporting.markdown_renderer import render_report_markdown
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context
from src.schemas import ResearchBrief, ResearchResult


def make_shared_case():
    brief = ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona ficticia")
    research = ResearchResult()
    scenario = create_economic_scenario("intermediate", 100, 50, 1000, 10,
                                        assumptions=["Escenario ficticio de integración."])
    original = next(c for c in evaluate_economic_scenario(
        scenario, limitations=["Costes ficticios pendientes de contrastar."]
    ) if c.calculation_type == "break_even")
    metrics = [metric_from_break_even(scenario, original)]
    return brief, research, metrics


def build_shared():
    brief, research, metrics = make_shared_case()
    draft = build_report(brief, research, calculated_metrics=metrics)
    return draft, research, metrics


def test_llm_builder_adds_real_metric_and_preserves_notes():
    brief, research, metrics = make_shared_case()
    # No se simulan constructor, cálculo, adaptador, revisión ni renderizador.
    with patch("src.agents.strategic_writer.run_writing", return_value=ReportDraft(
        title="Informe ficticio", study_area=brief.study_area,
        sections=["Alcance\nTexto cualitativo simulado."],
    )) as llm:
        draft = build_report(brief, research, use_llm=True, calculated_metrics=metrics)
    llm.assert_called_once_with(brief, research)
    claim = next(c for c in draft.claims if c.metric_id == metrics[0].metric_id)
    assert claim.reported_value == 25
    assert claim.reported_unit == "clients"
    assert "25 clientes" in claim.text
    assert any(claim.text in s for s in draft.sections)
    assert set(metric_context_notes(metrics[0])).issubset(draft.limitations)
    assert "25 clientes" in render_report_markdown(draft)
    checked = run_basic_review(draft, research, calculated_metrics=metrics)
    assert checked.issues == ()
    assert choose_review_route_for_context(checked, draft, research, 0,
                                          calculated_metrics=metrics) == "pending_review"


def test_json_roundtrip_preserves_claim_types_metrics_and_fingerprints():
    draft, research, metrics = build_shared()
    checked = run_basic_review(draft, research, calculated_metrics=metrics)
    payload = json.loads(json.dumps({
        "draft": asdict(draft),
        "metrics": [m.model_dump(mode="json") for m in metrics],
    }))
    raw = payload["draft"]
    raw["claims"] = [ReportClaim(**item) for item in raw["claims"]]
    restored = ReportDraft(**raw)
    recovered = [CalculatedMetric.model_validate(m) for m in payload["metrics"]]
    assert all(isinstance(c, ReportClaim) for c in restored.claims)
    assert recovered == metrics
    assert choose_review_route_for_context(checked, restored, research, 0,
                                          calculated_metrics=recovered) == "pending_review"


@pytest.mark.parametrize("change", ["draft", "research", "assumptions", "limitations"])
def test_changed_context_needs_new_review(change):
    draft, research, metrics = build_shared()
    checked = run_basic_review(draft, research, calculated_metrics=metrics)
    if change == "draft":
        draft.claims[0].text += " Modificado."
    elif change == "research":
        research.notes = "Nueva información."
    elif change == "assumptions":
        metrics[0].context.scenario.assumptions.append("Nuevo supuesto.")
    else:
        metrics[0].context.calculation_result.limitations.append("Nueva limitación.")
    with pytest.raises(ValueError, match="cambió"):
        choose_review_route_for_context(checked, draft, research, 0, calculated_metrics=metrics)


@pytest.mark.parametrize("count,expected", [(0, "revise_writing"), (2, "blocked")])
def test_wrong_reported_value_routes_with_revision_limit(count, expected):
    draft, research, metrics = build_shared()
    draft.claims[0].reported_value = 99
    checked = run_basic_review(draft, research, calculated_metrics=metrics)
    assert any(i.code == "metric_value_mismatch" for i in checked.issues)
    assert choose_review_route_for_context(checked, draft, research, count,
                                          calculated_metrics=metrics) == expected


def test_missing_notes_is_a_writing_issue():
    draft, research, metrics = build_shared()
    draft.limitations = []
    checked = run_basic_review(draft, research, calculated_metrics=metrics)
    assert any(i.code == "missing_calculation_notes" for i in checked.issues)
    assert choose_review_route_for_context(checked, draft, research, 0,
                                          calculated_metrics=metrics) == "revise_writing"


def test_unavailable_calculation_is_explained_without_zero_claim():
    brief, research, metrics = make_shared_case()
    metrics[0].value = None
    metrics[0].context.calculation_result.result = None
    draft = build_report(brief, research, calculated_metrics=metrics)
    assert not any(c.metric_id == metrics[0].metric_id for c in draft.claims)
    assert any("Resultado no disponible" in s for s in draft.sections)
    assert set(metric_context_notes(metrics[0])).issubset(draft.limitations)
