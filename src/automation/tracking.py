import csv
import os
import tempfile
from dataclasses import asdict, fields


"""Seguimiento de entregas aprobadas de FitFamily."""

from pathlib import Path

from src.automation.exporter import (
    calculate_draft_fingerprint,
    validate_export_approval,
)
from src.automation.models import ApprovalRecord, TrackingRecord
from src.reporting.models import ReportDraft


def _published_path(
    path: str | Path | None,
    *,
    suffix: str,
    action: str,
    authorized_actions: tuple[str, ...],
) -> str:
    """Comprueba una ruta de entrega proporcionada por el controlador."""
    # Sin ruta todavía no hay un archivo publicado para este formato.
    if path is None:
        return ""

    if not str(path).strip():
        raise ValueError("La ruta del entregable está vacía.")

    # No registramos un formato que no estuviera autorizado.
    if action not in authorized_actions:
        raise ValueError(
            f"No está autorizada la acción {action}."
        )

    resolved = Path(path).resolve()

    if resolved.suffix.lower() != suffix:
        raise ValueError(
            f"El entregable debe tener extensión {suffix}."
        )

    if not resolved.is_file():
        raise ValueError(
            f"No existe el archivo entregable: {resolved}"
        )

    return str(resolved)


def build_tracking_record(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    *,
    markdown_path: str | Path | None = None,
    pdf_path: str | Path | None = None,
) -> TrackingRecord:
    """
    Prepara una fila de seguimiento sin escribir archivos.

    Las rutas deben ser los resultados devueltos por los exportadores.
    El controlador es responsable de conservar su relación con esta
    ejecución; comprobar que existen no demuestra su procedencia.
    """
    # Registrar el seguimiento requiere su propia autorización.
    validate_export_approval(
        draft,
        approval,
        run_id,
        "update_tracking_csv",
    )

    # El validador anterior rechaza None. Esta comprobación también
    # permite que el editor reconozca el tipo de approval desde aquí.
    if approval is None:
        raise ValueError("Falta la aprobación humana.")

    export_actions = {
        "export_markdown",
        "export_pdf",
    }.intersection(approval.actions)

    # El seguimiento describe una entrega de informes.
    # Debe haberse autorizado al menos uno de los dos formatos.
    if not export_actions:
        raise ValueError(
            "El seguimiento requiere autorizar al menos "
            "un formato de informe."
        )

    markdown = _published_path(
        markdown_path,
        suffix=".md",
        action="export_markdown",
        authorized_actions=approval.actions,
    )
    pdf = _published_path(
        pdf_path,
        suffix=".pdf",
        action="export_pdf",
        authorized_actions=approval.actions,
    )

    # Solo cuentan los formatos autorizados para esta entrega.
    # Por ejemplo, si se pidió únicamente Markdown, no exigimos PDF.
    completed_actions = set()
    if markdown:
        completed_actions.add("export_markdown")
    if pdf:
        completed_actions.add("export_pdf")

    status = (
        "complete"
        if export_actions.issubset(completed_actions)
        else "partial"
    )

    return TrackingRecord(
        run_id=run_id,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved_at=approval.decided_at.isoformat(),
        case=draft.title,
        study_area=draft.study_area,
        status=status,
        markdown_path=markdown,
        pdf_path=pdf,
    )

def _record_key(row: dict[str, str]) -> tuple[str, str, str]:
    """Identifica una entrega dentro del CSV de seguimiento."""
    return (
        row["run_id"],
        row["draft_id"],
        row["draft_version"],
    )


def _merge_tracking_row(
    previous: dict[str, str],
    current: dict[str, str],
    approval: ApprovalRecord,
) -> dict[str, str]:
    """Completa una entrega existente sin perder rutas anteriores."""
    # Estos datos deben permanecer iguales para una misma entrega.
    stable_fields = (
        "draft_fingerprint",
        "approved_at",
        "case",
        "study_area",
    )
    for name in stable_fields:
        if previous[name] != current[name]:
            raise ValueError(
                f"El seguimiento existente tiene otro valor para {name}."
            )

    merged = dict(current)

    for name in ("markdown_path", "pdf_path"):
        old_path = previous[name]
        new_path = current[name]

        # No sustituimos silenciosamente un entregable por otro.
        if old_path and new_path and old_path != new_path:
            raise ValueError(
                f"Ya existe otra ruta registrada en {name}."
            )

        # Un reintento puede proporcionar solo la acción recién lograda.
        merged[name] = new_path or old_path

    # Volvemos a comprobar los archivos conservados del registro anterior.
    merged["markdown_path"] = _published_path(
        merged["markdown_path"] or None,
        suffix=".md",
        action="export_markdown",
        authorized_actions=approval.actions,
    )
    merged["pdf_path"] = _published_path(
        merged["pdf_path"] or None,
        suffix=".pdf",
        action="export_pdf",
        authorized_actions=approval.actions,
    )

    expected = {
        "export_markdown",
        "export_pdf",
    }.intersection(approval.actions)

    completed = set()
    if merged["markdown_path"]:
        completed.add("export_markdown")
    if merged["pdf_path"]:
        completed.add("export_pdf")

    merged["status"] = (
        "complete" if expected.issubset(completed) else "partial"
    )
    return merged


def update_tracking_csv(
    draft: ReportDraft,
    approval: ApprovalRecord | None,
    run_id: str,
    csv_path: str | Path,
    *,
    markdown_path: str | Path | None = None,
    pdf_path: str | Path | None = None,
) -> Path:
    """
    Registra o completa una entrega aprobada sin duplicar su fila.

    csv_path lo configura el controlador. Las rutas de entregables
    deben proceder de export_markdown y export_pdf.
    """
    # Validamos antes de crear carpetas, bloqueos o archivos.
    record = build_tracking_record(
        draft,
        approval,
        run_id,
        markdown_path=markdown_path,
        pdf_path=pdf_path,
    )
    if approval is None:
        raise ValueError("Falta la aprobación humana.")

    target = Path(csv_path).resolve()
    if target.suffix.lower() != ".csv":
        raise ValueError("El seguimiento debe tener extensión .csv.")

    column_names = [item.name for item in fields(TrackingRecord)]
    current = {
        name: str(value)
        for name, value in asdict(record).items()
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(target.name + ".lock")

    # La creación exclusiva evita que dos llamadas de esta función
    # lean y actualicen simultáneamente el mismo CSV.
    # Si otra actualización está en marcha, el error se propaga.
    lock_descriptor = os.open(
        lock_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    temporary_path = None

    try:
        os.close(lock_descriptor)
        rows = []

        if target.exists():
            with target.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as existing:
                reader = csv.DictReader(existing, strict=True)

                # Rechazamos esquemas distintos para no perder columnas
                # ni reinterpretar un CSV que tenga otra finalidad.
                if reader.fieldnames != column_names:
                    raise ValueError(
                        "Las columnas del CSV no coinciden "
                        "con el esquema de seguimiento."
                    )

                seen = set()
                for row in reader:
                    if (
                        set(row) != set(column_names)
                        or any(value is None for value in row.values())
                    ):
                        raise ValueError(
                            "El CSV contiene una fila mal formada."
                        )

                    if any(
                        not row[name].strip()
                        for name in (
                            "run_id",
                            "draft_id",
                            "draft_version",
                        )
                    ):
                        raise ValueError(
                            "El CSV contiene una fila sin identificadores."
                        )

                    if row["status"] not in {"partial", "complete"}:
                        raise ValueError(
                            "El CSV contiene un estado desconocido."
                        )

                    key = _record_key(row)
                    if key in seen:
                        raise ValueError(
                            "El CSV contiene entregas duplicadas."
                        )

                    seen.add(key)
                    rows.append(row)

        current_key = _record_key(current)
        found = False

        for index, row in enumerate(rows):
            if _record_key(row) == current_key:
                merged = _merge_tracking_row(row, current, approval)

                # Si nada cambió, conservamos el archivo tal cual.
                if merged == row:
                    return target

                rows[index] = merged
                found = True
                break

        if not found:
            rows.append(current)

        # Escribimos una copia completa en la misma carpeta.
        # El CSV anterior permanece intacto si falla esta escritura.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=".tracking_",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            writer = csv.DictWriter(
                temporary,
                fieldnames=column_names,
            )
            writer.writeheader()
            writer.writerows(rows)
            temporary.flush()
            os.fsync(temporary.fileno())

        # Aquí sí reemplazamos el CSV: contiene todas las filas previas
        # más la entrega nueva o completada.
        os.replace(temporary_path, target)
        return target
    finally:
        # El bloqueo se elimina incluso si rechazamos el CSV
        # o se produce un error durante la actualización.
        try:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        finally:
            lock_path.unlink(missing_ok=True)