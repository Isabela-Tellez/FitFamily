"""Tarjetas reutilizables para el frontend de FitFamily."""

import streamlit as st


def render_section_header(title, description=None):
    st.subheader(title)

    if description:
        st.caption(description)


def render_metric_cards(metrics):
    """Representa métricas en columnas."""

    columns = st.columns(len(metrics))

    for column, metric in zip(columns, metrics):
        with column:
            st.metric(
                label=metric["label"],
                value=metric["value"],
                delta=metric.get("delta"),
            )


def render_empty_state(
    title,
    description,
    icon="📭",
):
    st.markdown(
        f"""
        <div style="
            background: white;
            border: 1px solid #EAECE6;
            border-radius: 16px;
            padding: 32px;
            text-align: center;
        ">
            <div style="font-size: 36px;">{icon}</div>
            <h3>{title}</h3>
            <p style="color: #879189;">
                {description}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
