"""
Exportación controlada de informes de FitFamily.

Las funciones de este módulo las utilizará el controlador,
no el agente redactor como herramienta de libre uso.
"""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.reporting.models import ReportDraft
from src.automation.models import ApprovalRecord
from src.reporting.markdown_renderer import render_report_markdown


def calculate_draft_fingerprint(draft: ReportDraft) -> str:
    """
    Calcula una huella del contenido completo del borrador.

    Permite comprobar si el borrador sigue siendo el mismo
    que recibió la aprobación. No concede ninguna aprobación.
    """
    serialized = json.dumps(
        asdict(draft),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def validate_export_approval(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    action: str,
) -> None:
    """
    Comprueba que una acción está autorizada para este borrador.

    Lanza ValueError si la aprobación falta, es negativa
    o no corresponde a la ejecución y al contenido actuales.
    """
    allowed_actions = {
        "export_markdown",
        "export_pdf",
        "update_tracking_csv",
    }

    if not run_id.strip():
        raise ValueError("El identificador de ejecución está vacío.")

    if action not in allowed_actions:
        raise ValueError("Acción de exportación desconocida.")

    if approval is None:
        raise ValueError("Falta la aprobación humana.")

    if approval.approved is not True:
        raise ValueError("La entrega no está aprobada.")

    if approval.run_id != run_id:
        raise ValueError("La aprobación pertenece a otra ejecución.")

    if approval.draft_id != draft.draft_id:
        raise ValueError("La aprobación pertenece a otro borrador.")

    if approval.draft_version != draft.version:
        raise ValueError("La aprobación corresponde a otra versión.")

    current_fingerprint = calculate_draft_fingerprint(draft)

    if approval.draft_fingerprint != current_fingerprint:
        raise ValueError("El contenido cambió después de la aprobación.")

    if action not in approval.actions:
        raise ValueError("La acción solicitada no está autorizada.")

    if (
        approval.decided_at.tzinfo is None
        or approval.decided_at.utcoffset() is None
    ):
        raise ValueError("La fecha de aprobación debe incluir zona horaria.")

def export_markdown(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    output_dir: str | Path,
) -> Path:
    """
    Exporta el borrador aprobado a un archivo Markdown.

    Una repetición devuelve el archivo existente si su contenido
    coincide. Nunca sobrescribe un archivo con contenido diferente.
    """
    validate_export_approval(
        draft,
        approval,
        run_id,
        "export_markdown",
    )

    markdown = render_report_markdown(draft)

    # La carpeta de salida la configura el controlador,
    # no el agente ni el contenido del informe.
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)

    # Convertimos los identificadores en un nombre seguro.
    operation = json.dumps(
        {
            "run_id": run_id,
            "draft_id": draft.draft_id,
            "version": draft.version,
            "action": "export_markdown",
        },
        sort_keys=True,
    )
    operation_key = hashlib.sha256(
        operation.encode("utf-8")
    ).hexdigest()

    target = directory / f"report_{operation_key}.md"

    try:
        # El modo "x" crea un archivo nuevo y evita sobrescribir.
        with target.open("x", encoding="utf-8", newline="\n") as file:
            file.write(markdown)
    except FileExistsError:
        existing_content = target.read_text(encoding="utf-8")

        if existing_content != markdown:
            raise ValueError(
                "Ya existe una exportación diferente para esta "
                "ejecución y versión."
            )

    return target