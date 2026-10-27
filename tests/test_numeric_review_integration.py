"""Integración de cifras, revisión general y control de vigencia."""

from dataclasses import replace
from decimal import Decimal

import pytest

from src.analysis.contracts import CalculatedMetric, ReportedMetric
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchResult


def make_case():
    """Prepara datos ficticios para comprobar la integración."""
    research = ResearchResult(
        evidences=[
            Evidence(
                evidence_id="demo_price",
                claim="La cuota ficticia es de 45 euros al mes.",
                value=45,
                unit="EUR",
                frequency="monthly",
                source_url="https://example.com/precios",
            )
        ]
    )

    metrics = [
        CalculatedMetric(
            metric_id="market.average_monthly_price_eur",
            value=Decimal("45.00"),
            unit="EUR/month",
            calculation="summarize_competitors",
            evidence_ids=["demo_price"],
        )
    ]

    draft = ReportDraft(
        title="Informe ficticio",
        study_area="Zona de prueba",
        claims=[
            ReportClaim(
                claim_id="average_price",
                text="La cuota media de la muestra ficticia es de 45 euros.",
                kind="fact",
                evidence_ids=["demo_price"],
            )
        ],
        reported_metrics=[
            ReportedMetric(
                claim_id="average_price",
                metric_id="market.average_monthly_price_eur",
                reported_value=Decimal("45.00"),
                reported_unit="EUR/month",
            )
        ],
    )

    return draft, research, metrics


def get_route(review, draft, research, metrics):
    """Utiliza el mismo contexto para comprobar la ruta."""
    return choose_review_route_for_context(
        review,
        draft,
        research,
        revision_count=0,
        calculated_metrics=metrics,
    )


def test_matching_number_remains_pending_human_review():
    draft, research, metrics = make_case()

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    assert review.issues == ()
    assert "numeric_values" in review.checks_performed
    assert get_route(review, draft, research, metrics) == "pending_review"


def test_wrong_number_returns_to_writing():
    draft, research, metrics = make_case()

    draft.reported_metrics[0] = (
        draft.reported_metrics[0].model_copy(
            update={"reported_value": Decimal("50.00")}
        )
    )
    draft.claims[0].text = (
        "La cuota media de la muestra ficticia es de 50 euros."
    )

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    assert any(
        issue.code == "metric_value_mismatch"
        for issue in review.issues
    )
    assert get_route(review, draft, research, metrics) == "revise_writing"


def test_missing_analysis_does_not_pass_numeric_review():
    draft, research, _ = make_case()

    review = run_basic_review(draft, research)

    assert any(
        issue.code == "missing_analysis_context"
        for issue in review.issues
    )
    assert get_route(review, draft, research, None) == "revise_analysis"


def test_number_must_belong_to_an_existing_claim():
    draft, research, metrics = make_case()

    draft.reported_metrics[0] = (
        draft.reported_metrics[0].model_copy(
            update={"claim_id": "nonexistent_claim"}
        )
    )

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    assert any(
        issue.code == "numeric_claim_not_found"
        for issue in review.issues
    )
    assert get_route(review, draft, research, metrics) == "revise_writing"


def test_duplicate_numeric_link_requires_correction():
    draft, research, metrics = make_case()

    draft.reported_metrics.append(
        draft.reported_metrics[0].model_copy(deep=True)
    )

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    assert any(
        issue.code == "duplicate_numeric_claim_link"
        for issue in review.issues
    )
    assert get_route(review, draft, research, metrics) == "revise_writing"


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", Decimal("50.00")),
        ("unit", "EUR/year"),
        ("evidence_ids", ["another_evidence"]),
    ],
)
def test_analysis_changes_invalidate_review(field, value):
    draft, research, metrics = make_case()

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    metrics[0] = metrics[0].model_copy(update={field: value})

    with pytest.raises(ValueError, match="análisis cambió"):
        get_route(review, draft, research, metrics)


def test_analysis_cannot_be_omitted_after_review():
    draft, research, metrics = make_case()

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    with pytest.raises(ValueError, match="análisis cambió"):
        get_route(review, draft, research, None)


def test_old_review_without_analysis_fingerprint_is_rejected():
    draft, research, metrics = make_case()

    review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )
    old_review = replace(review, analysis_fingerprint="")

    with pytest.raises(ValueError, match="no tiene huella"):
        get_route(old_review, draft, research, metrics)


def test_new_review_detects_changed_calculation():
    draft, research, metrics = make_case()

    metrics[0] = metrics[0].model_copy(
        update={"value": Decimal("50.00")}
    )

    new_review = run_basic_review(
        draft,
        research,
        calculated_metrics=metrics,
    )

    # La revisión es actual, pero el informe sigue indicando 45.
    assert get_route(
        new_review, draft, research, metrics
    ) == "revise_writing"