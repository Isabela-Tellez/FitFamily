
"""Controlador principal de ejecución de FitFamily."""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.types import Command

from src.automation.delivery import export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord, DeliveryResult
from src.graph.persistence import build_thread_config
from src.graph.state import ResearchState
from src.reporting.models import ReportClaim, ReportDraft


ALLOWED_ACTIONS = {
    "export_markdown",
    "export_pdf",
    "update_tracking_csv",
}


def start_run(
    graph: Any,
    initial_state: ResearchState,
    thread_id: str,
) -> Any:
    """Inicia una investigación o recupera su ejecución por hilo."""

    config = build_thread_config(thread_id)

    return graph.invoke(
        initial_state,
        config=config,
    )


def resume_approval(
    graph: Any,
    thread_id: str,
    decision: str,
    actions: list[str],
    output_dir: str | Path,
    csv_path: str | Path | None = None,
) -> DeliveryResult | None:
    """Reanuda la aprobación y entrega el informe si fue autorizado."""

    config = build_thread_config(thread_id)

    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError("No existe una investigación para este hilo.")

    if not snapshot.next:
        raise ValueError("La investigación no está esperando aprobación.")

    if "approval" not in snapshot.next:
        raise ValueError("El workflow no está esperando una aprobación.")

    if decision not in ("approved", "rejected"):
        raise ValueError("Decisión de aprobación inválida.")

    if not isinstance(actions, list):
        raise ValueError("Las acciones deben proporcionarse como lista.")

    if len(actions) != len(set(actions)):
        raise ValueError("No se permiten acciones duplicadas.")

    if any(action not in ALLOWED_ACTIONS for action in actions):
        raise ValueError("Se ha solicitado una acción desconocida.")

    if decision == "approved" and not actions:
        raise ValueError("Debes autorizar al menos una acción.")

    if decision == "rejected" and actions:
        raise ValueError("Un informe rechazado no puede exportarse.")

    report_version_id = snapshot.values.get("report_version_id")

    if not report_version_id:
        raise ValueError("No existe una versión válida del informe.")

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "report_version_id": report_version_id,
                "actions": actions,
            }
        ),
        config=config,
    )

    if decision == "rejected":
        return None

    if result.get("status") != "completed":
        raise ValueError("La aprobación no terminó correctamente.")

    draft = _restore_draft(result["report_draft"])

    fingerprint = calculate_draft_fingerprint(draft)

    approval = ApprovalRecord(
        run_id=result["run_id"],
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=fingerprint,
        approved=True,
        actions=tuple(actions),
        decided_at=datetime.now(timezone.utc),
    )

    # Conservamos el registro de autorización para futuros reintentos.
    graph.update_state(
        config,
        {
            "approval_record": _approval_to_dict(approval),
        },
    )

    delivery = export_approved_report(
        draft=draft,
        approval=approval,
        run_id=result["run_id"],
        output_dir=output_dir,
        csv_path=csv_path,
    )

    _save_delivery_result(graph, config, delivery)

    return delivery


def retry_delivery(
    graph: Any,
    thread_id: str,
    output_dir: str | Path,
    csv_path: str | Path | None = None,
) -> DeliveryResult:
    """Reintenta exclusivamente las acciones de entrega pendientes."""

    config = build_thread_config(thread_id)

    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError("No existe la investigación solicitada.")

    state = snapshot.values

    approval_data = state.get("approval_record")

    if not approval_data:
        raise ValueError("No existe una autorización de entrega.")

    approval = ApprovalRecord(
        **{
            **approval_data,
            "actions": tuple(approval_data["actions"]),
            "decided_at": datetime.fromisoformat(
                approval_data["decided_at"]
            ),
        }
    )

    if not approval.approved:
        raise ValueError("La entrega no está aprobada.")

    draft = _restore_draft(state["report_draft"])

    previous_data = state.get("delivery_result")

    previous = None

    if previous_data:
        previous = DeliveryResult(
            **{
                **previous_data,
                "requested_actions": tuple(
                    previous_data["requested_actions"]
                ),
                "completed_actions": tuple(
                    previous_data["completed_actions"]
                ),
                "failed_actions": tuple(
                    previous_data["failed_actions"]
                ),
                "errors": tuple(
                    tuple(error)
                    for error in previous_data["errors"]
                ),
            }
        )

    delivery = export_approved_report(
        draft=draft,
        approval=approval,
        run_id=approval.run_id,
        output_dir=output_dir,
        csv_path=csv_path,
        previous_result=previous,
    )

    _save_delivery_result(graph, config, delivery)

    return delivery


def _restore_draft(data: dict[str, Any]) -> ReportDraft:
    """Reconstruye el borrador y sus afirmaciones desde el checkpoint."""

    return ReportDraft(
        **{
            **data,
            "claims": [
                ReportClaim(**claim)
                for claim in data.get("claims", [])
            ],
        }
    )


def _approval_to_dict(
    approval: ApprovalRecord,
) -> dict[str, Any]:
    """Serializa el registro de aprobación."""

    data = asdict(approval)
    data["decided_at"] = approval.decided_at.isoformat()

    return data


def _save_delivery_result(
    graph: Any,
    config: dict[str, Any],
    delivery: DeliveryResult,
) -> None:
    """Persiste el resultado de la entrega en LangGraph."""

    if delivery.complete:
        status = "completed"
    elif delivery.completed_actions:
        status = "partial"
    else:
        status = "failed"

    graph.update_state(
        config,
        {
            "delivery_result": asdict(delivery),
            "delivery_status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
