"""Pantalla: Indicadores oficiales.

Los valores, estados, periodos y fuentes se leen de la respuesta del
servicio de indicadores. La pantalla no conserva cifras duplicadas ni
presenta valores propios; los datos no verificables se muestran como
«No disponible», nunca como cero.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui.studio import copy, services
from src.ui.studio.components import (
    empty_state,
    note,
    page_header,
    section_header,
)
from src.ui.studio.formatting import format_number, humanize
from src.ui.studio.state import format_value

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
    """Convierte la respuesta en filas con estado explícito."""
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
                "Periodo": item.get("reference_period") or "—",
                "Estado": status,
                "Fuente": item.get("source_url") or "",
                "Limitación / nota": item.get("limitations") or "",
            }
        )
    return pd.DataFrame(rows)


def _filtered(df: pd.DataFrame) -> pd.DataFrame:
    search = st.text_input(
        copy.TEXTS["indicators.search"],
        placeholder="Ej. población, hogares, gimnasios…",
        key="ff_indicator_search",
    )
    states = sorted(df["Estado"].unique().tolist())
    selected = st.multiselect(
        copy.TEXTS["indicators.filter"],
        options=states,
        default=[],
        placeholder="Todos los estados",
        key="ff_indicator_filter",
    )
    result = df
    if search.strip():
        needle = search.strip().lower()
        result = result[
            result["Indicador"].str.lower().str.contains(needle, regex=False)
            | result["Valor"].astype(str).str.lower().str.contains(needle, regex=False)
        ]
    if selected:
        result = result[result["Estado"].isin(selected)]
    return result


def _population_comparison(payload: dict) -> str | None:
    """Explica las dos cifras de población cuando conviven en la respuesta."""
    results = payload.get("results") or {}
    current = (results.get("population_total") or {}).get("value")
    previous = (results.get("population_total_2025") or {}).get("value")
    if current is None or previous is None:
        return None
    return (
        "Hay dos cifras de población con referencias distintas: "
        f"{format_number(current)} habitantes en octubre de 2026 y "
        f"{format_number(previous)} habitantes a 1 de enero de 2025. "
        "No son contradictorias: miden fechas distintas. No las uses como "
        "si fueran el mismo periodo; la diferencia refleja el crecimiento "
        "del barrio y el cambio de referencia."
    )


def render() -> None:
    page_header(
        copy.TEXTS["indicators.title"],
        copy.TEXTS["indicators.subtitle"],
        eyebrow="DATOS OFICIALES",
    )
    note(copy.TEXTS["indicators.note"])
    st.write("")

    if st.button(
        copy.TEXTS["action.update_indicators"],
        type="primary",
        key="ff_update_indicators",
    ):
        services.load_mcp()

    payload = st.session_state.get("ff_mcp")
    error = st.session_state.get("ff_mcp_error")
    if error:
        st.error(
            "No se pudieron actualizar los indicadores oficiales. "
            "Inténtalo de nuevo en unos segundos."
        )
        with st.expander(copy.TEXTS["indicators.technical"]):
            st.code(str(error))
        return

    if not payload:
        empty_state(
            copy.TEXTS["indicators.empty_title"],
            copy.TEXTS["indicators.empty_body"],
        )
        return

    full_df = _indicator_rows(payload)
    if full_df.empty:
        empty_state(
            "Respuesta sin indicadores",
            "La consulta respondió pero no devolvió indicadores para esta zona.",
        )
        return

    verified = int((full_df["Estado"] == "Verificado").sum())
    unavailable = int((full_df["Estado"] == "No disponible").sum())
    st.write("")
    metric_cols = st.columns(3)
    metric_cols[0].metric(
        "Indicadores devueltos",
        str(len(full_df)),
        delta="Respuesta completa",
        delta_color="off",
        border=True,
        help="Número de indicadores incluidos en la respuesta oficial.",
    )
    metric_cols[1].metric(
        "Verificados",
        str(verified),
        delta="Con fuente y periodo",
        delta_color="off",
        border=True,
        help="Indicadores con valor, fuente y periodo confirmados.",
    )
    metric_cols[2].metric(
        "No disponibles",
        str(unavailable),
        delta="Nunca se muestran como cero",
        delta_color="off",
        border=True,
        help="Datos que la fuente no permite verificar.",
    )

    comparison = _population_comparison(payload)
    if comparison:
        st.info(comparison)

    st.write("")
    section_header(copy.TEXTS["indicators.table_title"])
    filtered = _filtered(full_df)
    if filtered.empty:
        st.info(copy.TEXTS["indicators.no_match"])
    else:
        display = filtered[
            ["Indicador", "Valor", "Unidad", "Periodo", "Estado", "Fuente"]
        ]
        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True,
            height=460,
            column_config={
                "Valor": st.column_config.TextColumn("Valor", width="small"),
                "Unidad": st.column_config.TextColumn("Unidad", width="small"),
                "Periodo": st.column_config.TextColumn("Periodo", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small"),
                "Fuente": st.column_config.LinkColumn(
                    "Fuente",
                    display_text="Abrir fuente",
                    width="medium",
                ),
            },
        )

    with_limits = full_df[full_df["Limitación / nota"].astype(str).str.strip() != ""]
    if not with_limits.empty:
        with st.expander(copy.TEXTS["indicators.limitations_title"]):
            for _, row in with_limits.iterrows():
                st.markdown(
                    f"**{row['Indicador']}** · {humanize(row['Limitación / nota'])}"
                )

    st.write("")
    section_header(copy.TEXTS["indicators.source_title"])
    st.write(payload.get("geo_scope") or "Ámbito no especificado.")
    st.write(payload.get("period") or "Periodo no especificado.")
    st.caption(humanize(payload.get("source") or "La consulta no ha devuelto una fuente general."))
    if payload.get("limitations"):
        st.info(humanize(payload["limitations"]))

    with st.expander(copy.TEXTS["indicators.technical"]):
        st.json(payload)
