
import streamlit as st


def render_brand():
    st.markdown(
        """
        <div class="brand">
            <h1>Fit<span>Family</span></h1>
            <p>GIMNASIO CON LUDOTECA</p>
            <small>EL CAÑAVERAL • MADRID</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        render_brand()
        st.divider()
        st.caption("Bienvenido a FitFamily")
        st.divider()

        st.page_link(
            "app.py",
            label="Dashboard",
            icon="🏠",
        )

        st.page_link(
            "pages/1_Nueva_investigacion.py",
            label="Nueva investigación",
            icon="🔎",
        )

        st.page_link(
            "pages/2_Workflow.py",
            label="Workflow",
            icon="⚙️",
        )

        st.page_link(
            "pages/3_Eventos.py",
            label="Eventos",
            icon="📡",
        )

        st.page_link(
            "pages/4_Informes.py",
            label="Informes",
            icon="📄",
        )

        st.page_link(
            "pages/5_Aprobacion.py",
            label="Aprobación",
            icon="✅",
        )

        st.page_link(
            "pages/6_Presupuesto.py",
            label="Presupuesto",
            icon="💰",
        )

        st.page_link(
            "pages/7_Configuracion.py",
            label="Configuración",
            icon="⚙️",
        )

        st.divider()
        st.caption("FitFamily · Madrid")
