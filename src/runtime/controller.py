"""API pública única de ejecución de FitFamily."""

from pathlib import Path
from typing import Any

from langgraph.types import Command

from src.config import settings

from src.automation.delivery import ACTION_ORDER
from src.automation.models import DeliveryResult
from src.graph.persistence import (
    build_thread_config,
    load_run as _load_run,
)
from src.graph.state import ResearchState, create_initial_state
from src.runtime.events import emit_event


ALLOWED_ACTIONS = set(ACTION_ORDER)


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id debe ser una cadena no vacía.")


def _resolve_thread_id(
    run_id: str,
    thread_id: str | None = None,
) -> str:
    _validate_run_id(run_id)

    resolved = run_id if thread_id is None else thread_id

    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("thread_id debe ser una cadena no vacía.")

    return resolved


def _get_snapshot(
    graph: Any,
    run_id: str,
    thread_id: str | None = None,
) -> tuple[dict[str, Any], Any]:

    resolved = _resolve_thread_id(run_id, thread_id)
    config = build_thread_config(resolved)

    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError("No existe la investigación solicitada.")

    state = snapshot.values

    if state.get("run_id") != run_id:
        raise ValueError("El run_id no coincide con la investigación.")

    return config, snapshot


def start_run(
    graph: Any,
    run_id: str,
    brief: dict[str, Any],
    thread_id: str | None = None,
) -> Any:
    """Inicia una investigación o recupera una existente."""

    _validate_run_id(run_id)

    if not isinstance(brief, dict) or not brief:
        raise ValueError("brief debe ser un diccionario no vacío.")

    resolved = _resolve_thread_id(run_id, thread_id)
    config = build_thread_config(resolved)

    existing = graph.get_state(config)

    if existing.values:
        if existing.values.get("run_id") != run_id:
            raise ValueError("El identificador de ejecución no coincide.")

        if existing.values.get("brief") != brief:
            raise ValueError("El run_id ya pertenece a otro encargo.")

        return existing

    initial_state = create_initial_state(run_id, brief)

    emit_event(
        run_id=run_id,
        stage="workflow",
        event_type="run_started",
        message="Investigación iniciada.",
        details={
            "thread_id": resolved,
        },
        db_path=settings.events_db_path,
    )

    result = graph.invoke(
        initial_state,
        config=config,
    )

    if result.get("status") in (
        "completed",
        "rejected",
        "stopped_by_limit",
        "stopped_insufficient_evidence",
        "failed",
    ):
        emit_event(
            run_id=run_id,
            stage="workflow",
            event_type="run_completed",
            message="La investigación ha finalizado.",
            details={
                "status": result.get("status"),
            },
            db_path=settings.events_db_path,
        )

    return result


def load_run(
    graph: Any,
    run_id: str,
    thread_id: str | None = None,
) -> Any | None:
    """Recupera una investigación persistida."""

    resolved = _resolve_thread_id(run_id, thread_id)

    return _load_run(
        graph,
        resolved,
        expected_run_id=run_id,
    )


def resume_run(
    graph: Any,
    run_id: str,
    decision: dict[str, Any],
    thread_id: str | None = None,
) -> Any:
    """Reanuda una aprobación humana pendiente."""

    if not isinstance(decision, dict):
        raise ValueError(
            "La decisión debe ser un diccionario."
        )

    config, snapshot = _get_snapshot(
        graph,
        run_id,
        thread_id,
    )

    state = snapshot.values

    if state.get("status") != "awaiting_approval":
        raise ValueError(
            "La investigación no está esperando aprobación."
        )

    if "approval" not in snapshot.next:
        raise ValueError(
            "No existe una aprobación pendiente."
        )

    decision_value = decision.get("decision")

    if decision_value not in ("approved", "rejected"):
        raise ValueError(
            "La decisión de aprobación es inválida."
        )

    if (
        decision.get("report_version_id")
        != state.get("report_version_id")
    ):
        raise ValueError(
            "La decisión corresponde a otra versión."
        )

    actions = decision.get("actions", [])

    if not isinstance(actions, list):
        raise ValueError(
            "Las acciones deben proporcionarse como lista."
        )

    if any(
        not isinstance(action, str)
        for action in actions
    ):
        raise ValueError(
            "Todas las acciones deben ser cadenas."
        )

    if len(actions) != len(set(actions)):
        raise ValueError(
            "No se permiten acciones duplicadas."
        )

    if any(
        action not in ALLOWED_ACTIONS
        for action in actions
    ):
        raise ValueError(
            "Se ha solicitado una acción desconocida."
        )

    if decision_value == "approved" and not actions:
        raise ValueError(
            "Debes autorizar al menos una acción."
        )

    if decision_value == "rejected" and actions:
        raise ValueError(
            "Un informe rechazado no puede exportarse."
        )

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

    # Reanudamos el nodo interrumpido.
    # La validación definitiva y la creación del ApprovalRecord
    # siguen siendo responsabilidad de approval_node.
    result = graph.invoke(
        Command(
            resume={
                "decision": decision["decision"],
                **({"draft_fingerprint": decision["draft_fingerprint"]}
                   if "draft_fingerprint" in decision else {}),
                "report_version_id": decision["report_version_id"],
                "actions": actions,
            }
        ),
        config=config,
    )

    if decision_value == "rejected":
        return result

    delivery_data = result.get("delivery_result")

    if not isinstance(delivery_data, dict):
        raise ValueError(
            "El workflow no ha devuelto un resultado de entrega."
        )

    return _restore_delivery_result(delivery_data)


def retry_delivery(
    graph: Any,
    thread_id: str,
    output_dir: str | Path,
    csv_path: str | Path | None = None,
) -> DeliveryResult:
    """Reintenta la entrega delegando su ejecución en LangGraph."""

    config = build_thread_config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError(
            "No existe la investigación solicitada."
        )

    state = snapshot.values
    approval_data = state.get("approval_record")

    if not isinstance(approval_data, dict):
        raise ValueError(
            "No existe una autorización de entrega."
        )

    if not approval_data.get("approved"):
        raise ValueError(
            "La entrega no está aprobada."
        )

    update = {
        "status": "running",
        "delivery_output_dir": str(output_dir),
    }

    if csv_path is not None:
        update["delivery_csv_path"] = str(csv_path)

    result = graph.invoke(
        Command(
            update=update,
            goto="delivery",
        ),
        config=config,
    )

    delivery_data = result.get("delivery_result")

    if not isinstance(delivery_data, dict):
        raise ValueError(
            "El workflow no ha devuelto un resultado de entrega."
        )

    return _restore_delivery_result(delivery_data)



# Adaptadores temporales para mantener compatibilidad.

def resume_approval(
    graph: Any,
    thread_id: str,
    decision: str,
    actions: list[str],
    *,
    draft_fingerprint: str | None = None,
) -> DeliveryResult | None:
    """Reanuda una aprobación humana y recupera su entrega."""

    config = build_thread_config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError(
            "No existe una investigación para este hilo."
        )

    if not snapshot.next:
        raise ValueError(
            "La investigación no está esperando aprobación."
        )

    if "approval" not in snapshot.next:
        raise ValueError(
            "El workflow no está esperando una aprobación."
        )

    if decision not in ("approved", "rejected"):
        raise ValueError("Decisión de aprobación inválida.")

    if not isinstance(actions, list):
        raise ValueError(
            "Las acciones deben proporcionarse como lista."
        )

    if any(not isinstance(action, str) for action in actions):
        raise ValueError("Todas las acciones deben ser cadenas.")

    if len(actions) != len(set(actions)):
        raise ValueError(
            "No se permiten acciones duplicadas."
        )

    if any(action not in ALLOWED_ACTIONS for action in actions):
        raise ValueError(
            "Se ha solicitado una acción desconocida."
        )

    if decision == "approved" and not actions:
        raise ValueError(
            "Debes autorizar al menos una acción."
        )

    if decision == "rejected" and actions:
        raise ValueError(
            "Un informe rechazado no puede exportarse."
        )

    report_version_id = snapshot.values.get(
        "report_version_id"
    )

    if not report_version_id:
        raise ValueError(
            "No existe una versión válida del informe."
        )

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "report_version_id": report_version_id,
                "draft_fingerprint": draft_fingerprint,
                "actions": actions,
            }
        ),
        config=config,
    )

    if decision == "rejected":
        return None

    delivery_data = result.get("delivery_result")

    if not isinstance(delivery_data, dict):
        raise ValueError(
            "El workflow no ha devuelto un resultado de entrega."
        )

    return _restore_delivery_result(delivery_data)


def _restore_delivery_result(
    data: dict[str, Any],
) -> DeliveryResult:
    return DeliveryResult(
        **{
            **data,
            "requested_actions": tuple(data["requested_actions"]),
            "completed_actions": tuple(data["completed_actions"]),
            "failed_actions": tuple(data["failed_actions"]),
            "errors": tuple(
                tuple(error)
                for error in data.get("errors", [])
            ),
        }
    )
