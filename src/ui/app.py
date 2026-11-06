"""FitFamily Studio — punto de entrada único de la interfaz Streamlit.

Arranque:  python -m streamlit run src/ui/app.py

Arquitectura de presentación separada de la lógica de negocio:

  app.py             → este punto de entrada (bootstrap + router)
  studio/styles.py   → único sistema de diseño (tokens + CSS)
  studio/copy.py     → único diccionario de textos y etiquetas
  studio/state.py    → estado de sesión y utilidades compartidas
  studio/formatting.py → fechas, números y estados en lenguaje humano
  studio/components.py → componentes visuales reutilizables
  studio/navigation.py → router y barra lateral
  studio/services.py → envoltorios del backend real (controlador, MCP)
  studio/screens/    → una pantalla por área de experiencia
  controller.py      → adaptador de presentación sobre el backend
  report_preview.py  → previsualización trazable del informe

La app no lanza búsquedas, consultas ni exportaciones al cargarse: cada
operación externa requiere una acción explícita del usuario.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from src.ui.studio import copy, design, navigation
from src.ui.studio.screens import (
    approval,
    indicators,
    new_study,
    recommendation,
    results,
    workspace,
)
from src.ui.studio.state import init

# ---------------------------------------------------------------------------
# Configuración e identidad (una sola vez por sesión)
# ---------------------------------------------------------------------------
_favicon = ROOT / "assets" / "logo-fitfamily.png"
st.set_page_config(
    page_title=copy.TEXTS["app.title"],
    page_icon=str(_favicon) if _favicon.is_file() else "🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

design.inject()
init()

# ---------------------------------------------------------------------------
# Router: una sola pantalla activa por vez (sin bloques duplicados)
# ---------------------------------------------------------------------------
pending_page = st.session_state.pop("ff_pending_page", None)
if pending_page:
    st.session_state["ff_page"] = pending_page

page = navigation.render_sidebar()

SCREENS = {
    "Inicio": workspace.render,
    "Nuevo estudio": new_study.render,
    "Indicadores oficiales": indicators.render,
    "Resultados": results.render,
    "Recomendación": recommendation.render,
    "Aprobación y entrega": approval.render,
}
SCREENS.get(page, workspace.render)()
