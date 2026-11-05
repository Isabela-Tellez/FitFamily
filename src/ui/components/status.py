"""Componentes visuales para los estados de FitFamily."""

import streamlit as st


STATUS_CONFIG = {
    "running": ("En ejecución", "🟡"),
    "completed": ("Completada", "🟢"),
    "awaiting_approval": ("Pendiente de aprobación", "🔵"),
    "rejected": ("Rechazada", "🔴"),
    "failed": ("Fallida", "🔴"),
    "stopped_by_limit": ("Detenida por límite", "🟠"),
    "stopped_insufficient_evidence": (
        "Evidencia insuficiente",
        "🟠",
    ),
}


STAGE_LABELS = {
    "research": "Investigación",
    "analysis": "Análisis",
    "writing": "Redacción",
    "review": "Revisión",
    "approval": "Aprobación",
    "delivery": "Entrega",
    "completed": "Completada",
    "rejected": "Rechazada",
}


def get_status_label(status):
    """Devuelve el nombre legible de un estado."""
    return STATUS_CONFIG.get(
        status,
        (status or "Sin estado", "⚪"),
    )[0]


def get_stage_label(stage):
    """Devuelve el nombre legible de una etapa."""
    return STAGE_LABELS.get(
        stage,
        stage or "Sin etapa",
    )


def render_status(status):
    """Muestra un estado con su indicador visual."""
    label, emoji = STATUS_CONFIG.get(
        status,
        (status or "Sin estado", "⚪"),
    )

    st.markdown(
        f"**{emoji} {label}**"
    )
