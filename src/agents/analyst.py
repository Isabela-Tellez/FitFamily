"""Agente de análisis de mercado y viabilidad económica de FitFamily.

Calcula indicadores de mercado y escenarios económicos reproducibles.
Separa los datos observados de los supuestos y registra las limitaciones.
"""

from __future__ import annotations

import logging
from math import isfinite
from typing import Any

import pandas as pd
from crewai import Agent, Task
from pydantic import BaseModel, Field

from src.schemas import ResearchResult
from src.analysis.market_analysis import summarize_competitors
from src.analysis.scenarios import (
    create_economic_scenario,
    compare_economic_scenarios,
)

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    """Resultado estructurado del análisis de mercado y económico."""

    market_indicators: dict[str, Any] = Field(default_factory=dict)
    competitor_comparison: list[dict[str, Any]] = Field(
        default_factory=list
    )
    economic_scenarios: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict
    )
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def build_analyst() -> Agent:
    """Construye el agente responsable del análisis."""

    return Agent(
        role="Analista de mercado y viabilidad económica",
        goal=(
            "Analizar los datos de la investigación, calcular indicadores "
            "reproducibles y distinguir los datos observados de los "
            "supuestos económicos."
        ),
        backstory=(
            "Eres una analista especializada en estudios de mercado y "
            "viabilidad económica. No inventas precios, servicios ni "
            "evidencias. Respetas las unidades y condiciones originales, "
            "y distingues los cálculos matemáticos de las hipótesis."
        ),
        tools=[],
        allow_delegation=False,
        verbose=False,
    )


def build_analysis_task(
    research: ResearchResult,
    assumptions: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> Task:
    """Prepara una tarea de análisis a partir de la investigación."""

    assumptions = assumptions or {}
    context = context or {}

    description = (
        "Analiza la investigación de mercado de FitFamily.\n\n"
        "Instrucciones:\n"
        "- No inventes datos ni evidencias.\n"
        "- No interpretes datos ausentes como cero.\n"
        "- No mezcles tarifas mensuales, anuales y pagos únicos.\n"
        "- Distingue las observaciones de los supuestos.\n"
        "- Explica las limitaciones de los datos disponibles.\n"
        "- No presentes los escenarios como predicciones garantizadas.\n\n"
        f"Investigación:\n{research.model_dump_json(indent=2)}\n\n"
        f"Supuestos:\n{assumptions}\n\n"
        f"Contexto:\n{context}\n"
    )

    return Task(
        description=description,
        expected_output=(
            "Un análisis conciso de los competidores, los indicadores "
            "calculados, los escenarios económicos y sus limitaciones. "
            "No añadas cifras que no estén respaldadas por datos o "
            "cálculos reproducibles."
        ),
        agent=build_analyst(),
    )


def _validate_research(
    research: ResearchResult | dict[str, Any],
) -> ResearchResult:
    """Valida los datos recibidos de la investigación."""

    if isinstance(research, ResearchResult):
        return research

    return ResearchResult.model_validate(research)


def _extract_monthly_price(
    tariffs: list[dict[str, Any]],
) -> float | None:
    """Devuelve un precio mensual solo si resulta inequívoco."""

    monthly_prices: list[float] = []

    for tariff in tariffs:
        frequency = str(
            tariff.get("frequency") or ""
        ).strip().casefold()

        if frequency not in {"monthly", "mensual", "month"}:
            continue

        value = tariff.get("value")

        if isinstance(value, bool):
            continue

        try:
            price = float(value)
        except (TypeError, ValueError):
            continue

        if not isfinite(price) or price < 0:
            continue

        monthly_prices.append(price)

    # Si hay tarifas mensuales diferentes, no elegimos una arbitrariamente.
    unique_prices = list(dict.fromkeys(monthly_prices))

    if len(unique_prices) == 1:
        return unique_prices[0]

    return None


def _build_competitor_data(
    research: ResearchResult,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Prepara los datos para el análisis y la comparación."""

    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for competitor in research.competitors:
        price = _extract_monthly_price(competitor.tariffs)

        evidence_ids = [
            evidence.evidence_id
            for evidence in competitor.evidences
            if evidence.evidence_id
        ]

        name = competitor.name or "Nombre desconocido"

        rows.append(
            {
                "gym_name": name,
                "monthly_price_eur": price,
                "has_playroom": competitor.has_playroom,
            }
        )

        details.append(
            {
                "identifier": competitor.identifier,
                "gym_name": name,
                "location": competitor.location,
                "monthly_price_eur": price,
                "price_conditions": [
                    tariff.get("condition")
                    for tariff in competitor.tariffs
                    if tariff.get("condition")
                ],
                "has_playroom": competitor.has_playroom,
                "services": competitor.services,
                "evidence_ids": evidence_ids,
                "verification_status": competitor.verification_status,
            }
        )

    dataframe = pd.DataFrame(
        rows,
        columns=[
            "gym_name",
            "monthly_price_eur",
            "has_playroom",
        ],
    )

    return dataframe, details


def _sort_competitors(
    competitors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ordena por precio mensual y deja los precios desconocidos al final."""

    return sorted(
        competitors,
        key=lambda item: (
            item["monthly_price_eur"] is None,
            (
                item["monthly_price_eur"]
                if item["monthly_price_eur"] is not None
                else 0
            ),
            item["gym_name"].casefold(),
        ),
    )


def _build_economic_scenarios(
    assumptions: dict[str, Any],
    context: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[str], list[str]]:
    """Calcula tres escenarios si se proporcionan todos los parámetros."""

    economic_inputs = assumptions.get("economic", assumptions)

    required = (
        "expected_clients",
        "monthly_fee",
        "fixed_costs",
        "variable_cost_per_client",
    )

    missing = [
        name
        for name in required
        if name not in economic_inputs or economic_inputs[name] is None
    ]

    if missing:
        return (
            {},
            [],
            [
                "No se han calculado escenarios económicos porque faltan "
                f"parámetros: {', '.join(missing)}."
            ],
        )

    expected_clients = economic_inputs["expected_clients"]

    if (
        isinstance(expected_clients, bool)
        or not isinstance(expected_clients, int)
    ):
        raise ValueError("expected_clients debe ser un número entero.")

    numeric_parameters: dict[str, float] = {}

    for name in (
        "monthly_fee",
        "fixed_costs",
        "variable_cost_per_client",
    ):
        value = economic_inputs[name]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} debe ser numérico.")

        if not isfinite(value):
            raise ValueError(f"{name} debe ser un número finito.")

        numeric_parameters[name] = float(value)

    monthly_fee = numeric_parameters["monthly_fee"]
    fixed_costs = numeric_parameters["fixed_costs"]
    variable_cost = numeric_parameters["variable_cost_per_client"]

    if expected_clients < 0:
        raise ValueError("expected_clients no puede ser negativo.")

    if monthly_fee <= 0:
        raise ValueError("monthly_fee debe ser mayor que cero.")

    if fixed_costs < 0 or variable_cost < 0:
        raise ValueError("Los costes no pueden ser negativos.")

    if monthly_fee <= variable_cost:
        raise ValueError(
            "monthly_fee debe superar variable_cost_per_client "
            "para calcular el punto de equilibrio."
        )

    # Estos porcentajes son hipótesis de sensibilidad, no datos observados.
    scenario_definitions = [
        (
            "conservative",
            int(expected_clients * 0.8),
            "Se supone un 20 % menos de clientes que en el escenario "
            "de referencia.",
        ),
        (
            "intermediate",
            expected_clients,
            "Se utiliza el número de clientes proporcionado como referencia.",
        ),
        (
            "optimistic",
            int(expected_clients * 1.2),
            "Se supone un 20 % más de clientes que en el escenario "
            "de referencia.",
        ),
    ]

    scenarios = []
    assumptions_used = []

    for scenario_type, clients, description in scenario_definitions:
        scenario = create_economic_scenario(
            scenario_type=scenario_type,
            expected_clients=clients,
            monthly_fee=monthly_fee,
            fixed_costs=fixed_costs,
            variable_cost_per_client=variable_cost,
            assumptions=[
                description,
                "Los parámetros económicos proceden de los supuestos "
                "proporcionados al análisis.",
            ],
        )

        scenarios.append(scenario)
        assumptions_used.append(description)

    evidence_ids = context.get("economic_evidence_ids", [])

    if not isinstance(evidence_ids, list):
        evidence_ids = []

    comparison = compare_economic_scenarios(
        scenarios=scenarios,
        evidence_ids=evidence_ids,
        limitations=[
            "Los resultados son cálculos basados en supuestos y no "
            "garantizan la rentabilidad del negocio."
        ],
    )

    serialized = {
        scenario_id: [
            calculation.model_dump(mode="json")
            for calculation in calculations
        ]
        for scenario_id, calculations in comparison.items()
    }

    return serialized, assumptions_used, []


def run_analysis(
    research: ResearchResult | dict[str, Any],
    assumptions: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Ejecuta el análisis de mercado y los escenarios económicos."""

    research_result = _validate_research(research)
    assumptions = assumptions or {}
    context = context or {}

    limitations: list[str] = []

    # 1. Analizar los competidores.
    competitors_df, competitor_details = _build_competitor_data(
        research_result
    )

    market_indicators = summarize_competitors(competitors_df)

    competitor_count = market_indicators["competitor_count"]
    known_price_count = market_indicators["known_price_count"]

    market_indicators["price_coverage_percentage"] = (
        round(known_price_count / competitor_count * 100, 2)
        if competitor_count
        else 0.0
    )

    competitor_comparison = _sort_competitors(competitor_details)

    if competitor_count == 0:
        limitations.append(
            "La investigación no contiene competidores para comparar."
        )

    if known_price_count < competitor_count:
        limitations.append(
            "Algunos competidores no tienen un precio mensual inequívoco. "
            "Los precios desconocidos no se han interpretado como cero."
        )

    if research_result.coverage_percentage < 100:
        limitations.append(
            "La cobertura declarada de la investigación es del "
            f"{research_result.coverage_percentage:.1f} %."
        )

    if research_result.unresolved_questions:
        limitations.append(
            "Preguntas sin resolver: "
            + "; ".join(research_result.unresolved_questions)
        )

    if research_result.notes:
        limitations.append(
            "Notas de investigación: " + research_result.notes
        )

    # 2. Calcular los escenarios económicos.
    (
        economic_scenarios,
        scenario_assumptions,
        scenario_limitations,
    ) = _build_economic_scenarios(assumptions, context)

    limitations.extend(scenario_limitations)

    result = AnalysisResult(
        market_indicators=market_indicators,
        competitor_comparison=competitor_comparison,
        economic_scenarios=economic_scenarios,
        assumptions=scenario_assumptions,
        limitations=list(dict.fromkeys(limitations)),
    )

    logger.info(
        "Análisis completado: %s competidores y %s escenarios económicos.",
        competitor_count,
        len(economic_scenarios),
    )

    return result