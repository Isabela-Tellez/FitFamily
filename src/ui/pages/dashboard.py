
import html
import pandas as pd
import streamlit as st

from src.ui.runtime import get_all_researches


def get_value(research, key, default=""):
    if isinstance(research, dict):
        return research.get(key, default)
    return getattr(research, key, default)


def display_status(status):
    labels = {
        "running": "En ejecución",
        "completed": "Completada",
        "rejected": "Rechazada",
        "awaiting_approval": "Pendiente de aprobación",
        "failed": "Fallida",
        "stopped_by_limit": "Detenida por límite",
        "stopped_insufficient_evidence": "Evidencia insuficiente",
    }
    return labels.get(status, status or "Sin estado")


# ==========================================
# ENCABEZADO
# ==========================================

col_title = st.container()

with col_title:
    st.markdown(
        """
        <h1 style="color:#13404B; margin-bottom:4px;">
            ¡Bienvenido a FitFamily! 💚
        </h1>
        <p style="color:#52636A; font-size:16px; margin-top:0;">
            Centro de gestión de investigaciones y viabilidad.
        </p>
        """,
        unsafe_allow_html=True,
    )

st.divider()


# ==========================================
# DATOS REALES
# ==========================================

researches = get_all_researches()

total = len(researches)

running = sum(
    get_value(r, "status") == "running"
    for r in researches
)

completed = sum(
    get_value(r, "status") == "completed"
    for r in researches
)

pending = sum(
    get_value(r, "status") == "awaiting_approval"
    for r in researches
)

# ==========================================
# MÉTRICAS
# ==========================================

col_summary, col_refresh = st.columns([8, 1])

with col_summary:
    st.subheader("Resumen de actividad")

updated = st.session_state.get("dashboard_updated", False)

with col_refresh:
    if updated:
        st.markdown("""
            <div style="
                background-color: #4B9567;
                color: white;
                padding: 10px 16px;
                border-radius: 10px;
                text-align: center;
                font-weight: 600;
                white-space: nowrap;
            ">
                ✓ Actualizado
            </div>
        """, unsafe_allow_html=True)

    else:
        if st.button(
            "🔄 Actualizar",
            key="refresh_dashboard",
            use_container_width=True,
        ):
            st.session_state["dashboard_updated"] = True
            st.rerun()

# MANTENER LAS CUATRO MÉTRICAS
col1, col2, col3, col4 = st.columns(4)

col1.metric("Investigaciones", total)
col2.metric("En ejecución", running)
col3.metric("Completadas", completed)
col4.metric("Pendientes de aprobación", pending)

st.divider()


# ==========================================
# INVESTIGACIONES RECIENTES
# ==========================================

st.subheader("Investigaciones recientes")


def traducir_estado(status):
    estados = {
        "running": "En ejecución",
        "awaiting_approval": "Pendiente de aprobación",
        "completed": "Completada",
        "rejected": "Rechazada",
        "stopped_by_limit": "Detenida por límite",
        "stopped_insufficient_evidence": "Detenida por falta de evidencias",
        "failed": "Fallida",
    }
    return estados.get(status, status or "Sin estado")


def traducir_etapa(stage):
    etapas = {
        "research": "Investigación",
        "analysis": "Análisis",
        "writing": "Redacción",
        "review": "Revisión",
        "approval": "Aprobación",
        "completed": "Completada",
        "delivery": "Entrega",
        "rejected": "Rechazada",
    }
    return etapas.get(stage, stage or "Sin etapa")


rows = []

for research in researches:
    rows.append({
        "Identificador": get_value(research, "run_id", ""),
        "Estado": traducir_estado(
            get_value(research, "status", "")
        ),
        "Etapa": traducir_etapa(
            get_value(research, "current_stage", "")
        ),
        "Fecha de creación": get_value(
            research, "created_at", ""
        ),
        "Tipo de encargo": "Investigación",
    })


df = pd.DataFrame(rows)

if not df.empty:
    # Tabla personalizada con colores controlados.
    table_html = """
    <style>
    .fitfamily-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #FFFFFF;
        border-radius: 12px;
        overflow: hidden;
        font-size: 14px;
    }

    .fitfamily-table th {
        background-color: #EDEFE9;
        color: #13404B;
        text-align: left;
        padding: 14px 12px;
        font-weight: 700;
        border-bottom: 2px solid #DDE3DA;
    }

    .fitfamily-table td {
        background-color: #FFFFFF;
        color: #26383B;
        padding: 13px 12px;
        border-bottom: 1px solid #EAE5DC;
    }

    .fitfamily-table tr:hover td {
        background-color: #F4F7F2;
    }

    .fitfamily-table tr:last-child td {
        border-bottom: none;
    }
    </style>
    """

    table_html += """
    <table class="fitfamily-table">
    <thead>
    <tr>
    """

    for column in df.columns:
        table_html += f"<th>{column}</th>"

    table_html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        table_html += "<tr>"
        for value in row:
            table_html += f"<td>{value}</td>"
        table_html += "</tr>"

    table_html += "</tbody></table>"

    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("Todavía no hay investigaciones registradas.")
