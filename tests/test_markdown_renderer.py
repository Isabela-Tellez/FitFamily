"""Pruebas de presentación del informe en Markdown."""

from copy import deepcopy

from src.reporting.markdown_renderer import render_report_markdown
from src.reporting.models import ReportClaim, ReportDraft


def test_markdown_preserves_content_and_references():
    """El documento incluye los datos y sus referencias."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        draft_id="draft_test",
        version=2,
        sections=[
            "Competencia\nInformación de los centros estudiados."
        ],
        sources=[
            "https://example.com/tarifas",
            "https://example.com/tarifas",
        ],
        limitations=["Datos ficticios."],
        claims=[
            ReportClaim(
                claim_id="claim_price_1",
                text="Cuota mensual publicada de 45 euros.",
                kind="fact",
                evidence_ids=["price_1"],
            )
        ],
    )

    markdown = render_report_markdown(draft)

    assert "# Informe de prueba" in markdown
    assert "**Zona de estudio:** El Cañaveral" in markdown
    assert "**Identificador del borrador:** draft_test" in markdown
    assert "**Versión:** 2" in markdown
    assert "## Competencia" in markdown
    assert "Información de los centros estudiados." in markdown
    assert markdown.count("https://example.com/tarifas") == 1
    assert "Datos ficticios." in markdown
    assert "Cuota mensual publicada de 45 euros." in markdown
    assert "**Evidencias:** price_1" in markdown


def test_markdown_declares_missing_information():
    """Un borrador vacío no se presenta como completo."""
    draft = ReportDraft(
        title="Informe incompleto",
        study_area="El Cañaveral",
    )

    markdown = render_report_markdown(draft)

    assert "pendiente de revisión y aprobación" in markdown
    assert "No se han registrado fuentes." in markdown
    assert "No se han registrado limitaciones." in markdown
    assert "No se han registrado afirmaciones" in markdown


def test_rendering_does_not_modify_the_draft():
    """Presentar el informe no cambia su contenido ni su versión."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nEstudiar la competencia."],
        version=3,
    )
    original = deepcopy(draft)

    first = render_report_markdown(draft)
    second = render_report_markdown(draft)

    assert draft == original
    assert first == second

def test_markdown_shows_metric_reference_without_changing_draft():
    """Muestra la referencia numérica sin modificar el borrador."""
    from copy import deepcopy

    from src.reporting.models import ReportClaim, ReportDraft
    from src.reporting.markdown_renderer import render_report_markdown

    draft = ReportDraft(
        title="Informe ficticio",
        study_area="Zona de prueba",
        claims=[
            ReportClaim(
                claim_id="claim_break_even",
                text="Bajo estos supuestos se necesitan 25 clientes.",
                kind="inference",
                metric_id="scenario_intermediate.break_even_clients",
                reported_value=25.0,
                reported_unit="clients",
            )
        ],
    )
    original = deepcopy(draft)

    markdown = render_report_markdown(draft)

    assert "Métrica: scenario_intermediate.break_even_clients" in markdown
    assert "| Intermedio | Punto de equilibrio | 25 clientes |" in markdown
    assert draft == original


def test_economic_table_preserves_original_calculation_and_evidence():
    """El cálculo real conserva sus referencias hasta la tabla final."""
    from src.analysis.calculation_adapter import metric_from_break_even
    from src.analysis.economic_calculations import create_break_even_calculation
    from src.analysis.scenarios import create_economic_scenario
    from src.reporting.report_builder import build_report
    from src.schemas import Evidence, ResearchBrief, ResearchResult

    evidence = Evidence(
        evidence_id="economic_source_test",
        claim="Entradas ficticias documentadas para esta prueba.",
        source_url="https://example.com/escenario",
    )
    scenario = create_economic_scenario(
        "intermediate", 100, 50, 1000, 10,
        assumptions=["Escenario ficticio de prueba."],
    )
    calculation = create_break_even_calculation(
        fixed_costs=1000, monthly_fee=50, variable_cost_per_client=10,
        evidence_ids=[evidence.evidence_id],
    )
    metric = metric_from_break_even(scenario, calculation)
    draft = build_report(
        ResearchBrief(business_type="Gimnasio", location="Madrid", study_area="Prueba"),
        ResearchResult(evidences=[evidence]),
        calculated_metrics=[metric],
    )
    original = deepcopy(draft)

    markdown = render_report_markdown(draft)

    table_row = next(
        line for line in markdown.splitlines()
        if line.startswith("| Intermedio | Punto de equilibrio |")
    )
    assert "25 clientes" in table_row
    assert f"Métrica: {metric.metric_id}" in table_row
    assert f"Cálculo: {calculation.calculation_id}" in table_row
    assert f"Evidencias: {evidence.evidence_id}" in table_row
    assert draft.claims[0].calculation_id == calculation.calculation_id
    assert draft.claims[0].evidence_ids == [evidence.evidence_id]
    assert draft == original
