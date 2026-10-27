"""Pruebas de estructura y clasificación de las afirmaciones."""

from copy import deepcopy

import pytest

from src.graph.review_routes import choose_review_route_for_context
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.review.validation import validate_claim_structure
from src.schemas import ResearchResult


def make_draft():
    """Crea un supuesto ficticio para las pruebas."""
    return ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="assumption_1",
                text="Suponemos un alquiler mensual de 2.000 euros.",
                kind="assumption",
            )
        ],
    )


@pytest.mark.parametrize("kind", ["fact", "assumption", "inference"])
def test_allowed_classifications_have_valid_structure(kind):
    """Esta comprobación acepta los tres tipos previstos."""
    draft = make_draft()
    draft.claims[0].kind = kind

    assert validate_claim_structure(draft) == []


@pytest.mark.parametrize(
    "field,value,expected_code",
    [
        ("claim_id", "   ", "empty_claim_id"),
        ("text", "   ", "empty_claim_text"),
        ("kind", "opinion", "invalid_claim_kind"),
    ],
)
def test_invalid_structure_requires_writing_correction(
    field,
    value,
    expected_code,
):
    """Los errores se integran en la revisión y vuelven a redacción."""
    draft = make_draft()
    setattr(draft.claims[0], field, value)
    research = ResearchResult()

    review = run_basic_review(draft, research)

    issue = next(
        item for item in review.issues
        if item.code == expected_code
    )

    assert issue.severity == "error"
    assert issue.correction_stage == "writing"
    assert review.status == "needs_revision"

    assert choose_review_route_for_context(
        review,
        draft,
        research,
        revision_count=0,
    ) == "revise_writing"


def test_structure_validation_does_not_modify_draft():
    """El revisor informa del problema sin corregir el contenido."""
    draft = make_draft()
    draft.claims[0].text = "   "
    original = deepcopy(draft)

    issues = validate_claim_structure(draft)

    assert any(
        issue["code"] == "empty_claim_text"
        for issue in issues
    )
    assert draft == original