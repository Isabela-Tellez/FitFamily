"""Estructura común del contenido del informe de FitFamily.

Los renderizadores añaden por separado las fuentes, las limitaciones
y el registro de afirmaciones. No los repetimos aquí.
"""

# Una tupla mantiene un orden común y evita modificarlo accidentalmente.
REPORT_SECTION_TITLES: tuple[str, ...] = (
    "Resumen ejecutivo",
    "Objetivo y alcance",
    "Método y fuentes de datos",
    "Público potencial",
    "Competencia",
    "Precios y servicios",
    "Análisis visual",
    "Escenarios económicos",
    "Oportunidades y riesgos",
    "Incertidumbres",
    "Próximos pasos",
)

# Esta frase solo se utilizará cuando falte contenido para un apartado.
# No significa que se haya ejecutado una investigación o un análisis.
MISSING_SECTION_TEXT = (
    "No se ha incorporado información para este apartado. "
    "Queda pendiente de completar y revisar."
)

def validate_report_sections(sections: list[str]) -> None:
    """Comprueba los títulos y el orden de las secciones.

    No modifica el texto ni comprueba la veracidad del contenido.
    """
    actual_titles = [
        section.strip().partition("\n")[0].strip()
        for section in sections
    ]

    if actual_titles != list(REPORT_SECTION_TITLES):
        raise ValueError(
            "La estructura del informe no coincide con los apartados "
            "requeridos: deben estar completos, en orden y sin duplicados."
        )

    # Cada apartado debe tener contenido o indicar que está pendiente.
    for section in sections:
        _, separator, body = section.strip().partition("\n")

        if not separator or not body.strip():
            raise ValueError(
                "Cada apartado debe incluir contenido "
                "o indicar que está pendiente."
            )

def arrange_deterministic_sections(sections: list[str]) -> list[str]:
    """Ordena las secciones del redactor sin perder contenido."""
    contents: dict[str, list[str]] = {
        title: [] for title in REPORT_SECTION_TITLES
    }

    legacy_titles = {
        "Competidores y tarifas": "Competencia",
        "Tarifas documentadas": "Precios y servicios",
        "Supuestos del encargo": "Escenarios económicos",
        "Proceso de investigación": "Método y fuentes de datos",
        "Preguntas pendientes": "Incertidumbres",
    }

    for section in sections:
        heading, _, body = section.strip().partition("\n")
        heading = heading.strip()
        target = legacy_titles.get(heading, heading)

        if target not in contents:
            raise ValueError(
                f"No se reconoce el apartado del redactor: {heading}"
            )

        content = (
            section.strip()
            if heading in legacy_titles
            else body.strip()
        )

        if content:
            contents[target].append(content)

    return [
        f"{title}\n"
        + (
            "\n\n".join(contents[title])
            if contents[title]
            else MISSING_SECTION_TEXT
        )
        for title in REPORT_SECTION_TITLES
    ]