"""Controlador sin dependencias de Streamlit para la UI de FitFamily.

Mantiene las reglas de identidad, vigencia de revisión y aprobación fuera de
la capa visual. Nunca crea datos de investigación ni huellas artificiales.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable

from src.analysis.contracts import CalculatedMetric
from src.automation.delivery import ACTION_ORDER
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord, DeliveryResult
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


def create_approval_record(
    *,
    run_id: str,
    draft: ReportDraft,
    research: ResearchResult,
    metrics: list[CalculatedMetric],
    review: ReviewResult,
    actions: Iterable[str] = (),
    approved: bool = True,
) -> ApprovalRecord:
    """Registra una decisión humana sobre la versión exacta que se mostró.

    Para una aprobación, errores de revisión bloquean la operación. Las
    advertencias se muestran, pero no se convierten artificialmente en errores.
    Un rechazo registra una decisión negativa sin autorizar entregas.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id debe ser una cadena no vacía.")
    validate_review_context(
        draft=draft, research=research, metrics=metrics, review=review
    )

    selected_input = tuple(actions)
    unknown = set(selected_input).difference(ACTION_ORDER)
    if unknown:
        raise ValueError(
            "Acciones de entrega desconocidas: " + ", ".join(sorted(unknown))
        )

    if approved:
        blocking = [issue for issue in review.issues if issue.severity == "error"]
        if blocking:
            raise ValueError(
                "La revisión contiene errores bloqueantes; corrígelos antes de aprobar."
            )
        selected = tuple(action for action in ACTION_ORDER if action in selected_input)
        if not selected:
            raise ValueError("Selecciona al menos una acción de entrega.")
        if "update_tracking_csv" in selected and not {
            "export_markdown", "export_pdf"
        }.intersection(selected):
            raise ValueError("El seguimiento CSV requiere autorizar Markdown o PDF.")
    else:
        selected = ()

    return ApprovalRecord(
        run_id=run_id,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved=approved,
        actions=selected,
        decided_at=datetime.now(timezone.utc),
    )


def delivery_to_state(result: DeliveryResult) -> dict[str, Any]:
    """Serializa DeliveryResult para mantenerlo en session_state/checkpoint."""
    return asdict(result)


def delivery_from_state(payload: dict[str, Any] | DeliveryResult | None) -> DeliveryResult | None:
    """Reconstruye un resultado de entrega para un reintento idempotente."""
    if payload is None or isinstance(payload, DeliveryResult):
        return payload
    data = dict(payload)
    for name in ("requested_actions", "completed_actions", "failed_actions"):
        data[name] = tuple(data.get(name, ()))
    data["errors"] = tuple(tuple(item) for item in data.get("errors", ()))
    return DeliveryResult(**data)
