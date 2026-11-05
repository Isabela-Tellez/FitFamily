"""Workflow de investigación, análisis, redacción y revisión de FitFamily."""
from decimal import Decimal
from math import isfinite
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.researcher import run_research
from src.analysis.contracts import CalculatedMetric
from src.analysis.calculation_adapter import metric_from_break_even
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.graph.state import ResearchState
from src.reporting.models import ReportClaim, ReportDraft
from src.reporting.report_builder import build_report
from src.review.models import ReviewIssue
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult


def research_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta investigación web real y conserva el resultado íntegro."""
    brief = ResearchBrief.model_validate(state["brief"])
    result = run_research(brief)
    return {
        "research_result": result.model_dump(mode="json"),
        "current_stage": "analysis",
        "updated_at": _utc_now(),
    }


def analysis_node(state: ResearchState) -> dict[str, Any]:
    """Calcula indicadores únicamente cuando el encargo aporta supuestos."""
    brief = ResearchBrief.model_validate(state["brief"])
    params = brief.assumed_params or {}
    required = (
        "expected_clients", "monthly_fee", "fixed_costs",
        "variable_cost_per_client",
    )
    missing = [name for name in required if name not in params or params[name] is None]
    if missing:
        return {
            "analysis_result": {
                "scenarios": [],
                "calculated_metrics": [],
                "limitations": [
                    "No se calcularon indicadores económicos. Faltan supuestos: "
                    + ", ".join(missing) + ". No se sustituyen por valores ficticios."
                ],
            },
            "current_stage": "writing",
            "updated_at": _utc_now(),
        }

    numeric_params: dict[str, int | float] = {}
    for name in required:
        value = params[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"El parámetro financiero {name!r} debe ser un número finito.")
        numeric_params[name] = value
    if type(numeric_params["expected_clients"]) is not int:
        raise ValueError("expected_clients debe ser un número entero.")

    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=numeric_params["expected_clients"],
        monthly_fee=numeric_params["monthly_fee"],
        fixed_costs=numeric_params["fixed_costs"],
        variable_cost_per_client=numeric_params["variable_cost_per_client"],
        assumptions=[f"{name} es un supuesto introducido por la persona usuaria." for name in required],
    )
    calculations = evaluate_economic_scenario(
        scenario,
        limitations=[
            "Proyección calculada con supuestos aportados por la persona usuaria; "
            "no es un dato observado ni garantiza rentabilidad."
        ],
    )
    metrics = []
    for calculation in calculations:
        result = calculation.result
        if calculation.calculation_type == "break_even":
            # El adaptador conserva escenario, entradas, supuestos y cálculo
            # original para que Gema y María utilicen el mismo contrato.
            metrics.append(metric_from_break_even(scenario, calculation))
        else:
            metrics.append(CalculatedMetric(
                metric_id=calculation.calculation_type,
                value=Decimal(str(result.value)) if result is not None else None,
                unit=result.unit if result is not None else "unknown",
                calculation=calculation.operation,
                evidence_ids=calculation.evidence_ids,
            ))

    return {
        "analysis_result": {
            "scenarios": [{
                "scenario": scenario.model_dump(mode="json"),
                "calculations": [item.model_dump(mode="json") for item in calculations],
            }],
            "calculated_metrics": [item.model_dump(mode="json") for item in metrics],
            "limitations": list(dict.fromkeys(
                limitation for item in calculations for limitation in item.limitations
            )),
        },
        "current_stage": "writing",
        "updated_at": _utc_now(),
    }


def writing_node(state: ResearchState) -> dict[str, Any]:
    """Redacta un único borrador conectando las métricas del analista.

    El modo determinista es el valor predeterminado y no requiere claves LLM.
    El modo LLM es opcional y se activa explícitamente desde la UI.
    """
    brief = ResearchBrief.model_validate(state["brief"])
    research = ResearchResult.model_validate(state["research_result"])
    analysis = state.get("analysis_result") or {}
    metrics = [CalculatedMetric.model_validate(item)
               for item in analysis.get("calculated_metrics", [])]
    use_llm = state.get("writer_mode", "deterministic") == "llm"
    # El constructor de afirmaciones financieras actual admite el punto de
    # equilibrio. El resto de métricas sigue disponible para visualización y
    # revisión, pero no se fuerza a entrar en un contrato que no les corresponde.
    report_metrics = [
        metric for metric in metrics
        if metric.context is not None
        and metric.context.calculation_result.calculation_type == "break_even"
    ]
    draft = build_report(
        brief, research, use_llm=use_llm, calculated_metrics=report_metrics
    )
    return {
        "report_draft": _draft_to_dict(draft),
        "report_version_id": f"{draft.draft_id}:{draft.version}",
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def review_node(state: ResearchState) -> dict[str, Any]:
    """Revisa el borrador, sus evidencias y las métricas del análisis."""
    research = ResearchResult.model_validate(state["research_result"])
    draft_data = dict(state["report_draft"])
    draft_data["claims"] = [
        claim if isinstance(claim, ReportClaim) else ReportClaim(**claim)
        for claim in draft_data.get("claims", [])
    ]
    draft = ReportDraft(**draft_data)
    analysis = state.get("analysis_result") or {}
    metrics = [CalculatedMetric.model_validate(item)
               for item in analysis.get("calculated_metrics", [])]
    review = run_basic_review(draft, research, calculated_metrics=metrics)

    # Una búsqueda fallida no puede avanzar a aprobación solo porque no haya
    # afirmaciones que revisar. Se bloquea con una incidencia trazable.
    evidence_count = len(research.evidences) + sum(
        len(competitor.evidences) for competitor in research.competitors
    )
    if evidence_count == 0:
        review = type(review)(
            draft_id=review.draft_id,
            draft_version=review.draft_version,
            draft_fingerprint=review.draft_fingerprint,
            issues=review.issues + (ReviewIssue(
                code="no_research_evidence",
                reference_id=draft.draft_id,
                message=(
                    "La investigación no devolvió evidencias utilizables. "
                    "Comprueba la conexión y repite la búsqueda antes de aprobar."
                ),
                severity="error",
                correction_stage="research",
            ),),
            checks_performed=review.checks_performed + ("research_evidence_presence",),
            research_fingerprint=review.research_fingerprint,
            analysis_fingerprint=review.analysis_fingerprint,
        )

    return {
        "review_result": _review_to_dict(review),
        "status": "awaiting_approval" if review.status == "pending_review" else "failed",
        "current_stage": "approval" if review.status == "pending_review" else "review",
        "updated_at": _utc_now(),
    }


def build_workflow(*, checkpointer: Any = None) -> Any:
    """Construye y compila el workflow principal de FitFamily."""
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
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _draft_to_dict(draft: ReportDraft) -> dict[str, Any]:
    from dataclasses import asdict
    return asdict(draft)


def _review_to_dict(review: Any) -> dict[str, Any]:
    from dataclasses import asdict
    return asdict(review)
