"""
Estado compartido de las investigaciones de FitFamily.

Define los datos que LangGraph comparte entre los agentes y las etapas
del workflow, incluida la aprobación humana y la exportación.
"""

from datetime import datetime, timezone
from operator import add
from typing import Annotated, Any, Literal, TypedDict


# Estados posibles durante el ciclo de vida de una investigación.
RunStatus = Literal[
    "running",
    "awaiting_approval",
    "completed",
    "rejected",
    "budget_exceeded",
    "insufficient_evidence",
    "failed",
]

# Decisión de la persona responsable de aprobar el informe.
ApprovalDecision = Literal["approved", "rejected"]


class ResearchState(TypedDict, total=False):
    """Estado compartido y recuperable de una investigación."""

    # Identidad y encargo original.
    run_id: str
    brief: dict[str, Any]
    created_at: str
    updated_at: str

    # Resultados generados por los agentes.
    research_result: Any
    analysis_result: Any
    report_draft: Any
    review_result: Any

    # La aprobación debe quedar vinculada a una versión concreta.
    report_version_id: str | None
    approval_decision: ApprovalDecision | None
    approved_version_id: str | None

    # Control de la ejecución y tareas pendientes.
    status: RunStatus
    current_stage: str
    pending_tasks: list[str]

    # LangGraph concatena las listas gracias al reductor add.
    # Los nodos deben devolver solo los eventos y errores nuevos.
    events: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[dict[str, Any]], add]

    # Consumo acumulado y límites configurados para la ejecución.
    usage: dict[str, Any]
    budget: dict[str, Any]

    # Entregables generados y motivo de una posible interrupción.
    export_paths: list[str]
    stop_reason: str | None


def create_initial_state(
    run_id: str,
    brief: dict[str, Any],
) -> ResearchState:
    """
    Crea el estado inicial de una investigación.

    El run_id debe mantenerse al recuperar o reanudar la investigación.
    La persistencia del estado se gestiona por separado mediante LangGraph.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id debe ser una cadena no vacía.")

    if not isinstance(brief, dict) or not brief:
        raise ValueError("brief debe ser un diccionario no vacío.")

    # Usamos UTC para mantener marcas temporales consistentes.
    now = datetime.now(timezone.utc).isoformat()

    return {
        "run_id": run_id,
        "brief": brief,
        "created_at": now,
        "updated_at": now,
        "research_result": None,
        "analysis_result": None,
        "report_draft": None,
        "review_result": None,
        "report_version_id": None,
        "approval_decision": None,
        "approved_version_id": None,
        "status": "running",
        "current_stage": "research",
        "pending_tasks": [],
        "events": [],
        "errors": [],
        "usage": {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "estimated_cost": 0.0,
        },
        "budget": {},
        "export_paths": [],
        "stop_reason": None,
    }