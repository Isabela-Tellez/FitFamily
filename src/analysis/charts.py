"""Generación de gráficos reproducibles para el análisis de FitFamily."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def _prepare_output_path(output_path: str | Path) -> Path:
    """Prepara la ruta de salida y crea su directorio si es necesario."""

    path = Path(output_path)

    if path.suffix.lower() != ".png":
        raise ValueError("El archivo de salida debe tener extensión .png.")

    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def build_price_chart(
    competitors: pd.DataFrame,
    output_path: str | Path = "artifacts/price_comparison.png",
) -> dict[str, Any]:
    """Genera un gráfico de precios mensuales de los competidores.

    Parámetros:
        competitors: tabla con gym_name y monthly_price_eur.
        output_path: ruta donde guardar el gráfico PNG.

    Devuelve:
        Metadatos del gráfico, ruta, unidades y tamaño de la muestra.

    Los precios ausentes o no válidos se excluyen del gráfico y se cuentan
    explícitamente. No se interpretan como precios de cero euros.
    """

    required_columns = {"gym_name", "monthly_price_eur"}
    missing_columns = required_columns - set(competitors.columns)

    if missing_columns:
        raise ValueError(
            f"Faltan columnas obligatorias: {sorted(missing_columns)}"
        )

    if competitors.empty:
        raise ValueError("No hay competidores para representar.")

    data = competitors[["gym_name", "monthly_price_eur"]].copy()

    data["gym_name"] = (
        data["gym_name"]
        .fillna("Nombre desconocido")
        .astype(str)
        .str.strip()
        .replace("", "Nombre desconocido")
    )

    data["monthly_price_eur"] = pd.to_numeric(
        data["monthly_price_eur"],
        errors="coerce",
    )

    # Solo se representan precios mensuales conocidos y no negativos.
    valid_prices = (
        data["monthly_price_eur"].notna()
        & data["monthly_price_eur"].ge(0)
    )

    excluded_count = int((~valid_prices).sum())
    data = data.loc[valid_prices].copy()

    if data.empty:
        raise ValueError(
            "No hay precios mensuales válidos para representar."
        )

    # Ordenamos los precios para facilitar la comparación.
    data = data.sort_values(
        ["monthly_price_eur", "gym_name"],
        ascending=[True, True],
    )

    output = _prepare_output_path(output_path)

    figure_height = max(4.0, len(data) * 0.45)

    fig, ax = plt.subplots(figsize=(10, figure_height))

    positions = list(range(len(data)))

    bars = ax.barh(
        positions,
        data["monthly_price_eur"],
    )

    ax.set_yticks(positions)
    ax.set_yticklabels(data["gym_name"])
    ax.set_xlabel("Precio mensual (€)")
    ax.set_ylabel("Competidor")
    ax.set_title("Comparación de precios mensuales")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    # Mostramos el importe al lado de cada barra.
    ax.bar_label(
        bars,
        labels=[
            f"{price:.2f} €"
            for price in data["monthly_price_eur"]
        ],
        padding=4,
    )

    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)

    metadata = {
        "chart_type": "price_comparison",
        "path": str(output),
        "title": "Comparación de precios mensuales",
        "x_axis": "Precio mensual (€)",
        "y_axis": "Competidor",
        "unit": "EUR/month",
        "sample_size": int(len(data)),
        "excluded_price_count": excluded_count,
        "source_columns": [
            "gym_name",
            "monthly_price_eur",
        ],
    }

    logger.info("Gráfico de precios guardado en %s", output)

    return metadata


def build_scenario_chart(
    scenarios: dict[str, Any] | list[dict[str, Any]],
    output_path: str | Path = "artifacts/economic_scenarios.png",
    metric: str = "monthly_result",
) -> dict[str, Any]:
    """Genera un gráfico comparativo de resultados económicos.

    Parámetros:
        scenarios: lista de escenarios o diccionario indexado por escenario.
        output_path: ruta donde guardar el gráfico PNG.
        metric: tipo de cálculo que se quiere representar.

    Admite escenarios serializados con una lista de cálculos que contengan
    calculation_type y result.value/unit, como los modelos del proyecto.

    Devuelve:
        Metadatos del gráfico, ruta, unidades y escenarios representados.

    Los escenarios sin el cálculo solicitado o sin resultado numérico se
    excluyen y quedan reflejados en excluded_scenario_count.
    """

    if isinstance(scenarios, dict):
        scenario_items = list(scenarios.items())
    elif isinstance(scenarios, list):
        scenario_items = [
            (str(item.get("scenario_type", item.get("scenario_id", index))), item)
            for index, item in enumerate(scenarios)
        ]
    else:
        raise ValueError(
            "scenarios debe ser un diccionario o una lista de escenarios."
        )

    if not scenario_items:
        raise ValueError("No hay escenarios económicos para representar.")

    chart_rows: list[dict[str, Any]] = []
    excluded_count = 0
    units: set[str] = set()

    for scenario_name, scenario_data in scenario_items:
        # Aceptamos tanto listas de cálculos como estructuras anidadas.
        calculations = scenario_data

        if isinstance(scenario_data, dict):
            calculations = scenario_data.get(
                "calculations",
                scenario_data.get("results", []),
            )

        if not isinstance(calculations, list):
            excluded_count += 1
            continue

        matching_calculations = [
            calculation
            for calculation in calculations
            if isinstance(calculation, dict)
            and calculation.get("calculation_type") == metric
        ]

        if len(matching_calculations) != 1:
            excluded_count += 1
            continue

        calculation = matching_calculations[0]
        result = calculation.get("result")

        if not isinstance(result, dict):
            excluded_count += 1
            continue

        value = result.get("value")
        unit = result.get("unit")

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            excluded_count += 1
            continue

        if not pd.notna(value) or not unit:
            excluded_count += 1
            continue

        chart_rows.append(
            {
                "scenario": str(scenario_name),
                "value": float(value),
                "unit": str(unit),
            }
        )
        units.add(str(unit))

    if not chart_rows:
        raise ValueError(
            f"No hay resultados válidos para el cálculo {metric!r}."
        )

    # No mezclamos resultados con unidades diferentes.
    if len(units) != 1:
        raise ValueError(
            "Los resultados tienen unidades diferentes y no se pueden "
            "representar juntos."
        )

    data = pd.DataFrame(chart_rows)

    output = _prepare_output_path(output_path)

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.bar(
        data["scenario"],
        data["value"],
    )

    ax.set_title(
        f"Comparación de escenarios económicos: {metric}"
    )
    ax.set_xlabel("Escenario")
    ax.set_ylabel(f"Resultado ({next(iter(units))})")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    ax.bar_label(
        bars,
        labels=[
            f"{value:,.2f}"
            for value in data["value"]
        ],
        padding=4,
    )

    fig.tight_layout()
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)

    metadata = {
        "chart_type": "economic_scenarios",
        "path": str(output),
        "title": f"Comparación de escenarios económicos: {metric}",
        "metric": metric,
        "unit": next(iter(units)),
        "sample_size": int(len(data)),
        "excluded_scenario_count": excluded_count,
        "scenarios": data.to_dict(orient="records"),
    }

    logger.info("Gráfico de escenarios guardado en %s", output)

    return metadata