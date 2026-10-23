"""
Funciones para construir y comprobar borradores de informes.
"""

from src.reporting.models import ReportDraft
from src.schemas import ResearchResult, ResearchBrief


def find_missing_evidence_ids(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> list[str]:
    """
    Devuelve los identificadores citados que no existen
    entre las evidencias de la investigación.

    No modifica el borrador ni consulta las fuentes.
    """
    # Reunimos los identificadores de las evidencias generales.
    available_ids = {
        evidence.evidence_id
        for evidence in research_result.evidences
    }

    # También admitimos evidencias incluidas en los competidores.
    for competitor in research_result.competitors:
        available_ids.update(
            evidence.evidence_id
            for evidence in competitor.evidences
        )

    # Un conjunto evita repetir una referencia ausente.
    missing_ids = {
        evidence_id
        for claim in draft.claims
        for evidence_id in claim.evidence_ids
        if evidence_id not in available_ids
    }

    return sorted(missing_ids)

def validate_report_references(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> None:
    """
    Rechaza un borrador si cita evidencias inexistentes.

    Comprueba la existencia de las referencias, no que respalden
    el contenido de las afirmaciones.
    """
    missing_ids = find_missing_evidence_ids(draft, research_result)

    if missing_ids:
        raise ValueError(
            "El borrador cita evidencias inexistentes: "
            + ", ".join(missing_ids)
        )


def build_report(
    brief: ResearchBrief,
    research_result: ResearchResult,
    *,
    use_llm: bool = False,
) -> ReportDraft:
    """
    Genera un borrador y comprueba sus referencias.

    Por defecto utiliza el Writer determinista.
    use_llm=True ejecuta el agente con el proveedor configurado.
    """
    if use_llm:
        from src.agents.strategic_writer import run_writing

        draft = run_writing(brief, research_result)
    else:
        from src.agents.writer_agent import WriterAgent

        draft = WriterAgent().create_draft(brief, research_result)

    validate_report_references(draft, research_result)

    return draft


def build_report_markdown(
    brief: ResearchBrief,
    research_result: ResearchResult,
    *,
    use_llm: bool = False,
) -> str:
    """
    Genera el borrador validado y devuelve su Markdown.

    No escribe archivos ni concede aprobación.
    """
    from src.reporting.markdown_renderer import render_report_markdown

    draft = build_report(
        brief,
        research_result,
        use_llm=use_llm,
    )

    return render_report_markdown(draft)