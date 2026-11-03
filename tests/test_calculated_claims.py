"""Pruebas con datos ficticios y cálculos reales.

El redactor LLM se simula cuando corresponde.
No se realizan llamadas externas.
"""

import pytest

from src.analysis.calculation_adapter import (
    metric_context_notes,
    metric_from_break_even,
)
from src.analysis.economic_calculations import create_break_even_calculation
from src.analysis.scenarios import create_economic_scenario
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.calculated_claims import build_break_even_claim
from src.reporting.models import ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchResult


def test_break_even_text_matches_calculation_and_passes_review():
    """El texto y los campos conservan el resultado calculado."""
    # Escenario exclusivamente ficticio para esta prueba.
    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=50,
        fixed_costs=1000,
        variable_cost_per_client=10,
        assumptions=["Importes ficticios para comprobar la integración."],
    )

    # Usamos el cálculo real de Laura; no repetimos su fórmula.
    calculation = create_break_even_calculation(
        fixed_costs=scenario.fixed_costs,
        monthly_fee=scenario.monthly_fee,
        variable_cost_per_client=scenario.variable_cost_per_client,
        limitations=["No incluye impuestos ni estacionalidad."],
    )
    metric = metric_from_break_even(scenario, calculation)

    # Nuestra función genera texto y campos desde la misma métrica.
    claim = build_break_even_claim(
        metric,
        claim_id="claim_break_even",
    )

    assert claim is not None
    assert claim.reported_value == 25.0
    assert claim.reported_unit == "clients"
    assert claim.metric_id == metric.metric_id
    assert claim.evidence_ids == metric.evidence_ids
    assert claim.kind == "inference"
    assert "25 clientes" in claim.text
    assert "Esto no garantiza" in claim.text

    # Conservamos las notas que exige el contrato de María.
    draft = ReportDraft(
        title="Informe ficticio de prueba",
        study_area="Zona de prueba",
        sections=["Escenario económico\n" + claim.text],
        claims=[claim],
        limitations=metric_context_notes(metric),
    )
    research = ResearchResult()

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=[metric],
    )

    assert review.issues == ()

    route = choose_review_route_for_context(
        review,
        draft,
        research,
        revision_count=0,
        calculated_metrics=[metric],
    )

    # No significa aprobación humana: permite continuar la revisión.
    assert route == "pending_review"

def test_unavailable_result_does_not_generate_a_numeric_claim():
    """Un resultado ausente no se presenta como cero clientes."""
    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=50,
        fixed_costs=1000,
        variable_cost_per_client=10,
    )
    calculation = create_break_even_calculation(
        fixed_costs=1000,
        monthly_fee=50,
        variable_cost_per_client=10,
    )

    # Simulamos un resultado no disponible.
    calculation.result = None
    metric = metric_from_break_even(scenario, calculation)

    claim = build_break_even_claim(
        metric,
        claim_id="claim_unavailable",
    )

    assert claim is None


def test_text_uses_the_result_of_another_scenario():
    """La cifra del texto procede del cálculo, no está fijada en 25."""
    scenario = create_economic_scenario(
        scenario_type="conservative",
        expected_clients=80,
        monthly_fee=40,
        fixed_costs=1500,
        variable_cost_per_client=10,
    )
    calculation = create_break_even_calculation(
        fixed_costs=scenario.fixed_costs,
        monthly_fee=scenario.monthly_fee,
        variable_cost_per_client=scenario.variable_cost_per_client,
    )
    metric = metric_from_break_even(scenario, calculation)

    claim = build_break_even_claim(
        metric,
        claim_id="claim_conservative",
    )

    assert claim is not None
    assert claim.reported_value == 50.0
    assert "50 clientes" in claim.text
    assert "25 clientes" not in claim.text
    assert scenario.scenario_id in claim.text

def test_report_builder_includes_calculated_claim_and_context_notes():
    """El constructor incorpora cifra, texto y contexto del cálculo."""
    from src.reporting.report_builder import build_report
    from src.schemas import ResearchBrief

    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=50,
        fixed_costs=1000,
        variable_cost_per_client=10,
        assumptions=["Importes ficticios para la prueba."],
    )
    calculation = create_break_even_calculation(
        fixed_costs=scenario.fixed_costs,
        monthly_fee=scenario.monthly_fee,
        variable_cost_per_client=scenario.variable_cost_per_client,
        limitations=["No incluye impuestos ni estacionalidad."],
    )
    metric = metric_from_break_even(scenario, calculation)

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="Zona ficticia de prueba",
    )
    research = ResearchResult()

    # Esta vez el constructor crea e incorpora la afirmación.
    draft = build_report(
        brief,
        research,
        calculated_metrics=[metric],
    )

    linked_claims = [
        claim
        for claim in draft.claims
        if claim.metric_id == metric.metric_id
    ]

    assert len(linked_claims) == 1
    claim = linked_claims[0]

    assert claim.reported_value == 25.0
    assert claim.reported_unit == "clients"
    assert claim.kind == "inference"

    # La sección muestra exactamente el texto de la afirmación.
    assert any(claim.text in section for section in draft.sections)

    # Los supuestos y las limitaciones no desaparecen.
    expected_notes = metric_context_notes(metric)
    assert expected_notes
    assert set(expected_notes).issubset(draft.limitations)

    # Revisamos el borrador completo con el código de María.
    review = run_basic_review(
        draft,
        research,
        calculated_metrics=[metric],
    )

    assert review.issues == ()
    assert choose_review_route_for_context(
        review,
        draft,
        research,
        revision_count=0,
        calculated_metrics=[metric],
    ) == "pending_review"

def test_markdown_builder_includes_calculated_text_and_notes():
    """La salida Markdown conserva la cifra y sus limitaciones."""
    from src.reporting.report_builder import build_report_markdown
    from src.schemas import ResearchBrief

    scenario = create_economic_scenario(
        scenario_type="conservative",
        expected_clients=80,
        monthly_fee=40,
        fixed_costs=1500,
        variable_cost_per_client=10,
        assumptions=["Escenario ficticio para la prueba."],
    )
    calculation = create_break_even_calculation(
        fixed_costs=scenario.fixed_costs,
        monthly_fee=scenario.monthly_fee,
        variable_cost_per_client=scenario.variable_cost_per_client,
        limitations=["Costes pendientes de contrastar."],
    )
    metric = metric_from_break_even(scenario, calculation)

    markdown = build_report_markdown(
        ResearchBrief(
            business_type="gimnasio con ludoteca",
            location="Madrid",
            study_area="Zona ficticia",
        ),
        ResearchResult(),
        calculated_metrics=[metric],
    )

    assert "Punto de equilibrio por escenario" in markdown
    assert "50 clientes" in markdown

    for note in metric_context_notes(metric):
        assert note in markdown

@pytest.mark.parametrize(
    "existing_body",
    [
        "Información cualitativa del escenario.",
        None,
    ],
)
def test_calculations_keep_common_outline_without_duplicate_sections(
    existing_body,
):
    """Inserta el cálculo en su apartado y conserva el resto del informe."""
    from unittest.mock import patch

    from src.reporting.report_builder import build_report
    from src.reporting.templates import (
        MISSING_SECTION_TEXT,
        REPORT_SECTION_TITLES,
    )
    from src.schemas import ResearchBrief

    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=50,
        fixed_costs=1000,
        variable_cost_per_client=10,
    )
    calculation = create_break_even_calculation(
        fixed_costs=1000,
        monthly_fee=50,
        variable_cost_per_client=10,
    )
    metric = metric_from_break_even(scenario, calculation)

    sections = [
        f"{title}\n{MISSING_SECTION_TEXT}"
        for title in REPORT_SECTION_TITLES
    ]
    economic_index = REPORT_SECTION_TITLES.index("Escenarios económicos")

    if existing_body is not None:
        sections[economic_index] = (
            f"Escenarios económicos\n{existing_body}"
        )

    simulated_draft = ReportDraft(
        title="Informe ficticio",
        study_area="Zona de prueba",
        sections=list(sections),
    )

    # Simulamos el redactor; el constructor y el cálculo son reales.
    with patch(
        "src.agents.strategic_writer.run_writing",
        return_value=simulated_draft,
    ):
        draft = build_report(
            ResearchBrief(
                business_type="gimnasio",
                location="Madrid",
                study_area="Zona de prueba",
            ),
            ResearchResult(),
            use_llm=True,
            calculated_metrics=[metric],
        )

    titles = [
        section.partition("\n")[0]
        for section in draft.sections
    ]
    assert titles == list(REPORT_SECTION_TITLES)

    economic_section = draft.sections[economic_index]
    assert economic_section.count("25 clientes") == 1
    assert MISSING_SECTION_TEXT not in economic_section

    if existing_body is not None:
        assert existing_body in economic_section

    # Los demás apartados conservan exactamente su contenido.
    for index, section in enumerate(sections):
        if index != economic_index:
            assert draft.sections[index] == section