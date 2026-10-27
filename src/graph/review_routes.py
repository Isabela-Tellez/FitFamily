"""Decisiones de enrutamiento para la revisión de FitFamily."""

from typing import Literal

from src.analysis.contracts import CalculatedMetric
from src.reporting.models import ReportDraft
from src.review.models import ReviewResult
from src.review.quality_checks import (
    validate_review_matches_analysis,
    validate_review_matches_draft,
    validate_review_matches_research,
)
from src.schemas import ResearchResult

ReviewRoute = Literal[
    "revise_research",
    "revise_analysis",
    "revise_writing",
    "blocked",
    "pending_review",
]


def choose_review_route(
    review: ReviewResult,
    revision_count: int,
    max_revisions: int = 2,
) -> ReviewRoute:
    """
    Decide el siguiente paso a partir de las incidencias.

    revision_count:
        Número de rondas de corrección ya iniciadas.
        La revisión inicial comienza con 0.

    max_revisions:
        Máximo de rondas de corrección permitidas.

    No ejecuta agentes ni modifica el contador.
    """
    # Rechazamos contadores inválidos para no alterar los límites.
    for name, value in (
        ("revision_count", revision_count),
        ("max_revisions", max_revisions),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(
                f"{name} debe ser un entero mayor o igual que cero."
            )

    # Las advertencias no provocan por sí solas una corrección.
    errors = [
        issue
        for issue in review.issues
        if issue.severity == "error"
    ]

    # Pasar la revisión básica no implica aprobar todo el informe.
    if not errors:
        return "pending_review"

    # Hay errores, pero no queda margen para otra corrección.
    if revision_count >= max_revisions:
        return "blocked"

    stages = {issue.correction_stage for issue in errors}

    allowed_stages = {"research", "analysis", "writing"}

    if not stages.issubset(allowed_stages):
        raise ValueError("La revisión contiene una etapa desconocida.")

    # Priorizamos la etapa más temprana que necesita corrección.
    if "research" in stages:
        return "revise_research"

    if "analysis" in stages:
        return "revise_analysis"

    return "revise_writing"

def choose_review_route_for_draft(
    review: ReviewResult,
    draft: ReportDraft,
    revision_count: int,
    max_revisions: int = 2,
) -> ReviewRoute:
    """
    Comprueba la vigencia de la revisión antes de decidir la ruta.

    No ejecuta agentes ni concede aprobación humana.
    """
    validate_review_matches_draft(review, draft)

    return choose_review_route(
        review,
        revision_count=revision_count,
        max_revisions=max_revisions,
    )

def choose_review_route_for_context(
    review: ReviewResult,
    draft: ReportDraft,
    research_result: ResearchResult,
    revision_count: int,
    max_revisions: int = 2,
    *,
    calculated_metrics: list[CalculatedMetric] | None = None,
) -> ReviewRoute:
    """
    Comprueba investigación, análisis y borrador antes de decidir la ruta.

    Si algún contenido ha cambiado, es necesario revisar de nuevo.
    """
    validate_review_matches_research(review, research_result)
    validate_review_matches_analysis(review, calculated_metrics)

    return choose_review_route_for_draft(
        review,
        draft,
        revision_count=revision_count,
        max_revisions=max_revisions,
    )