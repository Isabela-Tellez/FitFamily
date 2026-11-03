"""Workflow principal de investigación de FitFamily mediante LangGraph."""

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.agents.researcher import run_research
from src.analysis.calculation_adapter import metric_from_break_even
from src.analysis.contracts import CalculatedMetric
from src.analysis.scenarios import (
    create_economic_scenario,
    evaluate_economic_scenario,
)
from src.automation.delivery import (
    ACTION_ORDER,
    export_approved_report,
)
from src.automation.models import ApprovalRecord, DeliveryResult
from src.graph.state import ResearchState
from src.reporting.models import ReportClaim, ReportDraft
from src.reporting.report_builder import build_report
from src.automation.exporter import calculate_draft_fingerprint
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult


# ============================================================
# RESEARCH NODE
# ============================================================
def research_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta la investigación y actualiza el estado compartido."""
    brief = ResearchBrief.model_validate(state["brief"])
    result = run_research(brief)

    return {
        "research_result": result.model_dump(mode="json"),
        "current_stage": "analysis",
        "updated_at": _utc_now(),
    }


# ============================================================
# ANALYSIS NODE
# ============================================================
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


# ============================================================
# WRITING NODE
# ============================================================
def writing_node(state: ResearchState) -> dict[str, Any]:
    """Genera un borrador nuevo e invalida autorizaciones anteriores."""
    brief = ResearchBrief.model_validate(state["brief"])
    research = ResearchResult.model_validate(state["research_result"])

    analysis = state.get("analysis_result") or {}

    metrics = [
        CalculatedMetric.model_validate(item)
        for item in analysis.get("calculated_metrics", [])
    ]

    draft = build_report(
        brief,
        research,
        use_llm=True,
        calculated_metrics=metrics,
    )

    return {
        "report_draft": _draft_to_dict(draft),
        "report_version_id": f"{draft.draft_id}:{draft.version}",
        # Invalidamos cualquier aprobación anterior.
        "approval_decision": None,
        "approval_record": None,
        "approved_version_id": None,
        "approved_at": None,
        "authorized_actions": [],
        # Invalidamos también las entregas anteriores.
        "delivery_result": None,
        "delivery_status": "not_started",
        "export_paths": [],
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


# ============================================================
# DRAFT RECONSTRUCTION
# ============================================================
def _draft_from_state(state: ResearchState) -> ReportDraft:
    """Reconstruye el borrador conservando sus afirmaciones."""
    draft_data = state.get("report_draft")

    if not isinstance(draft_data, dict):
        raise ValueError("No existe un borrador válido.")

    return ReportDraft(
        **{
            **draft_data,
            "claims": [
                claim if isinstance(claim, ReportClaim)
                else ReportClaim(**claim)
                for claim in draft_data.get("claims", [])
            ],
        }
    )


def _delivery_result_from_state(
    data: dict[str, Any] | None,
) -> DeliveryResult | None:
    """Reconstruye un resultado de entrega desde el estado persistido."""
    if data is None:
        return None

    if not isinstance(data, dict):
        raise ValueError(
            "El resultado de entrega almacenado no es válido."
        )

    return DeliveryResult(
        **{
            **data,
            "requested_actions": tuple(
                data["requested_actions"]
            ),
            "completed_actions": tuple(
                data["completed_actions"]
            ),
            "failed_actions": tuple(
                data["failed_actions"]
            ),
            "errors": tuple(
                tuple(error)
                for error in data.get("errors", [])
            ),
        }
    )


# ============================================================
# REVIEW NODE
# ============================================================
def review_node(state: ResearchState) -> dict[str, Any]:
    """Revisa el borrador usando la investigación y el análisis."""
    research = ResearchResult.model_validate(state["research_result"])
    draft = _draft_from_state(state)
    analysis = state.get("analysis_result") or {}

    metrics = [
        CalculatedMetric.model_validate(item)
        for item in analysis.get("calculated_metrics", [])
    ]

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    has_errors = any(
        issue.severity == "error"
        for issue in review.issues
    )

    status = "failed" if has_errors else "awaiting_approval"

    return {
        "review_result": _review_to_dict(review),
        "status": status,
        # Una nueva revisión invalida cualquier decisión anterior.
        "approval_decision": None,
        "approval_record": None,
        "approved_version_id": None,
        "approved_at": None,
        "authorized_actions": [],
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


# ============================================================
# APPROVAL NODE
# ============================================================
def approval_node(state: ResearchState) -> dict[str, Any]:
    """Solicita una decisión humana y registra su autorización."""
    if state.get("status") != "awaiting_approval":
        raise ValueError(
            "El informe no está listo para solicitar aprobación."
        )

    draft = _draft_from_state(state)
    report_version_id = state.get("report_version_id")
    expected_version_id = f"{draft.draft_id}:{draft.version}"

    if report_version_id != expected_version_id:
        raise ValueError(
            "La versión del informe no coincide con el borrador actual."
        )

    review_data = state.get("review_result")

    if not review_data:
        raise ValueError("No existe una revisión del informe.")

    if any(
        issue.get("severity") == "error"
        for issue in review_data.get("issues", [])
    ):
        raise ValueError(
            "No se puede solicitar aprobación con errores pendientes."
        )

    fingerprint = calculate_draft_fingerprint(draft)

    # Pausa del workflow hasta recibir una decisión humana.
    decision = interrupt(
        {
            "type": "human_approval",
            "run_id": state["run_id"],
            "report_version_id": report_version_id,
            "draft_id": draft.draft_id,
            "draft_version": draft.version,
            "draft_fingerprint": fingerprint,
            "draft": state["report_draft"],
            "message": (
                "¿Apruebas esta versión y sus acciones de entrega?"
            ),
            "allowed_decisions": ["approved", "rejected"],
            "available_actions": list(ACTION_ORDER),
        }
    )

    if not isinstance(decision, dict):
        raise ValueError("La decisión de aprobación no es válida.")

    decision_value = decision.get("decision")

    if decision_value not in ("approved", "rejected"):
        raise ValueError(
            "La decisión debe ser 'approved' o 'rejected'."
        )

    if decision.get("report_version_id") != report_version_id:
        raise ValueError(
            "La decisión no corresponde a la versión actual."
        )

    # --------------------------------------------------------
    # REJECTION
    # --------------------------------------------------------
    if decision_value == "rejected":
        return {
            "approval_decision": "rejected",
            "approval_record": None,
            "approved_version_id": None,
            "approved_at": None,
            "authorized_actions": [],
            "status": "rejected",
            "current_stage": "rejected",
            "delivery_status": "not_started",
            "updated_at": _utc_now(),
        }

    # --------------------------------------------------------
    # APPROVED ACTIONS
    # --------------------------------------------------------
    actions = decision.get("actions")

    if (
        not isinstance(actions, list)
        or not actions
        or any(not isinstance(action, str) for action in actions)
        or len(actions) != len(set(actions))
        or not set(actions).issubset(ACTION_ORDER)
    ):
        raise ValueError(
            "Debes indicar una lista válida de acciones autorizadas."
        )

    # El seguimiento requiere al menos un formato de informe.
    if (
        "update_tracking_csv" in actions
        and not {
            "export_markdown",
            "export_pdf",
        }.intersection(actions)
    ):
        raise ValueError(
            "El seguimiento CSV requiere autorizar Markdown o PDF."
        )

    authorized_actions = tuple(
        action
        for action in ACTION_ORDER
        if action in actions
    )

    decided_at = datetime.now(timezone.utc)

    approval = ApprovalRecord(
        run_id=state["run_id"],
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=fingerprint,
        approved=True,
        actions=authorized_actions,
        decided_at=decided_at,
    )

    return {
        "approval_decision": "approved",
        "approval_record": {
            **asdict(approval),
            "decided_at": decided_at.isoformat(),
        },
        "approved_version_id": report_version_id,
        "approved_at": decided_at.isoformat(),
        "authorized_actions": list(authorized_actions),
        # La aprobación no significa que la entrega esté completada.
        "status": "running",
        "current_stage": "delivery",
        "delivery_status": "not_started",
        "delivery_result": None,
        "export_paths": [],
        "updated_at": _utc_now(),
    }


# ============================================================
# DELIVERY NODE
# ============================================================
def delivery_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta la entrega real de un informe aprobado.

    Coordina las exportaciones mediante automation.delivery.
    Conserva los éxitos parciales para permitir reintentos.
    """
    if state.get("approval_decision") != "approved":
        raise ValueError(
            "No existe una aprobación válida."
        )

    if state.get("status") != "running":
        raise ValueError(
            "La ejecución no está preparada para entregar."
        )

    draft = _draft_from_state(state)

    # Comprobamos la versión aprobada.
    expected_version_id = f"{draft.draft_id}:{draft.version}"

    if state.get("approved_version_id") != expected_version_id:
        raise ValueError(
            "La aprobación no corresponde al borrador actual."
        )

    # --------------------------------------------------------
    # RECONSTRUCT APPROVAL
    # --------------------------------------------------------
    approval_data = state.get("approval_record")

    if not isinstance(approval_data, dict):
        raise ValueError(
            "No existe un registro de aprobación."
        )

    decided_at = datetime.fromisoformat(
        approval_data["decided_at"]
    )

    approval = ApprovalRecord(
        run_id=approval_data["run_id"],
        draft_id=approval_data["draft_id"],
        draft_version=approval_data["draft_version"],
        draft_fingerprint=approval_data["draft_fingerprint"],
        approved=approval_data["approved"],
        actions=tuple(approval_data["actions"]),
        decided_at=decided_at,
    )

    # --------------------------------------------------------
    # VALIDATE AUTHORIZED ACTIONS
    # --------------------------------------------------------
    if tuple(state.get("authorized_actions", [])) != approval.actions:
        raise ValueError(
            "Las acciones autorizadas no coinciden con la aprobación."
        )

    if approval.run_id != state["run_id"]:
        raise ValueError(
            "La aprobación pertenece a otra ejecución."
        )

    # --------------------------------------------------------
    # PREVIOUS DELIVERY RESULT
    # --------------------------------------------------------
    previous_result = _delivery_result_from_state(
        state.get("delivery_result")
    )

    # --------------------------------------------------------
    # EXECUTE DELIVERY
    # --------------------------------------------------------
    result = export_approved_report(
        draft=draft,
        approval=approval,
        run_id=state["run_id"],
        output_dir=state.get(
            "delivery_output_dir",
            "outputs/reports",
        ),
        csv_path=state.get(
            "delivery_csv_path",
            "outputs/tracking.csv",
        ),
        previous_result=previous_result,
    )

    # --------------------------------------------------------
    # DELIVERY STATUS
    # --------------------------------------------------------
    if result.complete:
        delivery_status = "completed"
        run_status = "completed"
        current_stage = "completed"
    elif result.completed_actions:
        delivery_status = "partial"
        run_status = "running"
        current_stage = "delivery_partial"
    else:
        delivery_status = "failed"
        run_status = "failed"
        current_stage = "delivery_failed"

    # --------------------------------------------------------
    # EXPORTED PATHS
    # --------------------------------------------------------
    export_paths = [
        path
        for path in (
            result.markdown_path,
            result.pdf_path,
            result.tracking_path,
        )
        if path
    ]

    return {
        "delivery_result": asdict(result),
        "delivery_status": delivery_status,
        "status": run_status,
        "current_stage": current_stage,
        "export_paths": export_paths,
        "updated_at": _utc_now(),
    }


# ============================================================
# WORKFLOW ROUTING
# ============================================================
def _route_after_approval(state: ResearchState) -> str:
    """Envía únicamente las aprobaciones a la entrega."""
    if state.get("approval_decision") == "approved":
        return "delivery"

    return "end"


def _route_after_delivery(state: ResearchState) -> str:
    """Finaliza según el resultado real de la entrega."""
    if state.get("delivery_status") == "completed":
        return "completed"

    if state.get("delivery_status") == "partial":
        return "partial"

    return "failed"


def build_workflow(
    *,
    checkpointer: Any = None,
) -> Any:
    """Construye el workflow completo de FitFamily.

    Flujo:
        Research
            |
        Analysis
            |
        Writing
            |
        Review
            |
        Approval (human interrupt)
            |
        Delivery
            |
        Completed / Partial / Failed
    """
    builder = StateGraph(ResearchState)

    # --------------------------------------------------------
    # REGISTER NODES
    # --------------------------------------------------------
    builder.add_node("research", research_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("writing", writing_node)
    builder.add_node("review", review_node)
    builder.add_node("approval", approval_node)
    builder.add_node("delivery", delivery_node)

    # --------------------------------------------------------
    # MAIN FLOW
    # --------------------------------------------------------
    builder.add_edge(START, "research")
    builder.add_edge("research", "analysis")
    builder.add_edge("analysis", "writing")
    builder.add_edge("writing", "review")

    # --------------------------------------------------------
    # REVIEW ROUTING
    # --------------------------------------------------------
    builder.add_conditional_edges(
        "review",
        lambda state: (
            "approval"
            if state.get("status") == "awaiting_approval"
            else "end"
        ),
        {
            "approval": "approval",
            "end": END,
        },
    )

    # --------------------------------------------------------
    # APPROVAL ROUTING
    # --------------------------------------------------------
    builder.add_conditional_edges(
        "approval",
        _route_after_approval,
        {
            "delivery": "delivery",
            "end": END,
        },
    )

    # --------------------------------------------------------
    # DELIVERY ROUTING
    # --------------------------------------------------------
    builder.add_conditional_edges(
        "delivery",
        _route_after_delivery,
        {
            "completed": END,
            "partial": END,
            "failed": END,
        },
    )

    return builder.compile(
        checkpointer=checkpointer,
    )


# ============================================================
# UTILITIES
# ============================================================
def _utc_now() -> str:
    """Devuelve la hora actual en UTC."""
    return datetime.now(timezone.utc).isoformat()


def _draft_to_dict(draft: ReportDraft) -> dict[str, Any]:
    """Convierte el borrador en un diccionario serializable."""
    return asdict(draft)


def _review_to_dict(review: Any) -> dict[str, Any]:
    """Convierte el resultado de revisión en un diccionario serializable."""
    return asdict(review)