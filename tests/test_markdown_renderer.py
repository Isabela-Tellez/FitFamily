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

    assert "**Métrica:** scenario_intermediate.break_even_clients" in markdown
    assert "**Valor declarado:** 25.0" in markdown
    assert "**Unidad:** clients" in markdown
    assert "Bajo estos supuestos se necesitan 25 clientes." in markdown
    assert draft == original