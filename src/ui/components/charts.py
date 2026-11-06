"""
Gráficos reutilizables del frontend de FitFamily.

Representan exclusivamente resultados económicos persistidos.
No ejecutan cálculos económicos ni modifican los datos originales.
"""

import pandas as pd
import streamlit as st


SCENARIO_LABELS = {
    "conservative": "Conservador",
    "intermediate": "Intermedio",
    "optimistic": "Optimista",
}

COLORS = {
    "primary": "#13404B",
    "coral": "#E26D5C",
    "sage": "#819885",
}


def get_scenario_label(scenario_type):
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


def format_euros(value):
    if value is None:
        return "No disponible"

    return (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        + " €"
    )


def render_scenario_summary(scenarios):
    """Muestra tres tarjetas con los resultados de cada escenario."""

    st.subheader("Resumen económico")

    columns = st.columns(3)

    for index, item in enumerate(scenarios):

        scenario = item.get("scenario", {})
        calculations = item.get("calculations", [])

        if not isinstance(scenario, dict):
            continue

        name = get_scenario_label(
            scenario.get("scenario_type")
        )

        revenue = get_calculation_value(
            calculations,
            "monthly_revenue",
        )

        result = get_calculation_value(
            calculations,
            "monthly_result",
        )

        with columns[index]:
            with st.container(border=True):

                st.markdown(f"**{name}**")

                st.metric(
                    "Resultado mensual",
                    format_euros(result),
                )

                st.caption(
                    f"Ingresos mensuales: {format_euros(revenue)}"
                )


def render_scenario_comparison(scenarios):
    """Compara horizontalmente ingresos y resultados."""

    st.subheader("Comparación de escenarios")

    st.caption(
        "Comparacíon de los ingresos mensuales estimados "
        "y el resultado de los escenarios conservador, "
        "intermedio y optimista."
    )

    rows = []

    for item in scenarios:

        if not isinstance(item, dict):
            continue

        scenario = item.get("scenario", {})
        calculations = item.get("calculations", [])

        if not isinstance(scenario, dict):
            continue

        rows.append({
            "Escenario": get_scenario_label(
                scenario.get("scenario_type")
            ),
            "Ingresos mensuales": get_calculation_value(
                calculations,
                "monthly_revenue",
            ),
            "Resultado mensual": get_calculation_value(
                calculations,
                "monthly_result",
            ),
        })

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        st.info("No existen escenarios disponibles.")
        return

    dataframe = dataframe.set_index("Escenario")

    st.bar_chart(
        dataframe,
        horizontal=True,
        color=[
            COLORS["primary"],
            COLORS["coral"],
        ],
        height=260,
        width="stretch",
    )


def render_scenario_composition(scenarios):
    """
    Compara la distribución de ingresos entre costes y resultado.

    Los costes incluyen costes fijos y costes variables persistidos.
    """

    st.subheader("Distribución de ingresos")

    st.caption(
        "Comparación de los costes totales y el resultado mensual "
        "de cada escenario."
    )

    rows = []

    for item in scenarios:

        if not isinstance(item, dict):
            continue

        scenario = item.get("scenario", {})
        calculations = item.get("calculations", [])

        if not isinstance(scenario, dict):
            continue

        fixed_costs = scenario.get("fixed_costs")

        variable_costs = get_calculation_value(
            calculations,
            "monthly_variable_costs",
        )

        monthly_result = get_calculation_value(
            calculations,
            "monthly_result",
        )

        if (
            isinstance(fixed_costs, bool)
            or not isinstance(fixed_costs, (int, float))
            or variable_costs is None
            or monthly_result is None
        ):
            continue

        rows.append({
            "Escenario": get_scenario_label(
                scenario.get("scenario_type")
            ),
            "Costes totales": float(fixed_costs) + variable_costs,
            "Resultado mensual": monthly_result,
        })

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        st.info(
            "No hay información suficiente para comparar "
            "la distribución de ingresos."
        )
        return

    dataframe = dataframe.set_index("Escenario")

    st.bar_chart(
        dataframe,
        horizontal=True,
        stack=True,
        color=[
            COLORS["sage"],
            COLORS["coral"],
        ],
        height=300,
        width="stretch",
    )
