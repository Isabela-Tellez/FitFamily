"""Pantalla: Recomendación determinista.

Presenta el resultado del modelo real sin mostrar códigos internos en
primer plano. Separa de forma explícita los datos verificados de los
supuestos del usuario y trata el punto de equilibrio como riesgo cuando
supera los clientes previstos.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from src.ui.studio import copy, services
from src.ui.studio.components import (
    empty_state,
    note,
    page_header,
    section_header,
)
from src.ui.studio.formatting import (
    format_datetime,
    format_euro,
    format_number,
    format_score,
    humanize,
    scenario_label,
)

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

_DIMENSIONS = [
    ("demand_indicators", "Demanda", 25),
    ("competition_registry", "Competencia", 15),
    ("economic_scenario", "Escenario económico", 35),
    ("offer_differentiation", "Diferenciación", 25),
]


def _recommendation_label(code: object) -> str:
    """Traduce un código interno a una etiqueta legible."""
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
        "No hay una explicación adicional para este estado. Consulta los detalles técnicos.",
    )


def _break_even(fixed: float, fee: float, variable: float) -> float | None:
    contribution = float(fee) - float(variable)
    if contribution <= 0 or float(fixed) <= 0:
        return None
    return float(fixed) / contribution


def _scenario_rows(inputs: dict, break_even: float | None) -> list[dict[str, str]]:
    rows = [
        {"Concepto": "Clientes previstos", "Valor": format_number(inputs.get("clients"))},
        {"Concepto": "Cuota mensual", "Valor": format_euro(inputs.get("fee"), decimals=2)},
        {"Concepto": "Costes fijos / mes", "Valor": format_euro(inputs.get("fixed"))},
        {"Concepto": "Coste variable / cliente", "Valor": format_euro(inputs.get("variable"), decimals=2)},
    ]
    if break_even is not None:
        rows.append(
            {
                "Concepto": "Punto de equilibrio",
                "Valor": f"{format_number(math.ceil(break_even))} clientes",
            }
        )
    return rows


def _render_score(result) -> None:
    score = getattr(result, "score_global", None)
    section_header("Puntuación global")
    st.metric(
        "Oportunidad",
        f"{format_score(score)} / 10",
        delta="No es probabilidad de éxito",
        delta_color="off",
        border=True,
        help="Promedio ponderado de demanda, competencia, escenario económico y diferenciación.",
    )
    if score is not None:
        st.progress(
            min(max(float(score), 0.0), 10.0) / 10.0,
            text=f"{format_score(score)} de 10",
        )
    st.caption(copy.TEXTS["recommendation.score_legend"])

    section_header("Desglose por dimensión")
    breakdown = getattr(result, "score_breakdown", {}) or {}
    for key, label, weight in _DIMENSIONS:
        value = breakdown.get(key)
        if value is None:
            st.progress(0.0, text=f"{label} · sin datos · peso {weight} %")
        else:
            st.progress(
                min(max(float(value), 0.0), 10.0) / 10.0,
                text=f"{label} · {format_score(value)}/10 · peso {weight} %",
            )


def _render_scenario(inputs: dict, break_even: float | None) -> None:
    section_header(
        copy.TEXTS["recommendation.assumptions_title"],
        copy.TEXTS["recommendation.assumptions_help"],
    )
    st.dataframe(
        pd.DataFrame(_scenario_rows(inputs, break_even)),
        hide_index=True,
        use_container_width=True,
    )
    expected = inputs.get("clients")
    if break_even is not None and expected is not None:
        needed = math.ceil(break_even)
        if needed > int(expected):
            st.warning(
                copy.t("recommendation.break_even_risk", break_even=needed, expected=int(expected))
            )
        else:
            st.success(
                copy.t("recommendation.break_even_ok", break_even=needed, expected=int(expected))
            )
        st.caption(copy.TEXTS["recommendation.break_even_note"])


def _source_label(item: object) -> str:
    """Quita rutas de archivo y conserva el nombre legible de la fuente."""
    text = humanize(item).strip()
    for separator in (" — ", " – ", " - "):
        if separator in text:
            left, right = text.rsplit(separator, 1)
            candidate = right.strip().lower()
            if any(marker in candidate for marker in ("/", "\\", ".json", ".csv", ".db", ".sqlite")):
                return left.strip()
    return text


def _render_double_check(result, inputs: dict) -> None:
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown(f"**{copy.TEXTS['recommendation.verified_title']}**")
            sources = [
                _source_label(item)
                for item in (getattr(result, "sources_used", []) or [])
                if "equilibrio" not in str(item).lower()
            ]
            if sources:
                for item in sources:
                    st.markdown(f"- {item}")
            else:
                st.caption("No hay datos verificados cargados para este escenario.")
    with right:
        with st.container(border=True):
            st.markdown(f"**{copy.TEXTS['recommendation.assumptions_box']}**")
            assumptions = [
                humanize(item)
                for item in (getattr(result, "assumptions_used", []) or [])
                if "=" not in str(item)
            ]
            if inputs:
                assumptions.append(
                    "Clientes previstos: "
                    f"{format_number(inputs.get('clients'))}; cuota: "
                    f"{format_euro(inputs.get('fee'), decimals=2)}; costes fijos: "
                    f"{format_euro(inputs.get('fixed'))}."
                )
            for item in assumptions:
                st.markdown(f"- {item}")
            if not assumptions:
                st.caption("No se registraron supuestos.")


def render() -> None:
    page_header(
        copy.TEXTS["recommendation.title"],
        copy.TEXTS["recommendation.subtitle"],
        eyebrow="DECISIÓN FUNDAMENTADA",
    )
    note(copy.TEXTS["recommendation.note"])
    st.write("")

    with st.form("ff_recommendation"):
        section_header(copy.TEXTS["recommendation.assumptions_title"])
        row_one = st.columns([1.2, 1, 1])
        with row_one[0]:
            scenario = st.selectbox(
                "Tipo de escenario",
                ["intermediate", "basic", "optimistic"],
                index=0,
                format_func=scenario_label,
                help="Define el nivel de demanda y precio que quieres evaluar.",
                key="ff_scenario",
            )
        with row_one[1]:
            clients = st.number_input(
                "Clientes previstos",
                min_value=0,
                value=150,
                help="Supuesto tuyo; no es una previsión observada.",
                key="ff_clients",
            )
        with row_one[2]:
            fee = st.number_input(
                "Cuota mensual (€)",
                min_value=0,
                value=40,
                help="Supuesto tuyo; no es una tarifa verificada.",
                key="ff_fee",
            )
        row_two = st.columns([1, 1, 1.2])
        with row_two[0]:
            fixed = st.number_input(
                "Costes fijos / mes (€)",
                min_value=0,
                value=8000,
                help="Supuesto tuyo.",
                key="ff_fixed_recommendation",
            )
        with row_two[1]:
            variable = st.number_input(
                "Coste variable / cliente (€)",
                min_value=0,
                value=10,
                help="Supuesto tuyo.",
                key="ff_variable_recommendation",
            )
        with row_two[2]:
            st.markdown('<div class="ff-form-action-spacer"></div>', unsafe_allow_html=True)
            submit = st.form_submit_button(
                copy.TEXTS["action.calculate_recommendation"],
                type="primary",
                use_container_width=True,
            )
        st.caption(copy.TEXTS["recommendation.assumptions_help"])

    if submit:
        st.session_state["ff_recommendation_inputs"] = {
            "scenario": scenario,
            "clients": int(clients),
            "fee": float(fee),
            "fixed": float(fixed),
            "variable": float(variable),
        }
        st.session_state.pop("ff_recommendation_result", None)
        with st.spinner("Evaluando la oportunidad con la evidencia disponible…"):
            result, error = services.recommend(
                scenario_type=scenario,
                expected_clients=int(clients),
                monthly_fee=float(fee),
                fixed_costs=float(fixed),
                variable_cost_per_client=float(variable),
            )
        if error:
            st.error(f"Recomendación no disponible: {humanize(error)}")
        else:
            st.session_state["ff_recommendation_result"] = result

    result = st.session_state.get("ff_recommendation_result")
    if result is None:
        if not submit:
            empty_state(
                "Sin evaluación todavía",
                "Introduce tus supuestos y pulsa «Calcular recomendación» "
                "para obtener una valoración trazable.",
            )
        return

    inputs = st.session_state.get("ff_recommendation_inputs") or {
        "scenario": scenario,
        "clients": int(clients),
        "fee": float(fee),
        "fixed": float(fixed),
        "variable": float(variable),
    }
    break_even = _break_even(inputs["fixed"], inputs["fee"], inputs["variable"])

    st.write("")
    code = getattr(result, "recommendation", "")
    label = _recommendation_label(code)
    if str(code or "").strip() == "promising_conditional":
        st.success(f"**{label}**")
    else:
        st.warning(f"**{label}**")
    st.write(_recommendation_explanation(result))

    _render_score(result)
    st.write("")
    _render_scenario(inputs, break_even)
    st.write("")
    _render_double_check(result, inputs)

    st.write("")
    missing = [humanize(item) for item in (getattr(result, "missing_evidence", []) or [])]
    section_header(copy.TEXTS["recommendation.missing_title"])
    if missing:
        for item in missing:
            st.markdown(f"- {item}")
    else:
        st.markdown("- No quedan datos obligatorios pendientes.")

    limitations = [humanize(item) for item in (getattr(result, "limitations", []) or [])]
    section_header(copy.TEXTS["recommendation.limitations_title"])
    if limitations:
        for item in limitations:
            st.markdown(f"- {item}")
    else:
        st.markdown("- Sin limitaciones adicionales documentadas.")

    favorable = [
        humanize(item)
        for item in (getattr(result, "factors_favorable", []) or [])
        if "equilibrio" not in str(item).lower()
    ]
    risks = [
        humanize(item)
        for item in (getattr(result, "factors_unfavorable", []) or [])
    ]

    section_header(copy.TEXTS["recommendation.factors_ok"])
    if favorable:
        for item in favorable:
            st.markdown(f"- {item}")
    else:
        st.markdown("- Ninguno verificado.")
    section_header(copy.TEXTS["recommendation.factors_risk"])
    if risks:
        for item in risks:
            st.markdown(f"- {item}")
    else:
        st.markdown("- Ninguno documentado.")

    evaluated = getattr(result, "evaluated_at", None)
    st.caption(
        f"Evaluado el {format_datetime(evaluated)} "
        "(hora de Madrid). Este modelo no garantiza rentabilidad."
    )

    with st.expander(copy.TEXTS["recommendation.technical"]):
        st.code(str(code or "—"), language="text")
        st.code(str(getattr(result, "model_version", "—")), language="text")
        st.code(str(getattr(result, "run_id", "—")), language="text")
        st.write(
            "Evaluado: "
            f"{evaluated.isoformat() if hasattr(evaluated, 'isoformat') else evaluated}"
        )


def result_status(result) -> str:
    """Estado legible del resultado."""
    status = str(getattr(result, "status", "") or "")
    return {
        "pending_review": "Requiere revisión",
        "approved": "Aprobado",
        "blocked": "Bloqueado",
    }.get(status, status or "No disponible")
