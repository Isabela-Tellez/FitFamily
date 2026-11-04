"""Navegación y barra lateral de FitFamily Studio.

Router basado en session_state: un solo punto de entrada para cambiar
de pantalla. La sidebar muestra identidad, navegación y estado real
del estudio en sesión (sin datos inventados).
"""
from __future__ import annotations

import streamlit as st

from src.ui.studio import design
from src.ui.studio.state import get_state

# Catálogo de pantallas en orden de navegación
PAGES = [
    "Inicio",
    "Nuevo estudio",
    "Resultados",
    "Indicadores oficiales",
    "Recomendación",
    "Aprobación y entrega",
]


def go(page: str) -> None:
    """Navega a una pantalla (usado por botones y callbacks).

    Se usa una clave pendiente para no modificar ``ff_page`` después de
    que el radio de la barra lateral ya se haya instanciado en el mismo
    run de Streamlit.
    """
    st.session_state["ff_pending_page"] = page


def render_sidebar() -> str:
    """Dibuja la sidebar y devuelve la página activa."""
    with st.sidebar:
        # Identidad del producto
        st.markdown(
            """
            <div style="padding-bottom:14px; border-bottom:1px solid var(--ff-border); margin-bottom:14px;">
              <div style="font-size:1.35rem; font-weight:800; letter-spacing:-0.04em; color:var(--ff-primary); line-height:1.15;">
                fit<span style="color:var(--ff-accent);">family</span>.
              </div>
              <div style="font-size:.66rem; letter-spacing:.16em; text-transform:uppercase; color:var(--ff-muted); font-weight:700; margin-top:3px;">
                Market Intelligence
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navegación principal
        page = st.radio(
            "Navegación",
            PAGES,
            key="ff_page",
            label_visibility="collapsed",
        )
        st.divider()

        # Estado real del estudio en sesión
        state = get_state()
        if state:
            st.markdown(
                '<span class="ff-badge ff-badge-ok">● Estudio en sesión</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"ID · {st.session_state.get('ff_run_id') or '—'}")
            st.caption(f"Estado · {state.get('status', '—')}")
        else:
            st.markdown(
                '<span class="ff-badge ff-badge-muted">○ Sin estudio activo</span>',
                unsafe_allow_html=True,
            )
        st.divider()
        st.caption(
            "Las búsquedas, consultas MCP y exportaciones solo se ejecutan "
            "al pulsar sus controles."
        )
    return page
