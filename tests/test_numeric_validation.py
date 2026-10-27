"""Ejemplo de conexión entre análisis y revisión con datos ficticios."""

from decimal import Decimal

import pandas as pd
import pytest

from src.analysis.contracts import CalculatedMetric, ReportedMetric
from src.analysis.market_analysis import summarize_competitors
from src.review.numeric_validation import validate_reported_metrics


def make_calculated_metric() -> CalculatedMetric:
    """Ejecuta la función real de Laura sobre tres datos ficticios."""
    data = pd.DataFrame({
        "gym_name": ["Gimnasio A", "Gimnasio B", "Gimnasio C"],
        "monthly_price_eur": [40.0, 45.0, 50.0],
        "has_playroom": [False, True, None],
    })

    summary = summarize_competitors(data)
    average = summary["average_monthly_price_eur"]

    return CalculatedMetric(
        metric_id="market.average_monthly_price_eur",
        value=Decimal(str(average)) if average is not None else None,
        unit="EUR/month",
        calculation=(
            "src.analysis.market_analysis.summarize_competitors"
        ),
        evidence_ids=[
            "demo_price_a",
            "demo_price_b",
            "demo_price_c",
        ],
    )


def make_reported_metric() -> ReportedMetric:
    """Representa una cifra que el informe quiere presentar."""
    return ReportedMetric(
        claim_id="average_price_claim",
        metric_id="market.average_monthly_price_eur",
        reported_value=Decimal("45.00"),
        reported_unit="EUR/month",
    )


def test_correct_value_matches_real_calculation():
    """El informe coincide con el cálculo ejecutado por Python."""
    calculated = make_calculated_metric()
    reported = make_reported_metric()

    assert calculated.value == Decimal("45")

    issues = validate_reported_metrics([reported], [calculated])

    assert issues == []


@pytest.mark.parametrize(
    "field,value,expected_code",
    [
        (
            "reported_value",
            Decimal("50"),
            "metric_value_mismatch",
        ),
        (
            "reported_unit",
            "EUR/year",
            "metric_unit_mismatch",
        ),
        (
            "metric_id",
            "unknown_metric",
            "missing_calculated_metric",
        ),
    ],
)
def test_incorrect_report_requires_writing_correction(
    field,
    value,
    expected_code,
):
    """Detecta cifras, unidades y referencias incorrectas."""
    calculated = make_calculated_metric()
    reported = make_reported_metric().model_copy(
        update={field: value}
    )

    issues = validate_reported_metrics([reported], [calculated])

    assert len(issues) == 1
    assert issues[0].code == expected_code
    assert issues[0].severity == "error"
    assert issues[0].correction_stage == "writing"


def test_unknown_value_cannot_support_a_number():
    """No permite presentar una cifra si el cálculo no está disponible."""
    calculated = make_calculated_metric().model_copy(
        update={"value": None}
    )
    reported = make_reported_metric()

    issues = validate_reported_metrics([reported], [calculated])

    assert issues[0].code == "unavailable_calculated_metric"


def test_duplicate_metric_identifier_requires_analysis_correction():
    """No elige arbitrariamente entre dos resultados del mismo indicador."""
    calculated = make_calculated_metric()
    reported = make_reported_metric()

    issues = validate_reported_metrics(
        [reported],
        [calculated, calculated.model_copy(deep=True)],
    )

    assert issues[0].code == "ambiguous_calculated_metric"
    assert issues[0].correction_stage == "analysis"