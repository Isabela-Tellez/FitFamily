import pandas as pd
import pytest

from src.analysis.market_analysis import (
    classify_competitors,
    summarize_competitors,
)


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


def test_clasificar_competidor_con_ludoteca_verificada_es_directa():
    competitors = pd.DataFrame({
        "gym_name": ["Gym Con Ludoteca"],
        "monthly_price_eur": [45],
        "has_playroom": [True],
    })

    result = classify_competitors(competitors)

    assert result["directa"]["count"] == 1
    assert result["directa"]["competidores"][0]["gym_name"] == "Gym Con Ludoteca"
    assert result["indirecta"]["count"] == 0
    assert result["pendiente_verificacion"]["count"] == 0
    assert result["potencial"]["count"] == 0


def test_clasificar_competidor_sin_ludoteca_es_indirecta():
    competitors = pd.DataFrame({
        "gym_name": ["Gym Sin Ludoteca"],
        "monthly_price_eur": [40],
        "has_playroom": [False],
    })

    result = classify_competitors(competitors)

    assert result["indirecta"]["count"] == 1
    assert result["directa"]["count"] == 0
    assert result["pendiente_verificacion"]["count"] == 0
    assert result["potencial"]["count"] == 0


def test_clasificar_competidor_con_ludoteca_desconocida_es_pendiente():
    competitors = pd.DataFrame({
        "gym_name": ["Gym Dato Desconocido"],
        "monthly_price_eur": [None],
        "has_playroom": [None],
    })

    result = classify_competitors(competitors)

    assert result["pendiente_verificacion"]["count"] == 1
    assert result["directa"]["count"] == 0
    assert result["indirecta"]["count"] == 0
    assert result["potencial"]["count"] == 0


def test_clasificar_plataforma_sin_ludoteca_no_es_potencial():
    # Wellhub es una plataforma, no un gimnasio físico. Como no hay evidencia
    # de ludoteca ni de apertura futura, no debe clasificarse como potencial.
    competitors = pd.DataFrame({
        "gym_name": ["Wellhub"],
        "monthly_price_eur": [0],
        "has_playroom": [None],
    })

    result = classify_competitors(competitors)

    assert result["pendiente_verificacion"]["count"] == 1
    assert result["potencial"]["count"] == 0
    assert result["directa"]["count"] == 0
    assert result["indirecta"]["count"] == 0


def test_clasificar_establecimiento_sin_datos_es_pendiente():
    competitors = pd.DataFrame({
        "gym_name": ["Negocio Misterioso"],
        "monthly_price_eur": [None],
        "has_playroom": [None],
    })

    result = classify_competitors(competitors)

    assert result["pendiente_verificacion"]["count"] == 1
    assert result["total"] == 1
    assert result["directa"]["count"] == 0
    assert result["indirecta"]["count"] == 0
    assert result["potencial"]["count"] == 0


def test_clasificacion_no_inventa_abertura_futura():
    # Ningún competidor tiene evidencia de apertura futura, por lo que
    # potencial debe quedar vacío aunque haya establecimientos pendientes.
    competitors = pd.DataFrame({
        "gym_name": ["Gym A", "Gym B"],
        "monthly_price_eur": [None, None],
        "has_playroom": [None, None],
    })

    result = classify_competitors(competitors)

    assert result["potencial"]["count"] == 0
    assert result["pendiente_verificacion"]["count"] == 2