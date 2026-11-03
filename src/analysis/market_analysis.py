import pandas as pd
import math


def normalize_playroom_value(value: object) -> bool | None:
    """
    Normaliza los datos de ludoteca a True, False o None.

    Los valores desconocidos o no reconocidos se mantienen como None.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return None

    if isinstance(value, str):
        normalized_value = value.strip().casefold()

        if normalized_value in {"sí", "si", "true", "yes"}:
            return True

        if normalized_value in {"no", "false"}:
            return False

    return None


def normalize_prices(data: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los precios de una tabla de competidores.

    Los precios ausentes o no válidos se mantienen como valores desconocidos.
    No convierte tarifas de otras frecuencias en cuotas mensuales.
    """
    required_columns = {
        "gym_name",
        "monthly_price_eur",
        "has_playroom",
    }

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    normalized_data = data.copy()

    normalized_data["gym_name"] = (
        normalized_data["gym_name"]
        .astype("string")
        .str.strip()
    )

    normalized_data["monthly_price_eur"] = pd.to_numeric(
        normalized_data["monthly_price_eur"],
        errors="coerce",
    )

    # No consideramos precios negativos válidos.
    normalized_data.loc[
        normalized_data["monthly_price_eur"] < 0,
        "monthly_price_eur",
    ] = float("nan")

    normalized_data["has_playroom"] = (
        normalized_data["has_playroom"]
        .map(normalize_playroom_value)
    )

    return normalized_data


def summarize_competitors(data: pd.DataFrame) -> dict:
    """
    Resume los precios y la disponibilidad de ludoteca.

    Los promedios se calculan solo con precios mensuales conocidos.
    """
    normalized_data = normalize_prices(data)

    prices = normalized_data["monthly_price_eur"]
    playroom = normalized_data["has_playroom"]

    return {
        "competitor_count": len(normalized_data),
        "known_price_count": int(prices.notna().sum()),
        "average_monthly_price_eur": (
            round(float(prices.mean()), 2)
            if prices.notna().any()
            else None
        ),
        "playroom_yes_count": int(playroom.eq(True).sum()),
        "playroom_no_count": int(playroom.eq(False).sum()),
        "playroom_unknown_count": int(playroom.isna().sum()),
    }


def compare_competitors(data: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara una tabla comparable de competidores.

    Los competidores con precio mensual conocido aparecen primero.
    No se eliminan los datos desconocidos.
    """
    normalized_data = normalize_prices(data)

    return normalized_data.sort_values(
        by=["monthly_price_eur", "gym_name"],
        ascending=[True, True],
        na_position="last",
    ).reset_index(drop=True)


def calculate_indicators(data: pd.DataFrame) -> dict:
    """
    Calcula los indicadores descriptivos básicos del mercado.
    """
    summary = summarize_competitors(data)

    known_price_count = summary["known_price_count"]
    competitor_count = summary["competitor_count"]

    summary["price_coverage_percentage"] = (
        round(known_price_count / competitor_count * 100, 2)
        if competitor_count > 0
        else None
    )

    return summary


def summarize_research_result(research_result: object) -> dict | None:
    """
    Adapta el resultado de investigación al formato del análisis de mercado.

    Solo utiliza tarifas identificadas como mensuales y conserva como
    desconocidos los precios y servicios que no estén documentados.
    """
    if research_result is None:
        return None

    if isinstance(research_result, dict):
        competitors = research_result.get("competitors", [])
    else:
        competitors = getattr(research_result, "competitors", [])

    rows = []

    for competitor in competitors or []:
        if isinstance(competitor, dict):
            name = competitor.get("name")
            tariffs = competitor.get("tariffs", [])
            has_playroom = competitor.get("has_playroom")
        else:
            name = getattr(competitor, "name", None)
            tariffs = getattr(competitor, "tariffs", [])
            has_playroom = getattr(competitor, "has_playroom", None)

        monthly_prices = []

        for tariff in tariffs or []:
            if not isinstance(tariff, dict):
                continue

            frequency = str(
                tariff.get("frequency") or ""
            ).strip().casefold()

            value = tariff.get("value")

            if frequency in {"monthly", "mensual", "month"} and value is not None:
                try:
                    price = float(value)
                except (TypeError, ValueError):
                    continue

                if math.isfinite(price) and price >= 0:
                    monthly_prices.append(price)

        # No elegimos arbitrariamente entre varias tarifas mensuales.
        # Si existen varias, se deja el precio sin resolver hasta definir
        # una regla de comparación que tenga en cuenta sus condiciones.
        monthly_price = (
            monthly_prices[0]
            if len(monthly_prices) == 1
            else None
        )

        rows.append(
            {
                "gym_name": name or "Unknown competitor",
                "monthly_price_eur": monthly_price,
                "has_playroom": has_playroom,
            }
        )

    if not rows:
        return {
            "competitor_count": 0,
            "known_price_count": 0,
            "average_monthly_price_eur": None,
            "playroom_yes_count": 0,
            "playroom_no_count": 0,
            "playroom_unknown_count": 0,
            "price_coverage_percentage": None,
        }

    competitors_data = pd.DataFrame(rows)

    return calculate_indicators(competitors_data)