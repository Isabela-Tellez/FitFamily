"""Workflow principal de investigación de FitFamily mediante LangGraph."""

from decimal import Decimal
from math import isfinite
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.agents.researcher import run_research
from src.analysis.contracts import CalculatedMetric
from src.analysis.scenarios import (
    create_economic_scenario,
    evaluate_economic_scenario,
)
from src.graph.state import ResearchState
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult
from src.reporting.report_builder import build_report
from src.analysis.calculation_adapter import metric_from_break_even


def research_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta la investigación y actualiza el estado compartido."""
    brief = ResearchBrief.model_validate(state["brief"])
    result = run_research(brief)

    return {
        "research_result": result.model_dump(mode="json"),
        "current_stage": "analysis",
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

    metrics = []

    for calculation in calculations:
        if calculation.calculation_type == "break_even":
            # Conservamos el escenario y el cálculo originales.
            metric = metric_from_break_even(
                scenario,
                calculation,
            )
        else:
            # Los demás cálculos mantienen su contrato actual.
            result = calculation.result

            metric = CalculatedMetric(
                metric_id=calculation.calculation_type,
                value=(
                    Decimal(str(result.value))
                    if result is not None
                    else None
                ),
                unit=result.unit if result is not None else "unknown",
                calculation=calculation.operation,
                evidence_ids=calculation.evidence_ids,
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
            "limitations": [
                limitation
                for calculation in calculations
                for limitation in calculation.limitations
            ],
        },
        "current_stage": "writing",
        "updated_at": _utc_now(),
    }



def writing_node(state: ResearchState) -> dict[str, Any]:
    """Genera un borrador con las métricas del análisis compartido."""
    brief = ResearchBrief.model_validate(state["brief"])
    research = ResearchResult.model_validate(state["research_result"])

    # Recuperamos las métricas calculadas en el nodo anterior.
    analysis = state.get("analysis_result") or {}
    metrics = [
        CalculatedMetric.model_validate(item)
        for item in analysis.get("calculated_metrics", [])
    ]

    # Delegamos la construcción del informe al componente compartido.
    draft = build_report(
        brief,
        research,
        use_llm=True,
        calculated_metrics=metrics,
    )

    return {
        "report_draft": _draft_to_dict(draft),
        "report_version_id": f"{draft.draft_id}:{draft.version}",
        "approval_decision": None,
        "approved_version_id": None,
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def review_node(state: ResearchState) -> dict[str, Any]:
    """Revisa el borrador usando la investigación y el análisis."""
    research = ResearchResult.model_validate(state["research_result"])
    draft_data = state["report_draft"]

    draft = ReportDraft(
        **{
            **draft_data,
            "claims": [
                claim if isinstance(claim, ReportClaim)
                else ReportClaim(**claim)
                for claim in draft_data.get("claims", [])
            ],
        }
)

    analysis = state.get("analysis_result") or {}
    metrics_data = analysis.get("calculated_metrics", [])

    metrics = [
        CalculatedMetric.model_validate(item)
        for item in metrics_data
    ]

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    # No permitimos aprobar un borrador con incidencias.
    has_errors = any(
        issue.severity == "error"
        for issue in review.issues
    )

    if has_errors:
        status = "failed"
    else:
        status = "awaiting_approval"

    return {
        "review_result": _review_to_dict(review),
        "status": status,
        "approval_decision": None,
        "approved_version_id": None,
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def approval_node(state: ResearchState) -> dict[str, Any]:
    """Solicita aprobación humana para una versión concreta del informe."""

    if state.get("status") != "awaiting_approval":
        raise ValueError(
            "El informe no está listo para solicitar aprobación."
        )

    report_version_id = state.get("report_version_id")
    draft_data = state.get("report_draft")

    if not report_version_id or not draft_data:
        raise ValueError(
            "No existe una versión válida del informe para aprobar."
        )

    # La revisión automática debe haberse completado sin incidencias.
    review_data = state.get("review_result")

    if not review_data:
        raise ValueError("No existe una revisión del informe.")

    issues = review_data.get("issues", [])

    has_errors = any(
        issue.get("severity") == "error"
        for issue in issues
    )

    if has_errors:
        raise ValueError(
            "No se puede solicitar aprobación con errores pendientes."
        )

    # LangGraph pausa aquí y espera una decisión externa.
    decision = interrupt(
        {
            "type": "human_approval",
            "run_id": state["run_id"],
            "report_version_id": report_version_id,
            "draft": draft_data,
            "message": "¿Apruebas esta versión del informe?",
            "allowed_decisions": ["approved", "rejected"],
        }
    )

    if not isinstance(decision, dict):
        raise ValueError("La decisión de aprobación no es válida.")

    if decision.get("decision") not in ("approved", "rejected"):
        raise ValueError(
            "La decisión debe ser 'approved' o 'rejected'."
        )

    # Impedimos aprobar una versión distinta de la presentada.
    if decision.get("report_version_id") != report_version_id:
        raise ValueError(
            "La decisión no corresponde a la versión actual del informe."
        )

    approved = decision["decision"] == "approved"

    return {
        "approval_decision": decision["decision"],
        "approved_version_id": (
            report_version_id if approved else None
        ),
        "status": "completed" if approved else "rejected",
        "current_stage": "completed" if approved else "rejected",
        "updated_at": _utc_now(),
    }


def build_workflow(*, checkpointer: Any = None) -> Any:
    """Construye el workflow con una pausa para aprobación humana."""

    builder = StateGraph(ResearchState)

    builder.add_node("research", research_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("writing", writing_node)
    builder.add_node("review", review_node)
    builder.add_node("approval", approval_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "analysis")
    builder.add_edge("analysis", "writing")
    builder.add_edge("writing", "review")

    # Solo los informes sin incidencias pasan a aprobación.
    builder.add_conditional_edges(
        "review",
        lambda state: (
            "approval"
            if state.get("status") == "awaiting_approval"
            else END
        ),
        {
            "approval": "approval",
            END: END,
        },
    )

    builder.add_edge("approval", END)

    return builder.compile(checkpointer=checkpointer)


def _route_after_review(state: ResearchState) -> str:
    """Solicita aprobación solo cuando la revisión no tiene errores."""
    if state.get("status") == "awaiting_approval":
        return "approval"

    return "end"


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
