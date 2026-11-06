"""FitFamily Studio — punto de entrada de la interfaz alternativa.

Arranque:  python -m streamlit run src/ui/studio/app.py

Arquitectura de presentación separada de la lógica de negocio:
  design.py       → sistema de diseño (tokens + CSS)
  state.py        → estado de sesión y utilidades
  components.py   → componentes visuales reutilizables
  navigation.py   → router y sidebar
  services.py     → envoltorios del backend real (workflow, MCP, recomendación)
  screens/        → una pantalla por área de experiencia

La app no lanza búsquedas, consultas MCP ni exportaciones al cargarse:
cada operación externa requiere una acción explícita del usuario.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Raíz del proyecto en sys.path (mismo criterio que src/ui/app.py)
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from src.ui.studio import design, navigation
from src.ui.studio.screens import approval, indicators, new_study, results, workspace
from src.ui.studio.state import init

# ---------------------------------------------------------------------------
# Configuración e identidad (una sola vez)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FitFamily Studio · Inteligencia de mercado",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

design.inject()
init()

# ---------------------------------------------------------------------------
# Router: una pantalla activa por vez (sin bloques duplicados)
# ---------------------------------------------------------------------------
page = navigation.render_sidebar()

if page == "Inicio":
    workspace.render()
elif page == "Nuevo estudio":
    new_study.render()
elif page == "Resultados":
    results.render()
elif page == "Indicadores oficiales":
    indicators.render()
elif page == "Aprobación y entrega":
    approval.render()

from src.ui.studio.components import footer

footer()
