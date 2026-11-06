"""Formato humano de datos para la interfaz.

Convierte fechas ISO a hora de Madrid, números al formato español y
estados internos del workflow a etiquetas comprensibles. Ninguna
pantalla debe mostrar ``awaiting_approval``, ``insufficient_evidence``
ni una marca temporal en UTC.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

try:  # Windows puede no traer la base de datos horaria.
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except Exception:  # pragma: no cover - respaldo conservador
    MADRID_TZ = timezone(timedelta(hours=1))


_STATUS_LABELS = {
    # Estados del workflow
    "research": "En investigación",
    "analysis": "En análisis",
    "writing": "En redacción",
    "review": "En revisión",
    "approval": "Pendiente de aprobación",
    "delivery": "Preparando la entrega",
    "completed": "Completado",
    "approved": "Aprobado",
    "rejected": "Rechazado",
    "blocked": "Interrumpido",
    "failed": "Interrumpido",
    "delivery_partial": "Entrega parcial",
    "delivery_failed": "Entrega fallida",
    "awaiting_approval": "Pendiente de aprobación",
    "pending_review": "Pendiente de revisión",
    "pending": "Pendiente",
    "running": "En curso",
    "unknown": "Estado no disponible",
    "": "Estado no disponible",
}

_PHASE_KINDS = {
    "completed": "ok",
    "approved": "ok",
    "awaiting_approval": "warn",
    "approval": "warn",
    "review": "info",
    "analysis": "info",
    "writing": "info",
    "research": "info",
    "delivery": "info",
    "delivery_partial": "warn",
    "delivery_failed": "danger",
    "failed": "danger",
    "blocked": "danger",
    "rejected": "danger",
}

_ISO_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}(?::\d{2})?)"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)

_SCENARIO_LABELS = {
    "basic": "Básico",
    "intermediate": "Intermedio",
    "optimistic": "Premium",
}


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=MADRID_TZ)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def format_datetime(value: Any, fallback: str = "No disponible") -> str:
    """Devuelve ``dd/mm/aaaa HH:mm`` en hora de Madrid."""
    moment = _coerce_datetime(value)
    if moment is None:
        return fallback
    return moment.astimezone(MADRID_TZ).strftime("%d/%m/%Y %H:%M")


def format_date(value: Any, fallback: str = "No disponible") -> str:
    moment = _coerce_datetime(value)
    if moment is None:
        return fallback
    return moment.astimezone(MADRID_TZ).strftime("%d/%m/%Y")


def format_time(value: Any, fallback: str = "No disponible") -> str:
    moment = _coerce_datetime(value)
    if moment is None:
        return fallback
    return moment.astimezone(MADRID_TZ).strftime("%H:%M")


def format_number(value: Any, decimals: int = 0, fallback: str = "No disponible") -> str:
    if value is None:
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_euro(value: Any, decimals: int = 0, fallback: str = "No disponible") -> str:
    text = format_number(value, decimals=decimals, fallback=fallback)
    return text if text == fallback else f"{text} €"


def format_score(value: Any, fallback: str = "No disponible") -> str:
    if value is None:
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return f"{number:.1f}".replace(".", ",")


def format_percent(value: Any, fallback: str = "No disponible") -> str:
    number = format_score(value, fallback=fallback)
    return number if number == fallback else f"{number} %"


def status_label(value: Any) -> str:
    """Traduce un estado interno del workflow a lenguaje natural."""
    key = str(value or "").strip().lower()
    return _STATUS_LABELS.get(key, "Estado no disponible")


def phase_kind(value: Any) -> str:
    key = str(value or "").strip().lower()
    return _PHASE_KINDS.get(key, "muted")


def scenario_label(value: Any) -> str:
    key = str(value or "").strip().lower()
    return _SCENARIO_LABELS.get(key, "Escenario no disponible")


def study_headline(state: dict[str, Any] | None) -> str:
    """Describe el estudio activo sin identificadores internos."""
    if not state:
        return ""
    brief = state.get("brief")
    if not isinstance(brief, dict):
        brief = {}
    business = str(brief.get("business_type") or "").strip()
    area = str(brief.get("study_area") or brief.get("location") or "").strip()
    if business and area:
        return f"{business[0].upper() + business[1:]} · {area}"
    if business:
        return business[0].upper() + business[1:]
    if area:
        return area
    return "Estudio guardado"


def has_study(state: dict[str, Any] | None) -> bool:
    return isinstance(state, dict) and bool(state)


def has_report(state: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(state, dict)
        and state.get("report_draft")
        and state.get("review_result")
    )


def humanize(text: Any) -> str:
    """Sustituye términos internos por lenguaje de producto.

    Se usa en textos que vienen del backend (mensajes, limitaciones o
    factores). Los códigos completos solo se conservan en el expander de
    detalles técnicos.
    """
    result = str(text or "")
    result = re.sub(
        r"Indicadores\s+MCP",
        "Indicadores oficiales",
        result,
        flags=re.IGNORECASE,
    )
    replacements = {
        "GROQ_API_KEY": "clave de redacción",
        "TAVILY_API_KEY": "clave de búsqueda",
        "LANGSMITH_API_KEY": "clave de trazabilidad",
        "insufficient_evidence": "evidencia insuficiente",
        "promising_conditional": "oportunidad condicionada",
        "review_needed": "requiere revisión",
        "run_started": "estudio iniciado",
        "stage_interrupted": "etapa interrumpida",
        "intermediate": "Intermedio",
        "optimistic": "Premium",
        "basic": "Básico",
        "MCP": "indicadores oficiales",
        "checkpoint": "registro guardado",
        "workflow": "estudio",
    }
    for old, new in replacements.items():
        result = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])", new, result)
    return _ISO_RE.sub(lambda m: _display_iso(m.group(0)), result)


def _display_iso(value: str) -> str:
    moment = _coerce_datetime(value)
    return format_datetime(moment, fallback=value)
