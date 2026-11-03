"""DefiniciÃ³n y compilaciÃ³n del workflow de FitFamily."""

from pathlib import Path
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from src.config import settings

from functools import wraps
from langgraph.errors import GraphBubbleUp

from src.graph.state import ResearchState
from src.graph.nodes import (
    research_node,
    analysis_node,
    writing_node,
    review_node,
    approval_node,
    delivery_node,
)
from src.runtime.events import emit_event


# ============================================================
# TRANSICIONES REALES
# ============================================================

def _resolve_transition(
    stage: str,
    state: ResearchState,
    update: dict[str, Any],
) -> str:
    """Determina el destino a partir del estado actualizado."""

    merged = {**state, **update}

    if stage == "research":
        return "analysis"

    if stage == "analysis":
        return "writing"

    if stage == "writing":
        return "review"

    if stage == "review":
        return merged.get("review_route") or "blocked"

    if stage == "approval":
        if merged.get("approval_decision") == "approved":
            return "delivery"
        return "end"

    if stage == "delivery":
        status = merged.get("delivery_status")

        if status == "completed":
            return "completed"

        if status == "partial":
            return "partial"

        return "failed"

    return "unknown"


# ============================================================
# EVENTOS DEL WORKFLOW
# ============================================================

def _instrument_node(
    stage: str,
    node: Callable,
    db_path: str | Path | None = None,
) -> Callable:
    """Instrumenta un nodo y registra sus eventos reales."""

    resolved_db_path = (
        Path(db_path)
        if db_path is not None
        else settings.events_db_path
    )

    @wraps(node)
    def wrapped_node(state: ResearchState) -> dict[str, Any]:
        run_id = state.get("run_id")

        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError(
                "No se puede registrar un evento sin run_id."
            )

        emit_event(
            run_id=run_id,
            stage=stage,
            event_type="stage_started",
            message=f"Inicio de la etapa: {stage}",
            details={
                "current_stage": state.get("current_stage"),
            },
            db_path=resolved_db_path,
        )

        try:
            update = node(state)

            if not isinstance(update, dict):
                raise TypeError(
                    f"El nodo {stage!r} no devolviÃ³ un diccionario."
                )

        except GraphBubbleUp:
            # Las interrupciones de LangGraph no son fallos.
            emit_event(
                run_id=run_id,
                stage=stage,
                event_type="stage_interrupted",
                message=f"InterrupciÃ³n de la etapa: {stage}",
                details={
                    "current_stage": state.get("current_stage"),
                },
                db_path=resolved_db_path,
            )
            raise

        except Exception as exc:
            emit_event(
                run_id=run_id,
                stage=stage,
                event_type="stage_failed",
                message=f"Error en la etapa: {stage}",
                details={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                db_path=resolved_db_path,
            )
            raise

        emit_event(
            run_id=run_id,
            stage=stage,
            event_type="stage_completed",
            message=f"Etapa completada: {stage}",
            details={
                "current_stage": update.get(
                    "current_stage",
                    state.get("current_stage"),
                ),
            },
            db_path=resolved_db_path,
        )

        destination = _resolve_transition(
            stage,
            state,
            update,
        )

        emit_event(
            run_id=run_id,
            stage=stage,
            event_type="stage_transition",
            message=f"TransiciÃ³n prevista: {stage} -> {destination}",
            details={
                "from": stage,
                "to": destination,
            },
            db_path=resolved_db_path,
        )

        if stage == "approval":
            decision = update.get("approval_decision")

            if decision in ("approved", "rejected"):
                emit_event(
                    run_id=run_id,
                    stage=stage,
                    event_type=f"approval_{decision}",
                    message=(
                        "Informe aprobado."
                        if decision == "approved"
                        else "Informe rechazado."
                    ),
                    details={
                        "report_version_id": state.get(
                            "report_version_id"
                        ),
                        "actions": update.get(
                            "authorized_actions", []
                        ),
                    },
                    db_path=resolved_db_path,
                )

        if stage == "delivery":
            delivery_status = update.get(
                "delivery_status",
                state.get("delivery_status"),
            )

            if delivery_status in (
                "completed",
                "partial",
                "failed",
            ):
                emit_event(
                    run_id=run_id,
                    stage=stage,
                    event_type=f"delivery_{delivery_status}",
                    message=f"Estado de entrega: {delivery_status}",
                    details={
                        "delivery_status": delivery_status,
                        "export_paths": update.get(
                            "export_paths", []
                        ),
                    },
                    db_path=resolved_db_path,
                )

        if stage == "review" and destination == "blocked":
            emit_event(
                run_id=run_id,
                stage=stage,
                event_type="workflow_blocked",
                message=(
                    "Workflow bloqueado por el lÃ­mite de revisiÃ³n."
                ),
                details={
                    "correction_rounds": update.get(
                        "correction_rounds",
                        state.get("correction_rounds", 0),
                    ),
                    "stop_reason": update.get("stop_reason"),
                },
                db_path=resolved_db_path,
            )

        return update

    return wrapped_node


# ============================================================
# ROUTING
# ============================================================

def _route_after_approval(state: ResearchState) -> str:
    if state.get("approval_decision") == "approved":
        return "delivery"

    return "end"


def _route_after_delivery(state: ResearchState) -> str:
    status = state.get("delivery_status")

    if status == "completed":
        return "completed"

    if status == "partial":
        return "partial"

    return "failed"


def _route_after_review(state: ResearchState) -> str:
    return state.get("review_route") or "blocked"


# ============================================================
# WORKFLOW
# ============================================================

def build_workflow(
    *,
    checkpointer: Any = None,
    events_db_path: str | Path | None = None,
) -> Any:
    """Construye el workflow con registro persistente de eventos."""

    resolved_events_db_path = (
        Path(events_db_path)
        if events_db_path is not None
        else settings.events_db_path
    )

    builder = StateGraph(ResearchState)

    # Nodos instrumentados.
    builder.add_node(
        "research",
        _instrument_node(
            "research",
            research_node,
            resolved_events_db_path,
        ),
    )

    builder.add_node(
        "analysis",
        _instrument_node(
            "analysis",
            analysis_node,
            resolved_events_db_path,
        ),
    )

    builder.add_node(
        "writing",
        _instrument_node(
            "writing",
            writing_node,
            resolved_events_db_path,
        ),
    )

    builder.add_node(
        "review",
        _instrument_node(
            "review",
            review_node,
            resolved_events_db_path,
        ),
    )

    builder.add_node(
        "approval",
        _instrument_node(
            "approval",
            approval_node,
            resolved_events_db_path,
        ),
    )

    builder.add_node(
        "delivery",
        _instrument_node(
            "delivery",
            delivery_node,
            resolved_events_db_path,
        ),
    )

    # Flujo principal.
    builder.add_edge(START, "research")
    builder.add_edge("research", "analysis")
    builder.add_edge("analysis", "writing")
    builder.add_edge("writing", "review")

    # RevisiÃ³n y correcciones.
    builder.add_conditional_edges(
        "review",
        _route_after_review,
        {
            "revise_research": "research",
            "revise_analysis": "analysis",
            "revise_writing": "writing",
            "pending_review": "approval",
            "blocked": END,
        },
    )

    # AprobaciÃ³n humana.
    builder.add_conditional_edges(
        "approval",
        _route_after_approval,
        {
            "delivery": "delivery",
            "end": END,
        },
    )

    # Entrega.
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
