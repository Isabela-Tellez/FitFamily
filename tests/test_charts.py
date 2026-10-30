"""Pruebas de los gráficos del análisis de FitFamily."""

import pandas as pd
import pytest

from src.analysis.charts import (
    build_price_chart,
    build_scenario_chart,
)


def test_build_price_chart_creates_png(tmp_path):
    """Comprueba que el gráfico de precios se genera correctamente."""

    competitors = pd.DataFrame(
        [
            {
                "gym_name": "Gimnasio A",
                "monthly_price_eur": 35.0,
            },
            {
                "gym_name": "Gimnasio B",
                "monthly_price_eur": 45.0,
            },
            {
                "gym_name": "Gimnasio C",
                "monthly_price_eur": None,
            },
        ]
    )

    output_path = tmp_path / "prices.png"

    result = build_price_chart(
        competitors,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert result["sample_size"] == 2
    assert result["excluded_price_count"] == 1
    assert result["unit"] == "EUR/month"


def test_build_price_chart_rejects_empty_data():
    """Comprueba que no se genera un gráfico sin competidores."""

    competitors = pd.DataFrame(
        columns=["gym_name", "monthly_price_eur"]
    )

    with pytest.raises(ValueError, match="No hay competidores"):
        build_price_chart(competitors)


def test_build_price_chart_rejects_missing_columns():
    """Comprueba que se detectan las columnas obligatorias ausentes."""

    competitors = pd.DataFrame(
        [{"gym_name": "Gimnasio A"}]
    )

    with pytest.raises(ValueError, match="Faltan columnas"):
        build_price_chart(competitors)


def test_build_scenario_chart_creates_png(tmp_path):
    """Comprueba que se representa un resultado económico."""

    scenarios = {
        "scenario_conservative": [
            {
                "calculation_type": "monthly_result",
                "result": {
                    "value": -500.0,
                    "unit": "EUR/month",
                },
            }
        ],
        "scenario_intermediate": [
            {
                "calculation_type": "monthly_result",
                "result": {
                    "value": 1000.0,
                    "unit": "EUR/month",
                },
            }
        ],
    }

    output_path = tmp_path / "scenarios.png"

    result = build_scenario_chart(
        scenarios,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert result["sample_size"] == 2
    assert result["unit"] == "EUR/month"


def test_build_scenario_chart_rejects_missing_metric():
    """Comprueba que no se dibuja si falta el cálculo solicitado."""

    scenarios = {
        "scenario_intermediate": [
            {
                "calculation_type": "monthly_revenue",
                "result": {
                    "value": 4000.0,
                    "unit": "EUR/month",
                },
            }
        ]
    }

    with pytest.raises(ValueError, match="No hay resultados válidos"):
        build_scenario_chart(scenarios)


def test_build_scenario_chart_rejects_different_units(tmp_path):
    """Comprueba que no se mezclan unidades incompatibles."""

    scenarios = {
        "scenario_a": [
            {
                "calculation_type": "monthly_result",
                "result": {
                    "value": 1000.0,
                    "unit": "EUR/month",
                },
            }
        ],
        "scenario_b": [
            {
                "calculation_type": "monthly_result",
                "result": {
                    "value": 200.0,
                    "unit": "clients",
                },
            }
        ],
    }

    with pytest.raises(ValueError, match="unidades diferentes"):
        build_scenario_chart(
            scenarios,
            output_path=tmp_path / "invalid.png",
        )