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
from src.ui.studio.state import redact_secrets


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
    score = getattr(result, "score_global", None)
    render_metrics(
        [
            (
                "Puntuación global",
                f"{score:.1f}" if score is not None else "No disponible",
                "Escala 0-100 basada en datos reales",
            ),
            ("Estado", str(result_status(result)), "Estado del modelo"),
            ("Versión del modelo", str(getattr(result, "model_version", "—")), "Trazabilidad"),
        ],
        columns=3,
    )
    st.write("")

    st.markdown(f"### {getattr(result, 'recommendation', 'Resultado')}")
    explanation = getattr(result, "explanation", None)
    if explanation:
        st.write(explanation)
    else:
        st.caption(
            "Ver `docs/recommendation/RECOMMENDATION_MODEL.md` para la "
            "metodología completa."
        )

    section_header("Factores y limitaciones")
    st.markdown(
        "- **Factores favorables (datos reales):** "
        + (", ".join(result.factors_favorable) or "Ninguno verificado.")
    )
    st.markdown(
        "- **Factores desfavorables / riesgos:** "
        + (", ".join(result.factors_unfavorable) or "Ninguno documentado.")
    )
    st.markdown(
        "- **Datos faltantes (no inventados):** "
        + (", ".join(result.missing_evidence) or "Ninguno documentado.")
    )
    st.markdown(
        "- **Limitaciones:** "
        + ("; ".join(result.limitations) or "Sin limitaciones adicionales.")
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
