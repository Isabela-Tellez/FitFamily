import streamlit as st

from src.config import settings
from src.ui.styles import apply_styles
from src.ui.branding import render_brand
from src.ui.runtime import get_graph


st.set_page_config(
    page_title=settings.app_title,
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_styles()

# Inicializar backend una sola vez.
graph, _ = get_graph()

# Navegación real de FitFamily.
pages = {
    "Principal": [
        st.Page(
            "src/ui/pages/dashboard.py",
            title="Dashboard",
            icon="🏠",
            default=True,
        ),
        st.Page(
            "src/ui/pages/new_research.py",
            title="Nueva investigación",
            icon="🔎",
        ),
        st.Page(
            "src/ui/pages/research.py",
            title="Investigaciones",
            icon="📚",
        ),
    ],
    "Análisis": [
        st.Page(
            "src/ui/pages/analysis.py",
            title="Análisis económico",
            icon="📈",
        ),
        st.Page(
            "src/ui/pages/research_detail.py",
            title="Detalle de investigación",
            icon="📄",
        ),
    ],
    "Gestión": [
        st.Page(
            "src/ui/pages/approvals.py",
            title="Aprobaciones",
            icon="✅",
        ),
        st.Page(
            "src/ui/pages/exports.py",
            title="Configuración",
            icon="⚙️",
        ),
    ],
}

navigation = st.navigation(pages)

with st.sidebar:
    render_brand()
    st.divider()
    st.caption("GIMNASIO CON LUDOTECA")
    st.caption("EL CAÑAVERAL • MADRID")

navigation.run()
