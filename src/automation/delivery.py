"""Coordinación de entregas aprobadas de FitFamily."""

from pathlib import Path

from src.automation.exporter import (
    calculate_draft_fingerprint,
    export_markdown,
    export_pdf,
    validate_export_approval,
)
from src.automation.models import ApprovalRecord, DeliveryResult
from src.automation.tracking import update_tracking_csv
from src.reporting.models import ReportDraft


# El orden es estable: primero los informes y después el seguimiento.
ACTION_ORDER = (
    "export_markdown",
    "export_pdf",
    "update_tracking_csv",
)


def export_approved_report(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    output_dir: str | Path,
    *,
    csv_path: str | Path | None = None,
    previous_result: DeliveryResult | None = None,
) -> DeliveryResult:
    """
    Ejecuta las acciones autorizadas y conserva los éxitos parciales.

    previous_result debe ser un resultado conservado por el controlador,
    no un objeto creado por el LLM ni por contenido externo.
    """
    if approval is None:
        raise ValueError("Falta la aprobación humana.")

    if not approval.actions:
        raise ValueError("No hay acciones autorizadas para la entrega.")

    # Rechazamos toda la configuración antes de escribir archivos.
    # Cada acción debe estar autorizada para el contenido actual.
    for action in approval.actions:
        validate_export_approval(draft, approval, run_id, action)

    requested = tuple(
        action for action in ACTION_ORDER
        if action in approval.actions
    )

    if "update_tracking_csv" in requested:
        if csv_path is None or not str(csv_path).strip():
            raise ValueError("Falta configurar la ruta del CSV.")

        if Path(csv_path).suffix.lower() != ".csv":
            raise ValueError("El seguimiento debe tener extensión .csv.")

        if not {"export_markdown", "export_pdf"}.intersection(requested):
            raise ValueError(
                "El seguimiento requiere al menos un formato de informe."
            )

    fingerprint = calculate_draft_fingerprint(draft)
    completed = set()
    paths = {
        "markdown_path": "",
        "pdf_path": "",
        "tracking_path": "",
    }
    errors = []

    if previous_result is not None:
        # Nunca reutilizamos resultados de otra ejecución o contenido.
        if (
            previous_result.run_id != run_id
            or previous_result.draft_id != draft.draft_id
            or previous_result.draft_version != draft.version
            or previous_result.draft_fingerprint != fingerprint
            or previous_result.requested_actions != requested
        ):
            raise ValueError(
                "El resultado anterior no corresponde a esta entrega."
            )

        # Si un informe ya se publicó y sigue existiendo, conservamos
        # su ruta. Si desapareció, intentaremos generarlo de nuevo.
        for action, field_name in (
            ("export_markdown", "markdown_path"),
            ("export_pdf", "pdf_path"),
        ):
            path = getattr(previous_result, field_name)
            if (
                action in previous_result.completed_actions
                and action in requested
                and path
                and Path(path).is_file()
            ):
                completed.add(action)
                paths[field_name] = path

    # Cada formato se intenta por separado: un fallo de PDF no impide
    # conservar el Markdown ni registrar el resultado parcial.
    for action, exporter, field_name in (
        ("export_markdown", export_markdown, "markdown_path"),
        ("export_pdf", export_pdf, "pdf_path"),
    ):
        if action not in requested or action in completed:
            continue

        try:
            published = exporter(draft, approval, run_id, output_dir)
            paths[field_name] = str(published)
            completed.add(action)
        except (OSError, ValueError, RuntimeError) as error:
            errors.append((action, str(error)))

    if "update_tracking_csv" in requested:
        try:
            # Volvemos a actualizar el seguimiento en cada intento:
            # puede pasar de parcial a completo al obtener el PDF.
            published = update_tracking_csv(
                draft,
                approval,
                run_id,
                csv_path,
                markdown_path=paths["markdown_path"] or None,
                pdf_path=paths["pdf_path"] or None,
            )
            paths["tracking_path"] = str(published)
            completed.add("update_tracking_csv")
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(("update_tracking_csv", str(error)))

    # Una acción solo aparece completada si terminó correctamente
    # en este intento o conservamos su informe del intento anterior.
    return DeliveryResult(
        run_id=run_id,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=fingerprint,
        requested_actions=requested,
        completed_actions=tuple(
            action for action in requested if action in completed
        ),
        failed_actions=tuple(
            action for action in requested if action not in completed
        ),
        markdown_path=paths["markdown_path"],
        pdf_path=paths["pdf_path"],
        tracking_path=paths["tracking_path"],
        errors=tuple(errors),
    )