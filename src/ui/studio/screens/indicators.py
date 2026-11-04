"""Pantalla: Indicadores oficiales (consulta MCP real).

Los valores, estados, periodos y fuentes se leen de la respuesta del
servidor MCP local; esta pantalla no conserva cifras duplicadas ni
presenta valores propios.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.studio import services
from src.ui.studio.components import (
    empty_state,
    note,
    page_header,
    render_metrics,
    render_table,
    section_header,
)
from src.ui.studio.state import format_value

# Etiquetas legibles de los indicadores que MCP puede devolver
INDICATOR_LABELS = {
    "population_total": "Población total",
    "population_total_2025": "Población total · 2025",
    "households_total": "Hogares totales",
    "average_household_size": "Tamaño medio del hogar",
    "population_under_20_share": "Población menor de 20 años",
    "households_with_minors": "Hogares con menores",
    "families_with_children": "Familias con hijos",
    "businesses_open": "Locales abiertos",
    "gyms_registered": "Gimnasios registrados",
    "gyms_with_ludoteca": "Gimnasios con ludoteca",
    "sports_recreation": "Deporte y recreación",
    "child_leisure": "Ocio infantil",
    "community_pools": "Piscinas comunitarias",
}


def _indicator_rows(payload: dict) -> pd.DataFrame:
    """Convierte la respuesta MCP en filas con estado explícito."""
    rows = []
    for key, item in (payload.get("results") or {}).items():
        item = item if isinstance(item, dict) else {"value": item}
        value = item.get("value")
        verification = item.get("verification_status")
        if value is None or verification == "unavailable":
            status = "No disponible"
        elif verification == "verified":
            status = "Verificado"
        else:
            status = "Sin verificar"
        rows.append(
            {
                "Indicador": INDICATOR_LABELS.get(key, key.replace("_", " ").capitalize()),
                "Valor": format_value(value),
                "Unidad": item.get("unit") or "—",
                "Periodo de referencia": item.get("reference_period") or "—",
                "Estado": status,
                "Fuente": item.get("source_url") or "—",
                "Limitación / nota": item.get("limitations") or "—",
            }
        )
    return pd.DataFrame(rows)


def render() -> None:
    page_header(
        "Indicadores municipales",
        "Consulta en tiempo real el servidor MCP local. Los valores, estados, "
        "periodos y fuentes se leen de su respuesta; esta pantalla no conserva "
        "cifras duplicadas.",
        eyebrow="DATOS OFICIALES",
    )
    note(
        "Los hogares no equivalen a familias. Un indicador con valor "
        "<strong>null</strong> se presenta como «No disponible» y nunca como cero."
    )
    st.write("")

    if st.button("Consultar indicadores MCP", type="primary"):
        services.load_mcp()

    payload = st.session_state.get("ff_mcp")
    if st.session_state.get("ff_mcp_error"):
        st.error(f"No se pudo consultar MCP: {st.session_state['ff_mcp_error']}")

    if not payload:
        if not st.session_state.get("ff_mcp_error"):
            empty_state(
                "Sin consulta activa",
                "Pulsa «Consultar indicadores MCP» para recuperar los datos "
                "oficiales desde el servidor local. La consulta solo se ejecuta "
                "cuando tú lo pides.",
            )
        return

    result_df = _indicator_rows(payload)
    if result_df.empty:
        empty_state(
            "Respuesta sin indicadores",
            "El servidor MCP respondió pero no devolvió indicadores para esta zona.",
        )
        return

    verified = int((result_df["Estado"] == "Verificado").sum())
    unavailable = int((result_df["Estado"] == "No disponible").sum())
    render_metrics(
        [
            ("Indicadores devueltos", str(len(result_df)), "Respuesta completa de MCP"),
            ("Verificados", str(verified), "Con fuente y periodo confirmados"),
            ("No disponibles", str(unavailable), "Valor nulo documentado, nunca cero"),
        ],
        columns=3,
    )
    st.write("")

    section_header("Tabla de indicadores")
    st.dataframe(
        result_df,
        hide_index=True,
        use_container_width=True,
        height=480,
        column_config={"Fuente": st.column_config.LinkColumn("Fuente", display_text="Abrir fuente")},
    )

    st.write("")
    section_header("Contexto de la fuente")
    st.write(payload.get("geo_scope") or "Ámbito no especificado por MCP")
    st.write(payload.get("period") or "Periodo no especificado por MCP")
    st.caption(payload.get("source") or "MCP no ha devuelto una fuente general.")
    if payload.get("limitations"):
        st.info(payload["limitations"])

    with st.expander("Respuesta estructurada original de MCP"):
        st.json(payload)
