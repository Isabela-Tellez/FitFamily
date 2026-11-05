"""Gráficos reutilizables del frontend de FitFamily.

Representan exclusivamente resultados económicos persistidos.
No ejecutan cálculos ni modifican los datos originales.
"""

import pandas as pd
import streamlit as st


SCENARIO_LABELS = {
    "conservative": "Conservador",
    "intermediate": "Intermedio",
    "optimistic": "Optimista",
}


def get_scenario_label(scenario_type):
    """Devuelve el nombre visual de un escenario."""

    return SCENARIO_LABELS.get(
        scenario_type,
        str(scenario_type or "Escenario"),
    )


def get_calculation_value(calculations, calculation_type):
    """Recupera un resultado numérico persistido."""

    if not isinstance(calculations, list):
        return None

    matches = [
        item
        for item in calculations
        if isinstance(item, dict)
        and item.get("calculation_type") == calculation_type
    ]

    # Evitamos elegir arbitrariamente entre duplicados.
    if len(matches) != 1:
        return None

    result = matches[0].get("result")

    if not isinstance(result, dict):
        return None

    value = result.get("value")

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        return None

    return float(value)


def render_scenario_comparison(scenarios):
    """Compara ingresos y resultados mensuales."""

    st.subheader("Comparación de escenarios")

    rows = []

    for item in scenarios:

        if not isinstance(item, dict):
            continue

        scenario = item.get("scenario", {})
        calculations = item.get("calculations", [])

        if not isinstance(scenario, dict):
            continue

        scenario_type = scenario.get("scenario_type")

        rows.append({
            "Escenario": get_scenario_label(scenario_type),
            "Ingresos mensuales": get_calculation_value(
                calculations,
                "monthly_revenue",
            ),
            "Resultado mensual": get_calculation_value(
                calculations,
                "monthly_result",
            ),
        })

    if not rows:
        st.info("No existen escenarios disponibles.")
        return

    dataframe = pd.DataFrame(rows).set_index("Escenario")

    st.bar_chart(
        dataframe,
        use_container_width=True,
    )

    st.dataframe(
        dataframe.reset_index(),
        use_container_width=True,
        hide_index=True,
    )


def render_cost_breakdown(scenario_item):
    """Representa los costes fijos y variables mensuales."""

    st.subheader("Estructura de costes")

    if not isinstance(scenario_item, dict):
        st.info("No hay datos del escenario disponibles.")
        return

    # Aceptamos el objeto completo persistido.
    scenario = scenario_item.get("scenario", scenario_item)
    calculations = scenario_item.get(
        "calculations",
        scenario.get("calculations", []),
    )

    if not isinstance(scenario, dict):
        st.info("No hay datos del escenario disponibles.")
        return

    fixed_costs = scenario.get("fixed_costs")

    variable_costs = get_calculation_value(
        calculations,
        "monthly_variable_costs",
    )

    values = {
        "Costes fijos": fixed_costs,
        "Costes variables": variable_costs,
    }

    valid_values = {}

    for label, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            continue

        valid_values[label] = float(value)

    if not valid_values:
        st.info(
            "No hay información suficiente para representar los costes."
        )
        return

    dataframe = pd.DataFrame({
        "Tipo de coste": list(valid_values.keys()),
        "Importe mensual (€)": list(valid_values.values()),
    })

    st.bar_chart(
        dataframe.set_index("Tipo de coste"),
        use_container_width=True,
    )


def render_scenario_revenue(scenarios):
    """Compara los ingresos mensuales de cada escenario."""

    st.subheader("Previsión de ingresos")

    rows = []

    for item in scenarios:

        if not isinstance(item, dict):
            continue

        scenario = item.get("scenario", {})

        if not isinstance(scenario, dict):
            continue

        revenue = get_calculation_value(
            item.get("calculations", []),
            "monthly_revenue",
        )

        if revenue is None:
            continue

        rows.append({
            "Escenario": get_scenario_label(
                scenario.get("scenario_type")
            ),
            "Ingresos mensuales (€)": revenue,
        })

    if not rows:
        st.info("No hay ingresos calculados disponibles.")
        return

    dataframe = pd.DataFrame(rows).set_index("Escenario")

    st.bar_chart(
        dataframe,
        use_container_width=True,
    )
