import pandas as pd


import pandas as pd


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

    # Normalizamos las respuestas sobre la existencia de ludoteca.
    playroom = (
        data["has_playroom"]
        .astype("string")
        .str.strip()
        .str.casefold()
    )

    # Identificamos las respuestas que podemos interpretar.
    valid_answers = playroom.isin(["sí", "si", "no"])

    return {
        "competitor_count": len(data),
        "known_price_count": int(prices.notna().sum()),
        "average_monthly_price_eur": (
            round(float(prices.mean()), 2)
            if prices.notna().any()
            else None
        ),
        "playroom_yes_count": int(
            playroom.isin(["sí", "si"]).sum()
        ),
        "playroom_no_count": int(
            playroom.eq("no").sum()
        ),
        "playroom_unknown_count": int(
            (~valid_answers).sum()
        ),
    }