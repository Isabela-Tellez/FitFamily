import pandas as pd


import pandas as pd

def normalize_playroom_value(value: object) -> bool | None:
    """
    Normaliza los datos de ludoteca a True, False o None.

    Acepta valores booleanos y respuestas textuales en castellano.
    Los valores ausentes o no reconocidos se consideran desconocidos.
    """
    # Conservamos los valores booleanos que ya están normalizados.
    if isinstance(value, bool):
        return value

    # Tratamos los valores ausentes como desconocidos.
    if pd.isna(value):
        return None

    # Normalizamos las respuestas de texto.
    if isinstance(value, str):
        normalized_value = value.strip().casefold()

        if normalized_value in {"sí", "si", "true"}:
            return True

        if normalized_value in {"no", "false"}:
            return False

    # No interpretamos valores inesperados como respuestas conocidas.
    return None

def summarize_competitors(data: pd.DataFrame) -> dict:
    """
    Resume la información básica de los gimnasios competidores.

    Parámetros:
        data: tabla que contiene los datos de los gimnasios.

    Devuelve:
        Un diccionario con los principales indicadores del mercado.
    """
    # Definimos las columnas obligatorias para realizar el análisis.
    required_columns = {
        "gym_name",
        "monthly_price_eur",
        "has_playroom",
    }

    # Comprobamos si falta alguna columna necesaria.
    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Convertimos los precios a números.
    # Los valores ausentes o no válidos se consideran desconocidos.
    prices = pd.to_numeric(
        data["monthly_price_eur"],
        errors="coerce",
    )

    # Normalizamos todas las respuestas al mismo formato booleano.
    playroom = data["has_playroom"].map(normalize_playroom_value)

    # Contamos los estados conocidos y los desconocidos.
    playroom_yes_count = int(playroom.eq(True).sum())
    playroom_no_count = int(playroom.eq(False).sum())
    playroom_unknown_count = int(playroom.isna().sum())

    return {
        "competitor_count": len(data),
        "known_price_count": int(prices.notna().sum()),
        "average_monthly_price_eur": (
            round(float(prices.mean()), 2)
            if prices.notna().any()
            else None
        ),
        "playroom_yes_count": playroom_yes_count,
        "playroom_no_count": playroom_no_count,
        "playroom_unknown_count": playroom_unknown_count,
    }