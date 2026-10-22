import pandas as pd
import pytest

from src.analysis.market_analysis import summarize_competitors


def test_summarize_competitors_returns_expected_metrics():
    # Creamos datos ficticios para comprobar los cálculos.
    competitors = pd.DataFrame({
        "gym_name": ["Gym Alpha", "Gym Beta", "Gym Gamma"],
        "monthly_price_eur": [35, 45, None],
        "has_playroom": ["Sí", "No", None],
    })

    # Ejecutamos la función que queremos probar.
    result = summarize_competitors(competitors)

    # Comprobamos que los indicadores tienen los valores esperados.
    assert result["competitor_count"] == 3
    assert result["known_price_count"] == 2
    assert result["average_monthly_price_eur"] == 40.0
    assert result["playroom_yes_count"] == 1
    assert result["playroom_no_count"] == 1
    assert result["playroom_unknown_count"] == 1


def test_summarize_competitors_rejects_missing_columns():
    # Creamos una tabla incompleta para comprobar la validación.
    competitors = pd.DataFrame({
        "gym_name": ["Gym Alpha"],
        "monthly_price_eur": [35],
    })

    # Comprobamos que se genera un error si falta una columna obligatoria.
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_competitors(competitors)

def test_summarize_competitors_returns_no_average_without_prices():
    # Creamos datos ficticios en los que ningún gimnasio publica su precio.
    competitors = pd.DataFrame({
        "gym_name": ["Gym Alpha", "Gym Beta"],
        "monthly_price_eur": [None, None],
        "has_playroom": ["Sí", "No"],
    })

    # Ejecutamos el análisis con los datos sin precios.
    result = summarize_competitors(competitors)

    # Comprobamos que el precio medio queda sin calcular.
    assert result["competitor_count"] == 2
    assert result["known_price_count"] == 0
    assert result["average_monthly_price_eur"] is None

def test_summarize_competitors_accepts_boolean_playroom_values():
    # Comprobamos que los booleanos no se cuentan como desconocidos.
    competitors = pd.DataFrame({
        "gym_name": ["Gym Alpha", "Gym Beta", "Gym Gamma"],
        "monthly_price_eur": [35, 45, None],
        "has_playroom": [True, False, None],
    })

    result = summarize_competitors(competitors)

    assert result["playroom_yes_count"] == 1
    assert result["playroom_no_count"] == 1
    assert result["playroom_unknown_count"] == 1