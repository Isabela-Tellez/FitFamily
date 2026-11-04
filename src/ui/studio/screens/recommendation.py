"""Pantalla: Recomendación determinista.

Ejecuta el modelo real de recomendación (`src.recommendation.service`)
sobre indicadores MCP, registro de competidores y escenarios
económicos. No inventa cifras: si faltan datos obligatorios, el propio
modelo lo indica. Los campos financieros son supuestos del usuario.
"""
from __future__ import annotations

import streamlit as st

from src.ui.studio import services
from src.ui.studio.components import (
    empty_state,
    note,
    page_header,
    render_metrics,
    section_header,
)
# Traducción de estados internos del modelo a etiquetas comprensibles.
# El código interno se conserva para trazabilidad/diagnóstico.
_RECOMMENDATION_LABELS = {
    "promising_conditional": "Oportunidad prometedora (condicionada)",
    "insufficient_evidence": "Evidencia insuficiente para emitir una recomendación concluyente",
    "review_needed": "Requiere revisión adicional",
}

_RECOMMENDATION_EXPLANATIONS = {
    "promising_conditional": (
        "Los indicadores verificados, el registro de competidores y el escenario "
        "económico son suficientes para plantear una oportunidad. Aun así, "
        "conviene confirmar la disposición a pagar y los servicios de los competidores."
    ),
    "insufficient_evidence": (
        "La información disponible todavía no permite formular una recomendación "
        "firme. Es necesario completar o contrastar los datos pendientes antes de "
        "tomar una decisión."
    ),
    "review_needed": (
        "Los datos son parciales: faltan supuestos o evidencia completa de "
        "competencia. No se debe declarar rentabilidad; conviene completar la "
        "validación antes de decidir."
    ),
}

def _recommendation_label(code: object) -> str:
    """Traduce un código interno a una etiqueta legible (fallback genérico)."""
    text = str(code or "").strip()
    if text in _RECOMMENDATION_LABELS:
        return _RECOMMENDATION_LABELS[text]
    if not text:
        return "Estado no disponible"
    return "Estado no reconocido"


def _recommendation_explanation(result) -> str:
    """Explicación legible: primero la del modelo, luego la traducción."""
    model_explanation = getattr(result, "explanation", None)
    if isinstance(model_explanation, str) and model_explanation.strip():
        return model_explanation.strip()
    code = getattr(result, "recommendation", "")
    return _RECOMMENDATION_EXPLANATIONS.get(
        str(code or "").strip(),
        "No hay explicación disponible para este estado. Conserva el código "
        "técnico para diagnóstico.",
    )


def render() -> None:
    page_header(
        "Recomendación de oportunidad",
        "Modelo determinista y explicable: usa indicadores MCP, el registro "
        "oficial de competidores y tus supuestos económicos. No garantiza "
        "rentabilidad ni rellena datos faltantes.",
        eyebrow="MODELO DETERMINISTA",
    )
    note(
        "Los campos financieros son <strong>supuestos del usuario</strong>, "
        "nunca observaciones de mercado. Si faltan datos obligatorios, el "
        "modelo lo declara en lugar de estimarlos."
    )
    st.write("")

    with st.form("ff_recommendation"):
        section_header("Supuestos del escenario")
        col_a, col_b = st.columns(2)
        with col_a:
            scenario = st.selectbox(
                "Tipo de escenario",
                ["intermediate", "basic", "optimistic"],
                index=0,
                help="Escenario económico sobre el que evaluar la oportunidad.",
            )
            clients = st.number_input(
                "Clientes previstos (supuesto)",
                min_value=0, value=150,
            )
        with col_b:
            fee = st.number_input(
                "Cuota mensual (€, supuesto)", min_value=0, value=40
            )
            fixed = st.number_input(
                "Costes fijos / mes (€, supuesto)", min_value=0, value=8000
            )
        variable = st.number_input(
            "Coste variable / cliente (€, supuesto)", min_value=0, value=10
        )
        submit = st.form_submit_button(
            "Ejecutar recomendación determinista",
            type="primary",
            use_container_width=True,
        )

    if submit:
        with st.spinner("Evaluando la oportunidad con datos reales…"):
            result, error = services.recommend(
                scenario_type=scenario,
                expected_clients=int(clients),
                monthly_fee=float(fee),
                fixed_costs=float(fixed),
                variable_cost_per_client=float(variable),
            )
        if error:
            st.error(f"Recomendación no disponible: {error}")
            st.caption(
                "Verifica los datos de entrada y la existencia de "
                "`data/processed/competitor_registry.json`."
            )
        else:
            st.session_state["ff_recommendation_result"] = result

    result = st.session_state.get("ff_recommendation_result")
    if result is None:
        if not submit:
            empty_state(
                "Sin evaluación todavía",
                "Introduce tus supuestos y pulsa «Ejecutar recomendación "
                "determinista» para obtener una valoración trazable.",
            )
        return

    st.write("")
    code = getattr(result, "recommendation", "")
    label = _recommendation_label(code)
    st.markdown(f"### {label}")
    st.caption(f"Código interno del modelo (trazabilidad): `{code or '—'}`")

    explanation = _recommendation_explanation(result)
    st.write(explanation)

    score = getattr(result, "score_global", None)
    render_metrics(
        [
            (
                "Puntuación global",
                f"{score:.1f}" if score is not None else "No disponible",
                "Puntuación compuesta (0-10), no probabilidad de éxito",
            ),
            ("Estado", str(result_status(result)), "Estado del modelo"),
            ("Versión del modelo", str(getattr(result, "model_version", "—")), "Trazabilidad"),
        ],
        columns=3,
    )
    st.caption(
        "La puntuación (0-10) es un promedio ponderado de 4 dimensiones: "
        "demanda (25%), registro de competidores (15%), escenario económico "
        "(35%) y diferenciación (25%). No es probabilidad de éxito, ni de "
        "rentabilidad, ni garantía de viabilidad."
    )
    st.write("")

    # Datos pendientes primero (lo más importante para actuar)
    missing = list(getattr(result, "missing_evidence", []) or [])
    if missing:
        section_header("Datos pendientes (no inventados)")
        for item in missing:
            st.markdown(f"- {item}")

    limitations = list(getattr(result, "limitations", []) or [])
    section_header("Limitaciones")
    if limitations:
        for item in limitations:
            st.markdown(f"- {item}")
    else:
        st.markdown("- Sin limitaciones adicionales documentadas.")

    section_header("Factores y riesgos")
    st.markdown(
        "- **Factores favorables (datos reales):** "
        + (", ".join(result.factors_favorable) or "Ninguno verificado.")
    )
    st.markdown(
        "- **Factores desfavorables / riesgos:** "
        + (", ".join(result.factors_unfavorable) or "Ninguno documentado.")
    )

    evaluated = getattr(result, "evaluated_at", None)
    st.caption(
        f"Evaluado: {evaluated.isoformat() if evaluated else '—'} · "
        "Este modelo no garantiza rentabilidad. Usa datos verificados y "
        "supuestos etiquetados como tales."
    )


def result_status(result) -> str:
    """Estado legible del resultado (sin inventar etiquetas)."""
    status = str(getattr(result, "status", "") or "")
    return {
        "pending_review": "Requiere revisión",
        "approved": "Aprobado",
        "blocked": "Bloqueado",
    }.get(status, status or "No disponible")
