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

from src.automation.models import DeliveryResult
from src.reporting.models import ReportClaim, ReportDraft
from src.review.persisted_context import (
    metrics_from_state, research_from_state, review_from_state, validate_review_context,
)


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


def delivery_from_state(payload: dict[str, Any] | DeliveryResult | None) -> DeliveryResult | None:
    """Reconstruye un resultado de entrega para un reintento idempotente."""
    if payload is None or isinstance(payload, DeliveryResult):
        return payload
    data = dict(payload)
    for name in ("requested_actions", "completed_actions", "failed_actions"):
        data[name] = tuple(data.get(name, ()))
    data["errors"] = tuple(tuple(item) for item in data.get("errors", ()))
    return DeliveryResult(**data)
