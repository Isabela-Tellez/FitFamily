"""Estado compartido de las investigaciones de FitFamily."""
from datetime import datetime, timezone
from operator import add
from typing import Annotated, Any, Literal, TypedDict

RunStatus = Literal[
    "running", "awaiting_approval", "completed", "rejected",
    "budget_exceeded", "insufficient_evidence", "failed",
]
ApprovalDecision = Literal["approved", "rejected"]


class ResearchState(TypedDict, total=False):
    """Estado compartido y recuperable de una investigación."""
    run_id: str
    brief: dict[str, Any]
    created_at: str
    updated_at: str
    research_result: Any
    analysis_result: Any
    report_draft: Any
    review_result: Any
    report_version_id: str | None
    approval_decision: ApprovalDecision | None
    approved_version_id: str | None
    status: RunStatus
    current_stage: str
    pending_tasks: list[str]
    writer_mode: Literal["deterministic", "llm"]
    events: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[dict[str, Any]], add]
    usage: dict[str, Any]
    budget: dict[str, Any]
    export_paths: list[str]
    stop_reason: str | None


def create_initial_state(run_id: str, brief: dict[str, Any]) -> ResearchState:
    """Crea el estado inicial con un identificador estable de ejecución."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id debe ser una cadena no vacía.")
    if not isinstance(brief, dict) or not brief:
        raise ValueError("brief debe ser un diccionario no vacío.")
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
        "writer_mode": "deterministic",
        "events": [],
        "errors": [],
        "usage": {
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
            "cost": 0.0, "estimated_cost": 0.0,
        },
        "budget": {},
        "export_paths": [],
        "stop_reason": None,
    }
