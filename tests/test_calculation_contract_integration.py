"""Contrato real de Laura, adaptación y revisión. Datos exclusivamente ficticios."""
from decimal import Decimal
import pytest
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.economic_calculations import create_break_even_calculation
from src.analysis.calculation_adapter import metric_from_break_even, metric_context_notes
from src.reporting.models import ReportDraft, ReportClaim
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context
from src.schemas import ResearchResult, Evidence


def case():
    scenario = create_economic_scenario("intermediate", 100, 50, 1000, 10,
                                        assumptions=["Cuota hipotética para la prueba."])
    result = next(c for c in evaluate_economic_scenario(
        scenario, limitations=["Costes ficticios, pendientes de contrastar."]
    ) if c.calculation_type == "break_even")
    metric = metric_from_break_even(scenario, result)
    draft = ReportDraft(title="Escenario ficticio", study_area="Zona de prueba",
                        claims=[ReportClaim(
                            "break_even", "Con estos supuestos se necesitan 25 clientes.",
                            "inference", [], metric.metric_id, 25.0, "clients",
                        )])
    draft.limitations = metric_context_notes(metric)
    return scenario, result, metric, draft, ResearchResult()


def review(metric, draft, research):
    return run_basic_review(draft, research, calculated_metrics=[metric])


def test_real_scenario_adapter_and_reviewer_agree():
    scenario, original, metric, draft, research = case()
    checked = review(metric, draft, research)
    assert metric.value == Decimal("25")
    assert metric.metric_id == "scenario_intermediate.break_even_clients"
    assert metric.calculation == original.calculation_id
    assert metric.context.calculation_result == original
    assert metric.context.scenario.assumptions == scenario.assumptions
    assert metric.context.calculation_result.limitations == original.limitations
    assert checked.issues == ()
    assert "calculation_context" in checked.checks_performed
    assert choose_review_route_for_context(checked, draft, research, 0,
                                          calculated_metrics=[metric]) == "pending_review"


def test_conversion_copies_and_does_not_modify_original():
    scenario, original, metric, _, _ = case()
    original.limitations.append("Cambio posterior")
    scenario.assumptions.append("Otro supuesto")
    assert "Cambio posterior" not in metric.context.calculation_result.limitations
    assert "Otro supuesto" not in metric.context.scenario.assumptions


@pytest.mark.parametrize("part", ["inputs", "assumptions", "limitations", "operation", "calculation_id", "scenario_id"])
def test_context_changes_invalidate_existing_review(part):
    _, _, metric, draft, research = case()
    checked = review(metric, draft, research)
    ctx = metric.context
    if part == "inputs":
        ctx.calculation_result.inputs[0].value = 1100
    elif part == "assumptions":
        ctx.scenario.assumptions.append("Nuevo supuesto")
    elif part == "limitations":
        ctx.calculation_result.limitations.append("Nueva limitación")
    elif part == "operation":
        ctx.calculation_result.operation = "alterada"
    elif part == "calculation_id":
        ctx.calculation_result.calculation_id = "other"
    else:
        ctx.scenario.scenario_id = "other"
    with pytest.raises(ValueError, match="análisis cambió"):
        choose_review_route_for_context(checked, draft, research, 0, calculated_metrics=[metric])


@pytest.mark.parametrize("part", ["metric_value", "unit", "metric_id", "link", "formula", "result", "input", "input_unit", "duplicate"])
def test_invalid_conversion_or_original_calculation_returns_to_analysis(part):
    _, _, metric, draft, research = case()
    calc = metric.context.calculation_result
    if part == "metric_value":
        metric.value = Decimal("30")
    elif part == "unit":
        metric.unit = "EUR"
    elif part == "metric_id":
        metric.metric_id = "wrong"
    elif part == "link":
        metric.calculation = "wrong"
    elif part == "formula":
        calc.operation = "arbitrary code"
    elif part == "result":
        calc.result.value = 30
    elif part == "input":
        calc.inputs[0].value = 2000
    elif part == "input_unit":
        calc.inputs[1].unit = "EUR/month"
    else:
        calc.inputs.append(calc.inputs[0].model_copy())
    checked = review(metric, draft, research)
    assert any(i.code == "invalid_calculation_context" for i in checked.issues)
    assert choose_review_route_for_context(checked, draft, research, 0,
                                          calculated_metrics=[metric]) == "revise_analysis"


def test_wrong_claim_returns_to_writing():
    _, _, metric, draft, research = case()
    draft.claims[0].reported_value = 30
    checked = review(metric, draft, research)
    assert any(i.code == "metric_value_mismatch" for i in checked.issues)
    assert choose_review_route_for_context(checked, draft, research, 0,
                                          calculated_metrics=[metric]) == "revise_writing"


def test_explicit_evidence_input_keeps_per_client_unit():
    scenario, _, _, draft, _ = case()
    original = create_break_even_calculation(
        1000, 50, 10, evidence_ids=["fee"], input_types={"monthly_fee": "evidence"},
    )
    metric = metric_from_break_even(scenario, original, input_evidence_ids={"monthly_fee": "fee"})
    research = ResearchResult(evidences=[Evidence(
        evidence_id="fee", claim="Tarifa ficticia por cliente", value=50,
        unit="EUR/client/month", frequency="monthly", source_url="https://example.org/fee",
    )])
    draft.claims[0].evidence_ids = list(metric.evidence_ids)
    draft.limitations = metric_context_notes(metric)
    assert review(metric, draft, research).issues == ()
    research.evidences[0].value = 90
    assert any(i.code == "invalid_calculation_context" for i in review(metric, draft, research).issues)


def test_observation_needs_specific_evidence_link():
    scenario, _, _, draft, research = case()
    original = create_break_even_calculation(
        1000, 50, 10, input_types={"monthly_fee": "evidence"},
    )
    metric = metric_from_break_even(scenario, original)
    assert any(i.code == "invalid_calculation_context" for i in review(metric, draft, research).issues)


def test_unavailable_result_is_not_replaced_by_zero():
    scenario, original, _, draft, research = case()
    original.result = None
    metric = metric_from_break_even(scenario, original)
    assert metric.value is None
    assert any(i.code == "unavailable_calculated_metric" for i in review(metric, draft, research).issues)


def test_two_scenarios_have_distinct_metric_ids():
    scenario, original, first, _, _ = case()
    other = scenario.model_copy(update={"scenario_id": "scenario_optimistic", "scenario_type": "optimistic"})
    second = metric_from_break_even(other, original)
    assert first.metric_id != second.metric_id


def test_original_changes_are_detected_when_controller_refreshes_adapter():
    scenario, original, metric, draft, research = case()
    checked = review(metric, draft, research)
    original.limitations.append("Nueva limitación en el análisis original")
    current = metric_from_break_even(scenario, original)
    with pytest.raises(ValueError, match="análisis cambió"):
        choose_review_route_for_context(checked, draft, research, 0, calculated_metrics=[current])


def test_import_uses_laura_current_module():
    from src.review.calculation_validation import calculate_break_even_clients
    assert calculate_break_even_clients(1000, 50, 10) == 25


def test_assumptions_and_limitations_cannot_disappear_from_report():
    _, _, metric, draft, research = case()
    draft.limitations = []
    assert any(i.code == "missing_calculation_notes" for i in review(metric, draft, research).issues)


def test_assumed_scenario_is_not_an_observed_fact():
    _, _, metric, draft, research = case()
    draft.claims[0].kind = "fact"
    assert any(i.code == "scenario_presented_as_fact" for i in review(metric, draft, research).issues)
