"""Pantalla: Inicio / Workspace.

Página de bienvenida con identidad, propósito, acceso destacado a la
acción principal y estado real del trabajo. No muestra actividad
reciente ni indicadores ficticios: los «trabajos anteriores» provienen
del registro de eventos del backend y se recuperan con `load_run`.
"""
from __future__ import annotations

import streamlit as st

from src.ui.studio import navigation, services
from src.ui.studio.components import (
    empty_state,
    page_header,
    render_cards,
    render_mascot,
    render_steps,
    section_header,
)
from src.ui.studio.state import get_state, redact_secrets


def _render_previous_runs() -> None:
    """Trabajos anteriores reales (registro de eventos del backend)."""
    try:
        runs = services.list_runs(limit=8)
    except Exception as exc:
        st.warning(f"No se pudo leer el registro de trabajos: {redact_secrets(exc)}")
        return

    if not runs:
        st.caption(
            "Aún no hay ejecuciones registradas en esta instalación. "
            "Los estudios que ejecutes aparecerán aquí con su último estado."
        )
        return

    for run in runs:
        cols = st.columns([4, 3, 2, 2])
        cols[0].code(run.get("run_id", "—"), language=None)
        cols[1].caption(f"{run.get('stage', '—')} · {run.get('event_type', '—')}")
        cols[2].caption(str(run.get("timestamp", ""))[:19].replace("T", " "))
        if cols[3].button(
            "Cargar", key=f"ff_load_{run.get('run_id')}", use_container_width=True
        ):
            try:
                state = services.load_study(run.get("run_id", ""))
            except Exception as exc:
                st.error(f"No se pudo recuperar el trabajo: {redact_secrets(exc)}")
                return
            if state is None:
                st.error("El checkpoint de ese trabajo ya no está disponible.")
                return
            st.session_state["ff_run_id"] = run.get("run_id")
            st.session_state["ff_state"] = state
            navigation.go("Resultados")
            st.rerun()


def render() -> None:
    page_header(
        "Decisiones de negocio, con los pies en los datos.",
        "Investiga tu mercado, identifica oportunidades y convierte información "
        "verificable en decisiones fundamentadas. Sin rellenar huecos. Sin cifras inventadas.",
        eyebrow="MARKET INTELLIGENCE PLATFORM",
    )

    # Identidad visual + acceso destacado a la acción principal
    left, right = st.columns([3, 2], gap="small")
    with left:
        c1, c2 = st.columns(2)
        if c1.button("🔎  Crear nuevo estudio", type="primary", use_container_width=True):
            navigation.go("Nuevo estudio")
            st.rerun()
        if c2.button("📊  Consultar indicadores oficiales", use_container_width=True):
            navigation.go("Indicadores oficiales")
            st.rerun()
        st.write("")
        state = get_state()
        if state:
            section_header(
                "Estudio en curso",
                f"Ejecución {st.session_state.get('ff_run_id') or '—'} · "
                f"estado {state.get('status', '—')}",
            )
            render_steps(state)
            if st.button("Ver resultados", type="primary"):
                navigation.go("Resultados")
                st.rerun()
        else:
            empty_state(
                "Aún no hay un estudio activo",
                "Empieza un nuevo estudio para investigar competidores, indicadores "
                "oficiales y escenarios económicos con trazabilidad completa.",
                action_label="Empezar un nuevo estudio",
            )
    with right:
        # Corrección de compatibilidad: st.iframe en lugar de
        # st.components.v1.html (deprecado desde Streamlit 1.56).
        render_mascot()

    st.write("")

    # Trabajos anteriores: datos reales del registro de eventos
    section_header(
        "Trabajos anteriores",
        "Ejecuciones registradas en esta instalación; se recuperan tal cual "
        "desde su checkpoint.",
    )
    _render_previous_runs()

    st.write("")

    # Propósito de la plataforma (información, no métricas inventadas)
    section_header(
        "Un solo espacio para investigar, interpretar y decidir",
        "FitFamily reúne fuentes web, indicadores municipales, escenarios "
        "económicos opcionales y revisión del informe en un flujo guiado.",
    )
    render_cards(
        [
            ("Transparencia", "Visible", "Cada dato ausente queda declarado como no disponible."),
            ("Control humano", "Explícito", "La publicación siempre espera tu decisión."),
            ("Trazabilidad", "Completa", "Cada cifra conserva su fuente y su cálculo."),
            ("Sin invenciones", "Garantizado", "Los supuestos del usuario se etiquetan como tales."),
        ],
        columns=4,
    )

    st.write("")
    section_header("Cómo funciona", "Cinco etapas, cada una con su control de calidad.")
    render_steps(None)
