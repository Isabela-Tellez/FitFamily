"""Construcción de la vista ejecutiva del informe FitFamily."""

import re
from decimal import Decimal, InvalidOperation

from src.schemas import ResearchBrief, ResearchResult
from src.reporting.models import (
    ReportDraft,
    ExecutiveReport,
    ExecutiveKPI,
    ExecutiveScenario,
)
from src.analysis.contracts import CalculatedMetric
from src.reporting.calculated_claims import SCENARIO_NAMES


def _get_section_body(
    draft: ReportDraft,
    possible_titles: tuple[str, ...],
) -> str:
    """Extrae el cuerpo de una sección existente."""

    for section in draft.sections:
        heading, separator, body = section.partition("\n")

        if heading.strip() in possible_titles:
            return body.strip() if separator else ""

    return ""


def _parse_price(value) -> Decimal | None:
    """Convierte un precio observado en Decimal."""

    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, (int, float, Decimal)):
        try:
            result = Decimal(str(value))
            return result if result.is_finite() and result > 0 else None
        except InvalidOperation:
            return None

    if not isinstance(value, str):
        return None

    match = re.search(r"\d[\d.,]*", value.replace(" ", ""))

    if not match:
        return None

    number = match.group()

    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        number = number.replace(",", ".")

    try:
        result = Decimal(number)
        return result if result.is_finite() and result > 0 else None
    except InvalidOperation:
        return None


def _is_monthly(frequency: str | None, unit: str | None = None) -> bool:
    """Solo acepta precios identificados explícitamente como mensuales."""

    frequency = (frequency or "").lower().strip()
    unit = (unit or "").lower().strip()

    return (
        frequency in {"monthly", "mensual", "month"}
        or "/mes" in unit
        or "€/mes" in unit
        or "eur/month" in unit
    )


def _get_starting_price(
    research: ResearchResult,
) -> Decimal | None:
    """Obtiene el menor precio mensual documentado."""

    prices = []

    # Tarifas asociadas a competidores.
    for competitor in research.competitors:
        for tariff in competitor.tariffs:
            if not _is_monthly(
                tariff.get("frequency"),
                tariff.get("unit"),
            ):
                continue

            value = _parse_price(tariff.get("value"))

            if value is not None:
                prices.append(value)

    # Evidencias generales de precios.
    for evidence in research.evidences:
        if not _is_monthly(evidence.frequency, evidence.unit):
            continue

        value = _parse_price(evidence.value)

        if value is not None:
            prices.append(value)

    return min(prices) if prices else None


def _format_euros(value: Decimal) -> str:
    """Formatea una cantidad utilizando el formato español."""

    formatted = f"{value:,.2f}"
    formatted = formatted.replace(",", "X")
    formatted = formatted.replace(".", ",")
    formatted = formatted.replace("X", ".")

    if formatted.endswith(",00"):
        formatted = formatted[:-3]

    return f"{formatted} €"


def _format_chart_value(value: Decimal) -> str:
    """Formatea las cifras para las etiquetas del gráfico."""

    if abs(value) >= 1000:
        return (
            f"{value / Decimal('1000'):.1f}".replace(".", ",")
            + " mil €"
        )

    return _format_euros(value)


def _count_competitors(research: ResearchResult) -> int:
    """Cuenta competidores únicos presentes en la investigación."""

    identifiers = set()

    for index, competitor in enumerate(research.competitors):
        identity = (
            competitor.identifier
            or (competitor.name.lower().strip() if competitor.name else None)
        )

        if identity:
            identifiers.add(identity)
        else:
            identifiers.add(f"unknown_{index}")

    return len(identifiers)


def _build_scenarios(
    metrics: list[CalculatedMetric],
) -> list[ExecutiveScenario]:
    """Extrae los resultados mensuales sin recalcularlos."""

    scenarios = {}

    for metric in metrics:
        if metric.context is None or metric.value is None:
            continue

        calculation_type = (
            metric.context.calculation_result.calculation_type
        )

        if calculation_type != "monthly_result":
            continue

        scenario = metric.context.scenario

        name = scenario.scenario_type

        if name not in SCENARIO_NAMES:
            continue

        if not metric.value.is_finite():
            continue

        scenarios[name] = ExecutiveScenario(
            name=SCENARIO_NAMES[name].capitalize(),
            value=float(metric.value),
            formatted_value=_format_chart_value(metric.value),
        )

    return [
        scenarios[name]
        for name in ("conservative", "intermediate", "optimistic")
        if name in scenarios
    ]


def build_executive_report(
    draft: ReportDraft,
    brief: ResearchBrief,
    research_result: ResearchResult,
    calculated_metrics: list[CalculatedMetric],
) -> ExecutiveReport:
    """Construye la presentación ejecutiva desde datos existentes."""

    sections = {
        "Resumen ejecutivo": _get_section_body(
            draft,
            ("Resumen ejecutivo",),
        ),
        "Mercado y competencia": _get_section_body(
            draft,
            ("Mercado y competencia", "Competencia"),
        ),
        "Precios": _get_section_body(
            draft,
            ("Precios", "Precios y servicios"),
        ),
        "Conclusión preliminar": _get_section_body(
            draft,
            (
                "Conclusión preliminar",
                "Conclusiones",
                "Conclusión",
            ),
        ),
    }

    scenarios = _build_scenarios(calculated_metrics)

    centers = _count_competitors(research_result)
    starting_price = _get_starting_price(research_result)

    kpis = []

    if centers:
        kpis.append(
            ExecutiveKPI(
                label="Centros identificados",
                value=str(centers),
            )
        )

    if starting_price is not None:
        kpis.append(
            ExecutiveKPI(
                label="Precio desde",
                value=_format_euros(starting_price),
            )
        )

    if scenarios:
        kpis.append(
            ExecutiveKPI(
                label="Escenarios económicos",
                value=str(len(scenarios)),
            )
        )

    return ExecutiveReport(
        title=(
            f"Estudio de viabilidad: "
            f"{brief.business_type} en {brief.study_area}"
        ),
        subtitle=(
            f"{brief.location} · "
            "Informe de mercado y análisis económico"
        ),
        kpis=kpis,
        sections=sections,
        scenarios=scenarios,
    )