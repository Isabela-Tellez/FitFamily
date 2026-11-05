
"""
Página de análisis económico de FitFamily.

Consulta exclusivamente resultados económicos persistidos.
No ejecuta agentes ni realiza cálculos económicos.
"""

from __future__ import annotations

import streamlit as st

from src.ui.runtime import get_research_by_id

from src.ui.components.charts import (
    render_scenario_comparison,
    render_cost_breakdown,
    render_scenario_revenue,
)


st.set_page_config(
    page_title="Análisis económico | FitFamily",
    page_icon="📈",
    layout="wide",
)


# ============================================================
# PRESENTACIÓN
# ============================================================

st.title("📈 Análisis económico")

st.caption(
    "Resumen financiero, estructura de costes y viabilidad "
    "económica de FitFamily."
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def format_euros(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "No disponible"

    return (
        f"{value:,.2f} €"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def get_calculation(calculations, calculation_type):
    if not isinstance(calculations, list):
        return None

    matches = [
        item
        for item in calculations
        if isinstance(item, dict)
        and item.get("calculation_type") == calculation_type
    ]

    return matches[0] if len(matches) == 1 else None


def get_result(calculation):
    if not isinstance(calculation, dict):
        return None

    result = calculation.get("result")

    if not isinstance(result, dict):
        return None

    value = result.get("value")

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return float(value)


def get_scenario_data(item):
    if not isinstance(item, dict):
        return {}, []

    scenario = item.get("scenario", {})
    calculations = item.get("calculations", [])

    if not isinstance(scenario, dict):
        scenario = {}

    if not isinstance(calculations, list):
        calculations = []

    return scenario, calculations


SCENARIO_LABELS = {
    "conservative": "Conservador",
    "intermediate": "Intermedio",
    "optimistic": "Optimista",
}

SCENARIO_ORDER = {
    "conservative": 0,
    "intermediate": 1,
    "optimistic": 2,
}


# ============================================================
# CARGA DE INVESTIGACIÓN
# ============================================================

run_id = st.session_state.get("selected_research_id")

if not run_id:
    st.info(
        "Selecciona una investigación desde el módulo "
        "Investigaciones para consultar su análisis económico."
    )
    st.stop()

research = get_research_by_id(run_id)

if not research:
    st.error("No se ha encontrado la investigación seleccionada.")
    st.stop()

analysis = research.get("analysis_result") or {}

if not isinstance(analysis, dict):
    analysis = {}

scenarios = analysis.get("scenarios", [])

if not isinstance(scenarios, list):
    scenarios = []

limitations = analysis.get("limitations", [])

if not isinstance(limitations, list):
    limitations = []

scenarios.sort(
    key=lambda item: SCENARIO_ORDER.get(
        get_scenario_data(item)[0].get("scenario_type"),
        99,
    )
)

st.caption(
    f"Investigación: {run_id}"
)


# ============================================================
# 1. RESUMEN FINANCIERO
# ============================================================

st.divider()
st.header("1. Resumen financiero")

reference_item = next(
    (
        item for item in scenarios
        if get_scenario_data(item)[0].get("scenario_type")
        == "intermediate"
    ),
    None,
)

if reference_item is None and scenarios:
    reference_item = scenarios[0]

if reference_item is None:

    st.info("No existen escenarios económicos disponibles.")

else:

    reference_scenario, reference_calculations = (
        get_scenario_data(reference_item)
    )

    revenue = get_result(
        get_calculation(
            reference_calculations,
            "monthly_revenue",
        )
    )

    variable_costs = get_result(
        get_calculation(
            reference_calculations,
            "monthly_variable_costs",
        )
    )

    monthly_result = get_result(
        get_calculation(
            reference_calculations,
            "monthly_result",
        )
    )

    break_even = get_result(
        get_calculation(
            reference_calculations,
            "break_even",
        )
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Ingresos mensuales",
        format_euros(revenue),
    )

    col2.metric(
        "Costes variables",
        format_euros(variable_costs),
    )

    col3.metric(
        "Resultado mensual",
        format_euros(monthly_result),
    )

    if monthly_result is not None:

        if monthly_result >= 0:
            st.success(
                "El escenario de referencia presenta un resultado "
                "mensual no negativo."
            )
        else:
            st.warning(
                "El escenario de referencia presenta pérdidas mensuales."
            )

    st.caption(
        "Los indicadores corresponden al escenario intermedio "
        "cuando está disponible."
    )


# ============================================================
# 2. ESTRUCTURA DE COSTES
# ============================================================

st.divider()
st.header("2. Estructura de costes")

if reference_item is not None:

    reference_scenario, reference_calculations = (
        get_scenario_data(reference_item)
    )

    fixed_costs = reference_scenario.get("fixed_costs")

    col1, col2 = st.columns(2)

    col1.metric(
        "Costes fijos mensuales",
        format_euros(fixed_costs),
    )

    col2.metric(
        "Costes variables mensuales",
        format_euros(variable_costs),
    )

    cost_chart_data = {
        "fixed_costs": fixed_costs,
        "calculations": reference_calculations,
    }

    render_cost_breakdown(cost_chart_data)

    st.caption(
        "El desglose detallado por instalaciones, personal, "
        "suministros, equipamiento y ludoteca requiere "
        "datos específicos."
    )

else:
    st.info("No hay información de costes disponible.")


# ============================================================
# 3. PREVISIÓN DE INGRESOS
# ============================================================

st.divider()
st.header("3. Previsión de ingresos")

render_scenario_revenue(scenarios)


# ============================================================
# 4. PUNTO DE EQUILIBRIO
# ============================================================

st.divider()
st.header("4. Punto de equilibrio")

if scenarios:

    for item in scenarios:

        scenario, calculations = get_scenario_data(item)

        scenario_type = scenario.get("scenario_type", "")

        scenario_name = SCENARIO_LABELS.get(
            scenario_type,
            "Escenario económico",
        )

        break_even = get_result(
            get_calculation(
                calculations,
                "break_even",
            )
        )

        with st.container(border=True):

            st.subheader(scenario_name)

            if break_even is not None:

                st.metric(
                    "Clientes necesarios",
                    f"{break_even:,.0f}",
                )

            else:
                st.info(
                    "Punto de equilibrio no disponible."
                )

            monthly_fee = scenario.get("monthly_fee")
            variable_cost = scenario.get(
                "variable_cost_per_client"
            )

            if (
                isinstance(monthly_fee, (int, float))
                and isinstance(variable_cost, (int, float))
                and not isinstance(monthly_fee, bool)
                and not isinstance(variable_cost, bool)
            ):

                st.write(
                    "**Margen de contribución por cliente:**",
                    format_euros(monthly_fee - variable_cost),
                )

else:
    st.info("No existen escenarios para evaluar el punto de equilibrio.")


# ============================================================
# 5. COMPARACIÓN DE ESCENARIOS
# ============================================================

st.divider()
st.header("5. Comparación de escenarios")

render_scenario_comparison(scenarios)


# ============================================================
# 6. VIABILIDAD ECONÓMICA
# ============================================================

st.divider()
st.header("6. Viabilidad económica")

if limitations:

    st.subheader("Limitaciones y riesgos")

    for limitation in limitations:
        st.warning(str(limitation))

else:
    st.info("No hay limitaciones económicas registradas.")

if scenarios:

    st.subheader("Hipótesis utilizadas")

    for item in scenarios:

        scenario, _ = get_scenario_data(item)

        scenario_name = SCENARIO_LABELS.get(
            scenario.get("scenario_type"),
            "Escenario económico",
        )

        assumptions = scenario.get("assumptions", [])

        with st.expander(scenario_name):

            if assumptions:

                for assumption in assumptions:
                    st.write(f"- {assumption}")

            else:
                st.caption("No hay hipótesis documentadas.")


# ============================================================
# FINAL
# ============================================================

st.divider()

st.caption(
    "FitFamily · Los resultados económicos son estimaciones "
    "dependientes de los datos y supuestos registrados."
)

if st.button("← Volver a investigaciones"):
    st.switch_page("src/ui/pages/research.py")
