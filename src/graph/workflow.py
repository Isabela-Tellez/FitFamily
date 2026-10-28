"""Workflow principal de investigación de FitFamily mediante LangGraph."""

from decimal import Decimal
from math import isfinite
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.researcher import run_research
from src.analysis.calculation_adapter import metric_from_break_even
from src.analysis.contracts import CalculatedMetric
from src.analysis.scenarios import (
    create_economic_scenario,
    evaluate_economic_scenario,
)
from src.graph.state import ResearchState
from src.reporting.models import ReportDraft
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult


def research_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta la investigación y actualiza el estado compartido."""
    brief = ResearchBrief.model_validate(state["brief"])
    result = run_research(brief)

    return {
        "research_result": result.model_dump(mode="json"),
        "current_stage": "writing",
        "updated_at": _utc_now(),
    }


def analysis_node(state: ResearchState) -> dict[str, Any]:
    """Calcula indicadores económicos a partir de parámetros validados."""
    brief = ResearchBrief.model_validate(state["brief"])
    params = brief.assumed_params or {}

    required = (
        "expected_clients",
        "monthly_fee",
        "fixed_costs",
        "variable_cost_per_client",
    )

    missing = [
        name
        for name in required
        if name not in params or params[name] is None
    ]

    if missing:
        return {
            "analysis_result": {
                "scenarios": [],
                "calculated_metrics": [],
                "limitations": [
                    "No se pudieron calcular los indicadores económicos. "
                    f"Faltan parámetros: {', '.join(missing)}."
                ],
            },
            "current_stage": "writing",
            "updated_at": _utc_now(),
        }

    # No aceptamos booleanos como números ni valores no finitos.
    numeric_params: dict[str, int | float] = {}

    for name in required:
        value = params[name]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
        ):
            raise ValueError(
                f"El parámetro financiero {name!r} "
                "debe ser un número finito."
            )

        numeric_params[name] = value

    # El número de clientes debe ser entero.
    expected_clients = numeric_params["expected_clients"]

    if not isinstance(expected_clients, int):
        raise ValueError(
            "expected_clients debe ser un número entero."
        )

    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=expected_clients,
        monthly_fee=numeric_params["monthly_fee"],
        fixed_costs=numeric_params["fixed_costs"],
        variable_cost_per_client=numeric_params[
            "variable_cost_per_client"
        ],
        assumptions=[
            f"{name} procede de assumed_params del encargo."
            for name in required
        ],
    )

    calculations = evaluate_economic_scenario(
        scenario,
        limitations=[
            "Los resultados son proyecciones basadas en los parámetros "
            "proporcionados; no garantizan la rentabilidad del negocio."
        ],
    )

    metrics: list[CalculatedMetric] = []

    for calculation in calculations:
        if calculation.calculation_type == "break_even":
            # Conserva el escenario y el cálculo original.
            metric = metric_from_break_even(
                scenario,
                calculation,
            )
        else:
            result = calculation.result

            metric = CalculatedMetric(
                metric_id=calculation.calculation_type,
                value=(
                    Decimal(str(result.value))
                    if result is not None
                    else None
                ),
                unit=(
                    result.unit
                    if result is not None
                    else "unknown"
                ),
                calculation=calculation.operation,
                evidence_ids=list(calculation.evidence_ids),
            )

        metrics.append(metric)

    return {
        "analysis_result": {
            "scenarios": [
                {
                    "scenario": scenario.model_dump(mode="json"),
                    "calculations": [
                        calculation.model_dump(mode="json")
                        for calculation in calculations
                    ],
                }
            ],
            "calculated_metrics": [
                metric.model_dump(mode="json")
                for metric in metrics
            ],
            "limitations": list(
                dict.fromkeys(
                    limitation
                    for calculation in calculations
                    for limitation in calculation.limitations
                )
            ),
        },
        "current_stage": "writing",
        "updated_at": _utc_now(),
    }


def writing_node(state: ResearchState) -> dict[str, Any]:
    """Genera un borrador con investigación y métricas calculadas."""
    brief = ResearchBrief.model_validate(state["brief"])
    research = ResearchResult.model_validate(state["research_result"])

    analysis = state.get("analysis_result") or {}
    metrics_data = analysis.get("calculated_metrics", [])

    # Conservamos todas las métricas para el estado y la revisión.
    metrics = [
        CalculatedMetric.model_validate(item)
        for item in metrics_data
    ]

    # build_report solo admite actualmente métricas de punto de equilibrio.
    break_even_metrics = [
        metric
        for metric in metrics
        if (
            metric.context is not None
            and metric.context.calculation_result.calculation_type
            == "break_even"
        )
    ]

    draft = build_report(
        brief,
        research,
        use_llm=True,
        calculated_metrics=break_even_metrics,
    )

    # Conservamos las limitaciones del análisis.
    for limitation in analysis.get("limitations", []):
        if limitation not in draft.limitations:
            draft.limitations.append(limitation)

    return {
        "report_draft": _draft_to_dict(draft),
        "report_version_id": f"{draft.draft_id}:{draft.version}",
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def review_node(state: ResearchState) -> dict[str, Any]:
    """Revisa el borrador usando la investigación y el análisis."""
    research = ResearchResult.model_validate(state["research_result"])
    draft = ReportDraft(**state["report_draft"])

    analysis = state.get("analysis_result") or {}
    metrics_data = analysis.get("calculated_metrics", [])

    # La revisión recibe las cuatro métricas, no solo el punto de equilibrio.
    metrics = [
        CalculatedMetric.model_validate(item)
        for item in metrics_data
    ]

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    return {
        "review_result": _review_to_dict(review),
        "status": (
            "awaiting_approval"
            if not review.issues
            else "failed"
        ),
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def build_workflow(*, checkpointer: Any = None) -> Any:
    """Construye y compila el workflow de investigación."""
    builder = StateGraph(ResearchState)

    builder.add_node("research", research_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("writing", writing_node)
    builder.add_node("review", review_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "analysis")
    builder.add_edge("analysis", "writing")
    builder.add_edge("writing", "review")
    builder.add_edge("review", END)

    return builder.compile(checkpointer=checkpointer)


def _utc_now() -> str:
    """Devuelve la hora actual en UTC."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _draft_to_dict(draft: ReportDraft) -> dict[str, Any]:
    """Convierte el borrador en un diccionario serializable."""
    from dataclasses import asdict

    return asdict(draft)


def _review_to_dict(review: Any) -> dict[str, Any]:
    """Convierte el resultado de revisión en un diccionario serializable."""
    from dataclasses import asdict

    return asdict(review)
