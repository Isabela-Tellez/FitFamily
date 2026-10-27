"""
Exportación controlada de informes de FitFamily.

Las funciones de este módulo las utilizará el controlador,
no el agente redactor como herramienta de libre uso.
"""
import os
import tempfile
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.reporting.models import ReportDraft
from src.automation.models import ApprovalRecord
from src.reporting.markdown_renderer import render_report_markdown


def calculate_draft_fingerprint(draft: ReportDraft) -> str:
    """
    Calcula la huella del borrador, incluidas sus cifras estructuradas.

    Si cambia una cifra, la revisión y la aprobación anteriores
    dejan de corresponder al contenido actual.
    """
    payload = asdict(draft)
    payload["_review_policy"] = "numeric-traceability-v2"

    # asdict incluye los campos numéricos de cada ReportClaim.
    serialized = json.dumps(
        payload,
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

    from src.reporting.numeric_text import validate_numeric_text
    problems = validate_numeric_text(draft)
    if problems:
        raise ValueError("Texto numérico sin control: " + "; ".join(i.message for i in problems))


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

    markdown = render_report_markdown(draft, approved=True)

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

    _write_markdown_atomically(target, markdown)

    return target

def _write_markdown_atomically(target: Path, markdown: str) -> None:
    """
    Publica un archivo completo sin sobrescribir uno existente.

    El temporal se crea en la misma carpeta para mantener
    ambos archivos en el mismo sistema de archivos.
    """
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".report_",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(markdown)
            temporary.flush()
            os.fsync(temporary.fileno())

        try:
            # Publica el contenido completo. Si el destino existe,
            # no lo sobrescribe.
            os.link(temporary_path, target)
        except FileExistsError:
            existing_content = target.read_text(encoding="utf-8")

            if existing_content != markdown:
                raise ValueError(
                    "Ya existe una exportación diferente para esta "
                    "ejecución y versión."
                )
    finally:
        # Limpiamos el temporal tanto si funciona como si falla.
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

def export_pdf(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    output_dir: str | Path,
) -> Path:
    """
    Exporta un PDF únicamente después de validar su aprobación.

    Repetir la operación devuelve el archivo existente si coincide.
    Nunca sobrescribe una exportación con contenido diferente.
    """
    # Comprobamos la autorización antes de generar el documento
    # o crear la carpeta de salida.
    validate_export_approval(
        draft,
        approval,
        run_id,
        "export_pdf",
    )

    # Importamos el generador cuando se solicita un PDF.
    from src.reporting.pdf_renderer import render_report_pdf

    pdf_content = render_report_pdf(draft, approved=True)

    # El controlador decide la carpeta; el redactor no la configura.
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)

    # Incluimos la acción para distinguir esta operación
    # de la exportación Markdown del mismo borrador.
    operation = json.dumps(
        {
            "run_id": run_id,
            "draft_id": draft.draft_id,
            "version": draft.version,
            "action": "export_pdf",
        },
        sort_keys=True,
    )
    operation_key = hashlib.sha256(
        operation.encode("utf-8")
    ).hexdigest()

    target = directory / f"report_{operation_key}.pdf"
    _write_pdf_atomically(target, pdf_content)

    return target


def _write_pdf_atomically(target: Path, content: bytes) -> None:
    """Publica el PDF completo sin sobrescribir archivos existentes."""
    temporary_path = None

    try:
        # Creamos el temporal en la misma carpeta del destino.
        # El modo binario es necesario porque un PDF contiene bytes.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=".report_",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        try:
            # Publicamos el archivo completo mediante un enlace duro,
            # igual que en la exportación Markdown.
            os.link(temporary_path, target)
        except FileExistsError:
            # Un reintento solo se acepta si el contenido coincide.
            if target.read_bytes() != content:
                raise ValueError(
                    "Ya existe una exportación diferente para esta "
                    "ejecución y versión."
                )
    finally:
        # Limpiamos el temporal tanto al terminar como ante un error.
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)