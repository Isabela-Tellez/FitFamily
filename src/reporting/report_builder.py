"""
Funciones para construir y comprobar borradores de informes.
"""

from src.reporting.models import ReportDraft
from src.schemas import ResearchResult, ResearchBrief
from src.analysis.contracts import CalculatedMetric
from src.analysis.calculation_adapter import metric_context_notes
from src.reporting.calculated_claims import build_break_even_claim
from src.reporting.templates import MISSING_SECTION_TEXT


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
    calculated_metrics: list[CalculatedMetric] | None = None,
) -> ReportDraft:
    """Genera un borrador y añade puntos de equilibrio recibidos.

    Las frases numéricas se construyen desde las métricas,
    sin pedir al LLM que reproduzca o recalcule sus valores.
    """
    metrics = list(calculated_metrics or [])

    # Evitamos identificar dos resultados distintos con el mismo nombre.
    metric_ids = [metric.metric_id for metric in metrics]
    if len(metric_ids) != len(set(metric_ids)):
        raise ValueError("Hay identificadores de métricas duplicados.")

    if use_llm:
        from src.agents.strategic_writer import run_writing

        draft = run_writing(brief, research_result)
    else:
        from src.agents.writer_agent import WriterAgent

        draft = WriterAgent().create_draft(brief, research_result)

    numeric_texts: list[str] = []
    existing_claim_ids = {claim.claim_id for claim in draft.claims}

    for index, metric in enumerate(metrics, start=1):
        claim_id = f"calculated_break_even_{index}"

        if claim_id in existing_claim_ids:
            raise ValueError(
                f"El identificador de afirmación ya existe: {claim_id}"
            )

        # Esta primera integración solo admite puntos de equilibrio.
        # La función rechaza otros tipos o contextos incompletos.
        claim = build_break_even_claim(
            metric,
            claim_id=claim_id,
        )

        # Conservamos los supuestos y las limitaciones originales.
        for note in metric_context_notes(metric):
            if note not in draft.limitations:
                draft.limitations.append(note)

        if claim is None:
            # Un resultado ausente se explica, nunca se convierte en cero.
            message = (
                f"Resultado no disponible para {metric.metric_id}. "
                "No se presenta una cifra de punto de equilibrio."
            )
            numeric_texts.append(message)

            if message not in draft.limitations:
                draft.limitations.append(message)
            continue

        draft.claims.append(claim)
        existing_claim_ids.add(claim.claim_id)
        numeric_texts.append(claim.text)

    if numeric_texts:
        economic_title = "Escenarios económicos"
        calculated_text = (
            "Punto de equilibrio por escenario\n"
            + "\n\n".join(numeric_texts)
        )

        # Buscamos el apartado creado por el redactor.
        for index, section in enumerate(draft.sections):
            heading, _, body = section.strip().partition("\n")

            if heading.strip() != economic_title:
                continue

            # Retiramos únicamente el aviso genérico de apartado pendiente.
            # Conservamos cualquier otro contenido que ya exista.
            existing_body = body.strip()
            if existing_body == MISSING_SECTION_TEXT:
                existing_body = ""

            combined_body = "\n\n".join(
                text
                for text in (existing_body, calculated_text)
                if text
            )
            draft.sections[index] = (
                f"{economic_title}\n{combined_body}"
            )
            break
        else:
            # Compatibilidad con el redactor determinista, que todavía
            # no genera la estructura completa.
            draft.sections.append(
                f"{economic_title}\n{calculated_text}"
            )

    # Incluimos también las referencias de las afirmaciones nuevas.
    validate_report_references(draft, research_result)

    return draft


def build_report_markdown(
    brief: ResearchBrief,
    research_result: ResearchResult,
    *,
    use_llm: bool = False,
    calculated_metrics: list[CalculatedMetric] | None = None,
) -> str:
    """Genera el borrador con sus métricas y devuelve su Markdown.

    No escribe archivos ni concede aprobación.
    Para revisar y aprobar, el controlador debe conservar
    el ReportDraft obtenido mediante build_report().
    """
    from src.reporting.markdown_renderer import render_report_markdown

    draft = build_report(
        brief,
        research_result,
        use_llm=use_llm,
        calculated_metrics=calculated_metrics,
    )

    return render_report_markdown(draft)