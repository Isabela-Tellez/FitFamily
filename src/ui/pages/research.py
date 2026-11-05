"""Listado de investigaciones de FitFamily."""

import pandas as pd
import streamlit as st

from src.ui.runtime import get_all_researches
from src.ui.components.status import (
    get_status_label,
    get_stage_label,
)


st.title("📚 Investigaciones")

st.caption(
    "Consulta y administra las investigaciones de viabilidad "
    "registradas en FitFamily."
)

st.divider()

researches = get_all_researches()

if not researches:
    st.info(
        "Todavía no hay investigaciones registradas. "
        "Puedes crear una desde Nueva investigación."
    )
    st.stop()


def get_value(research, key, default=""):
    if isinstance(research, dict):
        return research.get(key, default)

    return getattr(research, key, default)


# Preparar registros
rows = []

for research in researches:
    brief = get_value(research, "brief", {}) or {}

    rows.append({
        "Identificador": get_value(research, "run_id"),
        "Negocio": brief.get("business_type", "No disponible"),
        "Localidad": brief.get("location", "No disponible"),
        "Zona": brief.get("study_area", "No disponible"),
        "Estado": get_status_label(
            get_value(research, "status")
        ),
        "Etapa": get_stage_label(
            get_value(research, "current_stage")
        ),
        "Creación": get_value(research, "created_at"),
        "_status": get_value(research, "status"),
    })


df = pd.DataFrame(rows)

# Resumen
st.subheader("Resumen")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total", len(rows))

col2.metric(
    "En ejecución",
    sum(r["_status"] == "running" for r in rows),
)

col3.metric(
    "Completadas",
    sum(r["_status"] == "completed" for r in rows),
)

col4.metric(
    "Pendientes de aprobación",
    sum(
        r["_status"] == "awaiting_approval"
        for r in rows
    ),
)

st.divider()

# Filtros
st.subheader("Listado de investigaciones")

col_search, col_status = st.columns([2, 1])

with col_search:
    search = st.text_input(
        "Buscar investigación",
        placeholder="Identificador, negocio o localidad...",
    )

with col_status:
    statuses = ["Todos"] + sorted(
        df["Estado"].unique().tolist()
    )

    selected_status = st.selectbox(
        "Estado",
        statuses,
    )

filtered = df.copy()

if search:
    mask = filtered.astype(str).apply(
        lambda column: column.str.contains(
            search,
            case=False,
            na=False,
        )
    ).any(axis=1)

    filtered = filtered[mask]

if selected_status != "Todos":
    filtered = filtered[
        filtered["Estado"] == selected_status
    ]

st.caption(
    f"Mostrando {len(filtered)} de {len(df)} investigaciones"
)

display_columns = [
    "Identificador",
    "Negocio",
    "Localidad",
    "Zona",
    "Estado",
    "Etapa",
    "Creación",
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True,
)


st.divider()
st.subheader("Consultar investigación")

available_researches = {
    str(row["Identificador"]): row["Negocio"]
    for _, row in filtered.iterrows()
    if row["Identificador"]
}

if available_researches:
    selected_id = st.selectbox(
        "Selecciona una investigación",
        options=list(available_researches.keys()),
        format_func=lambda x: (
            f"{available_researches[x]} — {x}"
        ),
    )

    if st.button(
        "📄 Abrir detalle de investigación",
        use_container_width=True,
    ):
        st.session_state["selected_research_id"] = selected_id

        st.switch_page(
            "src/ui/pages/research_detail.py"
        )
