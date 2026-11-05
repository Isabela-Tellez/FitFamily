"""Controlador sin dependencias de Streamlit para la UI de FitFamily.

Mantiene las reglas de identidad, vigencia de revisión y reconstrucción
de objetos fuera de la capa visual. Nunca crea datos de investigación
ni huellas artificiales.

La decisión de aprobación y la entrega NO se implementan aquí: pasan
por el workflow real (`approval_node` / `delivery_node`) a través de
`src.runtime.controller`.
"""
from __future__ import annotations

from typing import Any

from src.analysis.contracts import CalculatedMetric
from src.automation.models import DeliveryResult
from src.reporting.models import ReportClaim, ReportDraft
from src.review.models import ReviewIssue, ReviewResult
from src.review.quality_checks import (
    validate_review_matches_analysis,
    validate_review_matches_draft,
    validate_review_matches_research,
)
from src.schemas import ResearchResult


def draft_from_state(payload: dict[str, Any] | ReportDraft) -> ReportDraft:
    """Reconstruye el dataclass ReportDraft serializado por LangGraph."""
    if isinstance(payload, ReportDraft):
        return payload
    if not isinstance(payload, dict):
        raise TypeError("El estado no contiene un borrador válido.")
    data = dict(payload)
    data["claims"] = [
        claim if isinstance(claim, ReportClaim) else ReportClaim(**claim)
        for claim in data.get("claims", [])
    ]
    return ReportDraft(**data)


def review_from_state(payload: dict[str, Any] | ReviewResult) -> ReviewResult:
    """Reconstruye ReviewResult y sus incidencias tipadas."""
    if isinstance(payload, ReviewResult):
        return payload
    if not isinstance(payload, dict):
        raise TypeError("El estado no contiene una revisión válida.")
    data = dict(payload)
    data["issues"] = tuple(
        issue if isinstance(issue, ReviewIssue) else ReviewIssue(**issue)
        for issue in data.get("issues", [])
    )
    data["checks_performed"] = tuple(data.get("checks_performed", ()))
    return ReviewResult(**data)


def research_from_state(payload: dict[str, Any] | ResearchResult) -> ResearchResult:
    """Valida y reconstruye la investigación serializada."""
    return payload if isinstance(payload, ResearchResult) else ResearchResult.model_validate(payload)


def metrics_from_state(payload: dict[str, Any] | None) -> list[CalculatedMetric]:
    """Reconstruye solo las métricas que realmente produjo el analista."""
    analysis = payload or {}
    return [
        item if isinstance(item, CalculatedMetric) else CalculatedMetric.model_validate(item)
        for item in analysis.get("calculated_metrics", [])
    ]


def validate_review_context(
    *,
    draft: ReportDraft,
    research: ResearchResult,
    metrics: list[CalculatedMetric],
    review: ReviewResult,
) -> None:
    """Comprueba que la revisión sigue perteneciendo a todo el contenido actual."""
    validate_review_matches_draft(review, draft)
    validate_review_matches_research(review, research)
    validate_review_matches_analysis(review, metrics)


def delivery_from_state(payload: dict[str, Any] | DeliveryResult | None) -> DeliveryResult | None:
    """Reconstruye un resultado de entrega para un reintento idempotente."""
    if payload is None or isinstance(payload, DeliveryResult):
        return payload
    data = dict(payload)
    for name in ("requested_actions", "completed_actions", "failed_actions"):
        data[name] = tuple(data.get(name, ()))
    data["errors"] = tuple(tuple(item) for item in data.get("errors", ()))
    return DeliveryResult(**data)
