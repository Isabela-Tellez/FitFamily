"""Pantalla: Inicio / Workspace.

Portada con una acción principal clara, estado real del estudio y
trabajos anteriores legibles. No muestra identificadores internos,
hashes ni eventos técnicos: solo tipo de negocio, zona, fecha en hora
de Madrid y estado en español.
"""
from __future__ import annotations

import streamlit as st

from src.ui.studio import copy, navigation, services
from src.ui.studio.components import (
    badge,
    empty_state,
    page_header,
    render_cards,
    render_mascot,
    section_header,
)
from src.ui.studio.formatting import (
    format_datetime,
    humanize,
    phase_kind,
    status_label,
    study_headline,
)
from src.ui.studio.state import get_state, redact_secrets


def _run_summary(run: dict) -> tuple[str, str, str, dict | None]:
    """Resumen legible de una ejecución guardada, sin datos internos."""
    stamp = run.get("timestamp")
    readable_date = format_datetime(stamp, fallback="fecha no disponible")
    try:
        state = services.load_study(str(run.get("run_id") or ""))
    except Exception:
        state = None

    if state:
        title = study_headline(state)
        raw = state.get("current_stage") or state.get("status")
        if title == "Estudio guardado":
            title = copy.t("home.previous_fallback", date=readable_date)
        phase = status_label(raw)
    else:
        title = copy.t("home.previous_fallback", date=readable_date)
        phase = "Interrumpido"
    return title, readable_date, phase, state


def _resume(run: dict, state: dict | None) -> None:
    if state is None:
        try:
            state = services.load_study(str(run.get("run_id") or ""))
        except Exception as exc:
            st.error(f"No se pudo recuperar el trabajo: {redact_secrets(exc)}")
            return
    if state is None:
        st.warning("Los datos de ese trabajo ya no están disponibles en el registro.")
        return
    st.session_state["ff_run_id"] = run.get("run_id")
    st.session_state["ff_state"] = state
    navigation.go("Resultados")
    st.rerun()


def _render_previous_runs() -> None:
    """Trabajos anteriores reales, presentados como una lista limpia."""
    try:
        runs = services.list_runs(limit=6)
    except Exception as exc:
        st.warning(f"No se pudo leer el registro de trabajos: {redact_secrets(exc)}")
        return

    if not runs:
        st.caption(copy.TEXTS["home.previous_empty"])
        return

    # Solo se listan los trabajos cuyos datos se pueden recuperar; los
    # interrumpidos o inaccesibles no aportan valor al usuario.
    recoverable = []
    for run in runs:
        _, _, _, state = _run_summary(run)
        if state is not None:
            recoverable.append(run)
    if not recoverable:
        st.caption(copy.TEXTS["home.previous_empty"])
        return

    for run in recoverable:
        title, readable_date, phase, state = _run_summary(run)
        key = str(run.get("run_id") or readable_date)
        with st.container(border=True):
            cols = st.columns([5, 3, 2], vertical_alignment="center")
            with cols[0]:
                st.markdown(f"**{title}**")
                st.caption(
                    f"Última actividad: {readable_date}"
                    if state
                    else "No se pudo recuperar el detalle de este trabajo."
                )
            with cols[1]:
                raw_kind = (
                    (state or {}).get("current_stage")
                    or (state or {}).get("status")
                    if state
                    else "blocked"
                )
                st.markdown(
                    badge(humanize(phase), phase_kind(raw_kind)),
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if st.button(
                    copy.TEXTS["action.resume"],
                    key=f"ff_resume_{key}",
                    use_container_width=True,
                    disabled=state is None,
                    help=(
                        "Este trabajo no tiene datos recuperables."
                        if state is None
                        else None
                    ),
                ):
                    _resume(run, state)


def render() -> None:
    left, right = st.columns([5, 4], gap="large", vertical_alignment="center")
    with left:
        page_header(
            copy.TEXTS["home.title"],
            copy.TEXTS["home.subtitle"],
            eyebrow="INTELIGENCIA DE MERCADO",
        )
        st.write("")
        c1, c2 = st.columns(2)
        if c1.button(
            copy.TEXTS["action.new_study"],
            type="primary",
            use_container_width=True,
            key="ff_home_new",
        ):
            navigation.go("Nuevo estudio")
            st.rerun()
        if c2.button(
            copy.TEXTS["action.view_indicators"],
            use_container_width=True,
            key="ff_home_indicators",
        ):
            navigation.go("Indicadores oficiales")
            st.rerun()
    with right:
        render_mascot()

    st.write("")
    state = get_state()
    if state:
        cols = st.columns([5, 2], vertical_alignment="center")
        with cols[0]:
            st.markdown(f"**{study_headline(state)}**")
            raw = state.get("current_stage") or state.get("status")
            st.markdown(
                badge(status_label(raw), phase_kind(raw)),
                unsafe_allow_html=True,
            )
        if cols[1].button(
            copy.TEXTS["action.view_results"],
            type="primary",
            use_container_width=True,
            key="ff_home_results",
        ):
            navigation.go("Resultados")
            st.rerun()
    else:
        empty_state(
            copy.TEXTS["home.empty_title"],
            copy.TEXTS["home.empty_body"],
        )

    st.write("")
    section_header(
        copy.TEXTS["home.previous_title"],
        copy.TEXTS["home.previous_subtitle"],
    )
    _render_previous_runs()

    st.write("")
    section_header(
        copy.TEXTS["home.purpose_title"],
        copy.TEXTS["home.purpose_subtitle"],
    )
    render_cards(
        [
            (
                copy.TEXTS["home.transparency_title"],
                copy.TEXTS["home.transparency_body"],
            ),
            (
                copy.TEXTS["home.control_title"],
                copy.TEXTS["home.control_body"],
            ),
        ],
        columns=2,
    )
    st.caption(
        "Herramienta genérica: configura tu propio negocio, zona y preguntas; "
        "la investigación y los indicadores se adaptan a cada encargo."
    )
