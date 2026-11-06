"""Barra lateral y navegación por pasos de FitFamily Studio.

La navegación es un menú de seis pasos con estado visible. Los pasos que
necesitan datos previos aparecen deshabilitados con una explicación
humana; nunca se ocultan, para que la persona sepa qué falta.

No se usa `st.radio`: los botones nativos son más accesibles por teclado
y permiten deshabilitar cada paso de forma individual.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from src.ui.studio import copy
from src.ui.studio.components import render_study_status
from src.ui.studio.formatting import has_report, has_study
from src.ui.studio.state import get_state


@dataclass(frozen=True)
class NavStep:
    page: str
    label: str
    needs: str = ""  # "", "study" o "report"


STEPS: tuple[NavStep, ...] = (
    NavStep("Inicio", copy.TEXTS["nav.inicio"]),
    NavStep("Nuevo estudio", copy.TEXTS["nav.nuevo_estudio"]),
    NavStep("Indicadores oficiales", copy.TEXTS["nav.indicadores"]),
    NavStep("Resultados", copy.TEXTS["nav.resultados"], "study"),
    NavStep("Recomendación", copy.TEXTS["nav.recomendacion"]),
    NavStep("Aprobación y entrega", copy.TEXTS["nav.aprobacion"], "report"),
)

PAGES = [step.page for step in STEPS]


def go(page: str) -> None:
    """Navega a una pantalla desde un botón o callback.

    Se usa una clave pendiente porque la navegación lateral se dibuja al
    principio del run; `app.py` la aplica antes de crear los botones.
    """
    st.session_state["ff_pending_page"] = page


def _is_available(step: NavStep, state: dict | None) -> bool:
    if step.needs == "study":
        return has_study(state)
    if step.needs == "report":
        return has_report(state)
    return True


def _is_completed(step: NavStep, state: dict | None) -> bool:
    if step.page == "Nuevo estudio":
        return has_study(state)
    if step.page == "Indicadores oficiales":
        return bool(st.session_state.get("ff_mcp"))
    if step.page == "Resultados":
        return has_study(state)
    if step.page == "Recomendación":
        return bool(st.session_state.get("ff_recommendation_result"))
    if step.page == "Aprobación y entrega":
        return bool(state and state.get("approval_record"))
    return False


def _nav_button(step: NavStep, index: int, current: str, state: dict | None) -> None:
    label = f"{index}  {step.label}"
    available = _is_available(step, state)
    if not available:
        help_text = (
            copy.TEXTS["nav.locked_help_report"]
            if step.needs == "report"
            else copy.TEXTS["nav.locked_help"]
        )
        st.button(
            label,
            key=f"ff_nav_locked_{step.page}",
            disabled=True,
            help=help_text,
            use_container_width=True,
        )
        return

    current_step = step.page == current
    done = _is_completed(step, state) and not current_step
    display = f"{label}  ✓" if done else label
    if st.button(
        display,
        key=f"ff_nav_{step.page}",
        type="primary" if current_step else "secondary",
        use_container_width=True,
    ):
        st.session_state["ff_page"] = step.page
        st.rerun()


def render_sidebar() -> str:
    """Dibuja la barra lateral y devuelve la página activa."""
    state = get_state()
    current = st.session_state.get("ff_page", "Inicio")
    if current not in PAGES:
        current = "Inicio"
        st.session_state["ff_page"] = current

    with st.sidebar:
        logo_path = Path(__file__).resolve().parents[3] / "assets" / "logo-fitfamily.png"
        if logo_path.is_file():
            st.image(str(logo_path), width=104)

        for index, step in enumerate(STEPS, start=1):
            _nav_button(step, index, current, state)

        st.divider()
        render_study_status(state)
    return current
