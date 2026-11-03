"""
Presentación de borradores de FitFamily en formato Markdown.

Este módulo genera texto en memoria.
No escribe archivos ni ejecuta acciones de exportación.
"""

from src.reporting.calculated_claims import ECONOMIC_TRACE_HEADERS, economic_trace_row, format_scenario_note
from src.reporting.models import ReportDraft


def render_report_markdown(
    draft: ReportDraft,
    *,
    approved: bool = False,
) -> str:
    """
    Convierte un borrador en un documento Markdown.

    Conserva las secciones, las fuentes, las limitaciones
    y el registro de afirmaciones con sus referencias.
    """

    status = (
        "aprobado para exportación."
        if approved
        else "borrador pendiente de revisión y aprobación."
    )

    lines = [
        f"# {draft.title}",
        "",
        f"**Zona de estudio:** {draft.study_area}",
        "",
        f"**Identificador del borrador:** {draft.draft_id}",
        "",
        f"**Versión:** {draft.version}",
        "",
        f"**Estado:** {status}",
    ]

    # El Writer actual guarda cada sección como un texto:
    # primera línea = título; líneas siguientes = contenido.
    for section in draft.sections:
        clean_section = section.strip()
        if not clean_section:
            continue

        heading, separator, body = clean_section.partition("\n")

        lines.extend(["", f"## {heading}"])

        if separator and body.strip():
            lines.extend(["", body.strip()])

    lines.extend(["", "## Fuentes", ""])

    if draft.sources:
        for source in dict.fromkeys(draft.sources):
            lines.append(f"- {source}")
    else:
        lines.append("No se han registrado fuentes.")

    lines.extend(["", "## Limitaciones", ""])

    limitations = [
        visible
        for note in dict.fromkeys(draft.limitations)
        if (visible := format_scenario_note(note)) is not None
    ]
    if limitations:
        for limitation in limitations:
            lines.append(f"- {limitation}")
    else:
        lines.append(
            "No se han registrado limitaciones. "
            "Esto no implica que el estudio carezca de ellas."
        )

    lines.extend(["", "## Registro de afirmaciones", ""])

    if draft.claims:
        kind_labels = {
            "fact": "Afirmación factual",
            "assumption": "Supuesto",
            "inference": "Inferencia",
        }

        economic_rows = []
        for claim in draft.claims:
            row = economic_trace_row(claim)
            if row is not None:
                economic_rows.append(row)
                continue
            label = kind_labels.get(claim.kind, claim.kind)
            lines.extend([
                f"### {claim.claim_id}",
                "",
                f"**Tipo:** {label}",
                "",
                claim.text,
                "",
            ])

            if claim.evidence_ids:
                references = ", ".join(
                    dict.fromkeys(claim.evidence_ids)
                )
                lines.append(f"**Evidencias:** {references}")
            else:
                lines.append(
                    "**Evidencias:** sin referencias registradas."
                )

            # Mostramos los campos numéricos sin recalcularlos.
            if claim.metric_id is not None:
                lines.extend([
                    "",
                    f"**Métrica:** {claim.metric_id}",
                    "",
                    f"**Valor declarado:** {claim.reported_value}",
                    "",
                    f"**Unidad:** {claim.reported_unit}",
                ])

            lines.append("")

            lines.append("")
        if economic_rows:
            lines.append("| " + " | ".join(ECONOMIC_TRACE_HEADERS) + " |")
            lines.append("| --- | --- | --- | --- |")
            for row in economic_rows:
                cells = [cell.replace("|", r"\|").replace("\n", "<br>") for cell in row]
                lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append(
            "No se han registrado afirmaciones con referencias individuales."
        )

    return "\n".join(lines).rstrip() + "\n"
