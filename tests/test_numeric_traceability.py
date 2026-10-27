"""Regresiones de texto, procedencia y recorrido completo con datos ficticios."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from src.analysis.provenance import (
    AVERAGE, calculate_price_average, calculate_observed_metrics,
    calculate_break_even_metric, evidence_index, validate_metric_provenance,
)
from src.reporting.numeric_text import TEMPLATE
from src.reporting.models import ReportClaim
from src.reporting.markdown_renderer import render_report_markdown
from src.reporting.pdf_renderer import render_report_pdf
from src.graph.report_pipeline import prepare_reviewed_report
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context
from src.schemas import ResearchBrief, ResearchResult, Evidence, Competitor
from tests.test_numeric_review_integration import make_case


def codes(review):
    return {i.code for i in review.issues}


@pytest.mark.parametrize("location", ["claim", "section", "title", "limitation"])
def test_literal_number_cannot_bypass_review(location):
    draft, research, metrics = make_case()
    if location == "claim":
        draft.claims[0].text = "La cuota media es de 50 euros."
    elif location == "section":
        draft.sections.append("Resultados\nLa cuota media es de 99 euros.")
    elif location == "title":
        draft.title = "Cuota media de 99 euros"
    else:
        draft.limitations.append("Se garantiza una cuota de 99 euros.")
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    assert "uncontrolled_numeric_text" in codes(review)


@pytest.mark.parametrize("text", ["La cuota es de cincuenta euros.", "La cuota es de 50 €.", "{{value}}"])
def test_unlinked_numeric_claim_is_rejected(text):
    draft, research, metrics = make_case()
    draft.claims.append(ReportClaim("unlinked", text, "inference"))
    assert "uncontrolled_numeric_text" in codes(run_basic_review(draft, research, calculated_metrics=metrics))


@pytest.mark.parametrize("change", [
    {"evidence_ids": []}, {"evidence_ids": ["missing"]},
    {"evidence_ids": ["demo_price", "demo_price"]},
    {"calculation": "untrusted.python.function"},
    {"value": Decimal("90")}, {"unit": "EUR/year"},
])
def test_bad_calculated_provenance_is_blocked(change):
    draft, research, metrics = make_case()
    metrics[0] = metrics[0].model_copy(update=change)
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    assert "invalid_metric_provenance" in codes(review)
    assert choose_review_route_for_context(review, draft, research, 0, calculated_metrics=metrics) == "revise_analysis"


@pytest.mark.parametrize("field,value", [
    ("value", 90), ("value", True), ("value", "45"),
    ("value", float("inf")), ("value", -1),
    ("source_url", None), ("frequency", "annual"), ("unit", "USD"),
])
def test_source_changes_are_recomputed(field, value):
    draft, research, metrics = make_case()
    setattr(research.evidences[0], field, value)
    assert "invalid_metric_provenance" in codes(run_basic_review(draft, research, calculated_metrics=metrics))


def test_copies_are_deduplicated_but_conflicts_are_rejected():
    _, research, metrics = make_case()
    research.competitors.append(Competitor(evidences=[research.evidences[0].model_copy(deep=True)]))
    assert len(evidence_index(research)) == 1
    assert validate_metric_provenance(metrics, research) == []
    research.competitors[0].evidences[0].value = 90
    assert validate_metric_provenance(metrics, research)


def test_claim_must_cite_calculation_inputs():
    draft, research, metrics = make_case()
    draft.claims[0].evidence_ids = []
    assert "metric_claim_evidence_mismatch" in codes(run_basic_review(draft, research, calculated_metrics=metrics))


def test_shared_rendering_inserts_value_in_claim_and_section():
    import pdfplumber
    draft, _, _ = make_case()
    draft.sections = ["Resultados\n{{claim:average_price}}"]
    before = deepcopy(draft)
    markdown = render_report_markdown(draft)
    assert markdown.count("45 EUR/month") == 2
    assert "{{" not in markdown
    with pdfplumber.open(BytesIO(render_report_pdf(draft))) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert text.count("45 EUR/month") == 2
    assert draft == before


@pytest.mark.parametrize("renderer", [render_report_markdown, render_report_pdf])
def test_renderers_reject_literal_overrides(renderer):
    draft, _, _ = make_case()
    draft.claims[0].text = "50 euros"
    with pytest.raises(ValueError, match="plantilla"):
        renderer(draft)


def test_unknown_section_reference_is_rejected():
    draft, research, metrics = make_case()
    draft.sections = ["Resultados\n{{claim:missing}}"]
    assert "uncontrolled_numeric_text" in codes(run_basic_review(draft, research, calculated_metrics=metrics))
    with pytest.raises(ValueError):
        render_report_markdown(draft)


def test_real_average_and_complete_pipeline():
    _, research, _ = make_case()
    research.evidences[0].value = 40
    research.evidences.append(Evidence(
        evidence_id="other_price", claim="Otro precio ficticio", value=50,
        unit="EUR", frequency="monthly", source_url="https://example.org/price",
    ))
    brief = ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona ficticia")
    result = prepare_reviewed_report(brief, research, price_evidence_ids=["demo_price", "other_price"])
    assert result.route == "pending_review"
    assert result.review.issues == ()
    assert result.calculated_metrics[-1].value == Decimal("45")
    assert result.calculated_metrics[-1].evidence_ids == ["demo_price", "other_price"]
    assert "45 EUR/month" in render_report_markdown(result.draft)
    assert all(c.text == TEMPLATE for c in result.draft.claims)
    research.evidences[0].value = 60
    with pytest.raises(ValueError, match="investigación cambió"):
        choose_review_route_for_context(result.review, result.draft, research, 0,
                                        calculated_metrics=result.calculated_metrics)


def test_financial_inputs_are_reproducible_and_named():
    research = ResearchResult(evidences=[
        Evidence(evidence_id=name, claim="Entrada ficticia", value=value,
                 unit="EUR", frequency="monthly", source_url="https://example.org/" + name)
        for name, value in [("cost", 1000), ("fee", 50), ("variable", 10)]
    ])
    roles = {"fixed_costs": "cost", "monthly_fee": "fee", "variable_cost_per_client": "variable"}
    metric = calculate_break_even_metric(research, roles)
    assert metric.value == Decimal("25")
    assert metric.unit == "clients"
    assert validate_metric_provenance([metric], research) == []
    swapped = metric.model_copy(update={"input_evidence_ids": {**roles, "monthly_fee": "cost", "fixed_costs": "fee"}})
    assert validate_metric_provenance([swapped], research)


def test_llm_preserves_numeric_fields_and_receives_calculations():
    from src.agents.strategic_writer import run_writing
    from src.reporting.writing_models import WritingClaim, WritingOutput
    _, research, metrics = make_case()
    brief = ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona ficticia")
    response = WritingOutput(
        sections=["Resultados\n{{claim:claim_001}}"],
        claims=[WritingClaim(text=TEMPLATE, kind="inference", evidence_ids=["demo_price"],
                             metric_id=metrics[0].metric_id, reported_value=45, reported_unit="EUR/month")],
    )
    with patch("src.agents.strategic_writer.build_writer"), patch(
        "src.agents.strategic_writer.build_writing_task"
    ) as task, patch("src.agents.strategic_writer.Crew") as crew:
        crew.return_value.kickoff.return_value = SimpleNamespace(pydantic=response)
        draft = run_writing(brief, research, calculated_metrics=metrics)
    assert task.call_args.kwargs["calculated_metrics"] == metrics
    assert draft.claims[0].metric_id == metrics[0].metric_id
    assert run_basic_review(draft, research, calculated_metrics=metrics).issues == ()
    assert "45 EUR/month" in render_report_markdown(draft)


def test_approved_literal_text_is_still_blocked_at_export(tmp_path):
    from src.automation.exporter import export_markdown
    from tests.test_exporter import make_approved_record
    draft, _, _ = make_case()
    draft.sections = ["Resultados\nLa cuota es de 99 euros."]
    approval = make_approved_record(draft)  # decisión simulada, solo prueba
    with pytest.raises(ValueError, match="Texto numérico sin control"):
        export_markdown(draft, approval, approval.run_id, tmp_path / "not_created")
    assert not (tmp_path / "not_created").exists()


def test_delivery_gate_rejects_changed_analysis_and_missing_approval(tmp_path):
    from src.graph.report_pipeline import export_reviewed_report
    _, research, _ = make_case()
    brief = ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona ficticia")
    result = prepare_reviewed_report(brief, research)
    with pytest.raises(ValueError, match="aprobación"):
        export_reviewed_report(result, research, None, "test", tmp_path)
    result.calculated_metrics[0].value = Decimal("90")
    with pytest.raises(ValueError, match="análisis cambió"):
        export_reviewed_report(result, research, None, "test", tmp_path)
