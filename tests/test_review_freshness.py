"""Pruebas para impedir el uso de revisiones desactualizadas."""

from copy import deepcopy

import pytest

from src.graph.review_routes import choose_review_route_for_draft
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import (
    run_basic_review,
    validate_review_matches_draft,
)
from src.schemas import ResearchResult


def make_draft() -> ReportDraft:
    """Crea un borrador ficticio sin afirmaciones factuales."""
    return ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Introducción\nEstudio pendiente de completar."],
        claims=[
            ReportClaim(
                claim_id="assumption_1",
                text="Se plantea ofrecer una ludoteca.",
                kind="assumption",
                evidence_ids=[],
            )
        ],
        limitations=["Datos ficticios para pruebas."],
    )


def test_unchanged_copy_can_use_review():
    """Una copia con los mismos datos conserva una revisión válida."""
    draft = make_draft()
    review = run_basic_review(draft, ResearchResult())

    route = choose_review_route_for_draft(
        review,
        deepcopy(draft),
        revision_count=0,
    )

    assert route == "pending_review"


def test_review_from_another_draft_is_rejected():
    """El mismo texto no permite reutilizar la revisión de otro informe."""
    draft = make_draft()
    review = run_basic_review(draft, ResearchResult())
    other_draft = make_draft()

    with pytest.raises(ValueError, match="otro borrador"):
        validate_review_matches_draft(review, other_draft)


def test_changed_version_is_rejected():
    """Cambiar la versión exige una revisión nueva."""
    draft = make_draft()
    review = run_basic_review(draft, ResearchResult())

    draft.version += 1

    with pytest.raises(ValueError, match="otra versión"):
        validate_review_matches_draft(review, draft)


@pytest.mark.parametrize(
    "changed_part",
    ["sections", "evidence_ids", "limitations"],
)
def test_changed_content_is_rejected_without_version_change(changed_part):
    """La huella detecta cambios aunque no se actualice la versión."""
    draft = make_draft()
    review = run_basic_review(draft, ResearchResult())

    if changed_part == "sections":
        draft.sections.append("Resultados\nNuevo contenido.")
    elif changed_part == "evidence_ids":
        draft.claims[0].evidence_ids.append("new_reference")
    else:
        draft.limitations.append("Nueva limitación.")

    with pytest.raises(ValueError, match="contenido cambió"):
        choose_review_route_for_draft(
            review,
            draft,
            revision_count=0,
        )


def test_new_review_can_be_used_after_content_change():
    """Volver a revisar permite trabajar con el contenido actualizado."""
    draft = make_draft()
    draft.sections.append("Resultados\nInformación actualizada.")

    new_review = run_basic_review(draft, ResearchResult())

    route = choose_review_route_for_draft(
        new_review,
        draft,
        revision_count=0,
    )

    assert route == "pending_review"