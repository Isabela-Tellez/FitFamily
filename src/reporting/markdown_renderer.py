from src.reporting.numeric_text import render_claim, render_section
"""
Presentación de borradores de FitFamily en formato Markdown.

Este módulo genera texto en memoria.
No escribe archivos ni ejecuta acciones de exportación.
"""

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
        clean_section = render_section(section, draft.claims).strip()
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

    if draft.limitations:
        for limitation in dict.fromkeys(draft.limitations):
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

        for claim in draft.claims:
            label = kind_labels.get(claim.kind, claim.kind)
            lines.extend([
                f"### {claim.claim_id}",
                "",
                f"**Tipo:** {label}",
                "",
                render_claim(claim),
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

            lines.append("")
    else:
        lines.append(
            "No se han registrado afirmaciones con referencias individuales."
        )

    return "\n".join(lines).rstrip() + "\n"