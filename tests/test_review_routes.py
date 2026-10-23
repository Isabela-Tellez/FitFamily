"""Pruebas de prioridades y límites de las rutas de revisión."""

import pytest

from src.graph.review_routes import choose_review_route
from src.review.models import ReviewIssue, ReviewResult


def make_review(*stages: str) -> ReviewResult:
    """Crea incidencias ficticias para las etapas indicadas."""
    issues = tuple(
        ReviewIssue(
            code="test_issue",
            reference_id=f"reference_{index}",
            message="Problema ficticio.",
            severity="error",
            correction_stage=stage,
        )
        for index, stage in enumerate(stages, start=1)
    )

    return ReviewResult(
        draft_id="draft_test",
        draft_version=1,
        draft_fingerprint="test_fingerprint",
        issues=issues,
        checks_performed=("claim_references", "evidence_quality"),
    )


@pytest.mark.parametrize(
    "stages, expected",
    [
        (("writing",), "revise_writing"),
        (("writing", "analysis"), "revise_analysis"),
        (("writing", "research", "analysis"), "revise_research"),
    ],
)
def test_selects_earliest_stage(stages, expected):
    review = make_review(*stages)

    assert choose_review_route(review, revision_count=0) == expected


def test_allows_last_available_correction():
    review = make_review("writing")

    assert choose_review_route(
        review,
        revision_count=1,
        max_revisions=2,
    ) == "revise_writing"


@pytest.mark.parametrize("revision_count", [2, 3])
def test_blocks_when_correction_limit_is_reached(revision_count):
    review = make_review("research")

    assert choose_review_route(
        review,
        revision_count=revision_count,
        max_revisions=2,
    ) == "blocked"


def test_no_errors_keeps_full_review_pending():
    review = make_review()

    assert choose_review_route(
        review,
        revision_count=2,
    ) == "pending_review"


def test_warning_does_not_trigger_correction():
    review = ReviewResult(
        draft_id="draft_test",
        draft_version=1,
        draft_fingerprint="test_fingerprint",
        issues=(
            ReviewIssue(
                code="test_warning",
                reference_id="reference_1",
                message="Advertencia ficticia.",
                severity="warning",
                correction_stage="research",
            ),
        ),
        checks_performed=("evidence_quality",),
    )

    assert choose_review_route(review, revision_count=0) == "pending_review"


@pytest.mark.parametrize(
    "revision_count, max_revisions",
    [
        (-1, 2),
        (0, -1),
        (1.5, 2),
        (True, 2),
    ],
)
def test_rejects_invalid_counters(revision_count, max_revisions):
    with pytest.raises(ValueError):
        choose_review_route(
            make_review("writing"),
            revision_count=revision_count,
            max_revisions=max_revisions,
        )


def test_zero_limit_blocks_first_correction():
    assert choose_review_route(
        make_review("writing"),
        revision_count=0,
        max_revisions=0,
    ) == "blocked"


def test_rejects_unknown_correction_stage():
    with pytest.raises(ValueError, match="etapa desconocida"):
        choose_review_route(
            make_review("unknown"),
            revision_count=0,
        )