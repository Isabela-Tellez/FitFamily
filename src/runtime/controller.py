"""Controlador principal de ejecución de FitFamily."""

from pathlib import Path
from typing import Any

from langgraph.types import Command

from src.automation.delivery import ACTION_ORDER
from src.automation.models import DeliveryResult
from src.graph.persistence import build_thread_config
from src.graph.state import ResearchState


ALLOWED_ACTIONS = set(ACTION_ORDER)


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
) -> DeliveryResult | None:
    """
    Reanuda una aprobación humana.

    LangGraph continúa el workflow y delivery_node ejecuta
    las exportaciones. El controlador únicamente recupera
    el resultado generado por el workflow.
    """

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
                "actions": actions,
            }
        ),
        config=config,
    )

    if decision == "rejected":
        return None

    # La entrega ya ha sido ejecutada por delivery_node.
    # Aquí solamente recuperamos su resultado.
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

    # Preparamos la configuración del reintento.
    update = {
        "status": "running",
        "delivery_output_dir": str(output_dir),
    }

    if csv_path is not None:
        update["delivery_csv_path"] = str(csv_path)

    # LangGraph aplica la actualización y ejecuta delivery_node.
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


def _restore_delivery_result(
    data: dict[str, Any],
) -> DeliveryResult:
    """Reconstruye el resultado de entrega desde el checkpoint."""

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
