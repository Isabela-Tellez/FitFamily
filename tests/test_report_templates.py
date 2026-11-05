"""Pruebas de la estructura común del informe."""

import pytest

from src.reporting.templates import (
    MISSING_SECTION_TEXT,
    REPORT_SECTION_TITLES,
    validate_report_sections,
)


def make_sections():
    """Crea apartados pendientes sin inventar información."""
    return [
        f"{title}\n{MISSING_SECTION_TEXT}"
        for title in REPORT_SECTION_TITLES
    ]


def test_complete_outline_is_accepted():
    validate_report_sections(make_sections())


@pytest.mark.parametrize(
    "change",
    ["missing", "duplicate", "reordered", "extra", "empty_body"],
)
def test_invalid_outline_is_rejected(change):
    sections = make_sections()

    if change == "missing":
        sections.pop()
    elif change == "duplicate":
        sections[1] = sections[0]
    elif change == "reordered":
        sections[0], sections[1] = sections[1], sections[0]
    elif change == "extra":
        sections.append("Otro apartado\nContenido adicional.")
    else:
        sections[0] = REPORT_SECTION_TITLES[0]

    with pytest.raises(ValueError):
        validate_report_sections(sections)

def test_deterministic_sections_preserve_content_in_common_outline():
    """Reordena los apartados antiguos sin perder información."""
    from src.reporting.templates import arrange_deterministic_sections

    original_sections = [
        "Objetivo y alcance\nEstudiar un gimnasio con ludoteca.",
        "Competidores y tarifas\nCompetidor ficticio: cuota de 45 EUR.",
        "Tarifas documentadas\nTarifa respaldada por price_1.",
        "Supuestos del encargo\nCostes fijos supuestos: 1000 EUR.",
        "Proceso de investigación\nConsulta de fuentes municipales.",
        "Preguntas pendientes\n¿Existe demanda suficiente?",
    ]

    sections = arrange_deterministic_sections(original_sections)

    validate_report_sections(sections)

    by_title = {
        section.partition("\n")[0]: section.partition("\n")[2]
        for section in sections
    }

    assert "Estudiar un gimnasio con ludoteca." in by_title["Objetivo y alcance"]
    assert "cuota de 45 EUR" in by_title["Competencia"]
    assert "price_1" in by_title["Precios y servicios"]
    assert "1000 EUR" in by_title["Escenarios económicos"]
    assert "fuentes municipales" in by_title["Método y fuentes de datos"]
    assert "¿Existe demanda suficiente?" in by_title["Incertidumbres"]

    # No se inventa contenido para completar apartados.
    assert by_title["Análisis visual"] == MISSING_SECTION_TEXT
    assert by_title["Resumen ejecutivo"] == MISSING_SECTION_TEXT

    # La función no modifica la lista recibida.
    assert len(original_sections) == 6
    assert original_sections[0].startswith("Objetivo y alcance\n")


def test_unknown_deterministic_section_is_not_silently_discarded():
    """Un título desconocido se comunica en lugar de perder su contenido."""
    from src.reporting.templates import arrange_deterministic_sections

    with pytest.raises(ValueError, match="No se reconoce"):
        arrange_deterministic_sections([
            "Apartado inesperado\nInformación que no debe desaparecer."
        ])