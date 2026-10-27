"""Pruebas de vigencia de la investigación utilizada en la revisión."""

from dataclasses import replace

import pytest

from src.graph.review_routes import choose_review_route_for_context
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import Competitor, Evidence, ResearchResult


def make_case():
    """Crea un informe y una investigación completamente ficticios."""
    evidence = Evidence(
        evidence_id="price_1",
        claim="La cuota mensual es de 45 euros.",
        value=45,
        unit="EUR",
        frequency="monthly",
        source_url="https://example.com/precios",
    )

    research = ResearchResult(
        evidences=[evidence],
        competitors=[
            Competitor(
                name="Gimnasio ficticio",
                evidences=[evidence.model_copy(deep=True)],
            )
        ],
    )

    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Existe una cuota mensual documentada.",
                kind="fact",
                evidence_ids=["price_1"],
            )
        ],
        limitations=["Datos ficticios para pruebas."],
    )

    return draft, research


def test_unchanged_research_copy_can_use_review():
    """Una copia con los mismos datos conserva una revisión válida."""
    draft, research = make_case()
    review = run_basic_review(draft, research)

    route = choose_review_route_for_context(
        review,
        draft,
        research.model_copy(deep=True),
        revision_count=0,
    )

    assert review.research_fingerprint
    assert route == "pending_review"


@pytest.mark.parametrize(
    "changed_part",
    ["price", "source", "competitor_evidence", "limitations"],
)
def test_research_change_invalidates_review(changed_part):
    """Los cambios en datos o procedencia invalidan la revisión."""
    draft, research = make_case()
    review = run_basic_review(draft, research)

    if changed_part == "price":
        research.evidences[0].value = 50
    elif changed_part == "source":
        research.evidences[0].source_url = (
            "https://example.com/otra-fuente"
        )
    elif changed_part == "competitor_evidence":
        research.competitors[0].evidences[0].value = 50
    else:
        research.evidences[0].limitations = (
            "Precio sujeto a permanencia."
        )

    with pytest.raises(ValueError, match="investigación cambió"):
        choose_review_route_for_context(
            review,
            draft,
            research,
            revision_count=0,
        )


def test_review_without_research_fingerprint_is_rejected():
    """Una revisión antigua sin huella debe repetirse."""
    draft, research = make_case()
    review = run_basic_review(draft, research)
    old_review = replace(review, research_fingerprint="")

    with pytest.raises(ValueError, match="no tiene huella"):
        choose_review_route_for_context(
            old_review,
            draft,
            research,
            revision_count=0,
        )


def test_new_review_uses_updated_research():
    """Una nueva revisión detecta una fuente que se ha eliminado."""
    draft, research = make_case()

    research.evidences[0].source_url = None
    research.competitors[0].evidences[0].source_url = None

    new_review = run_basic_review(draft, research)

    route = choose_review_route_for_context(
        new_review,
        draft,
        research,
        revision_count=0,
    )

    assert route == "revise_research"
    assert any(
        issue.code == "evidence_without_source"
        for issue in new_review.issues
    )


def test_context_route_also_rejects_changed_draft():
    """El control de investigación no sustituye el del borrador."""
    draft, research = make_case()
    review = run_basic_review(draft, research)

    draft.sections.append("Resultados\nContenido añadido.")

    with pytest.raises(ValueError, match="contenido cambió"):
        choose_review_route_for_context(
            review,
            draft,
            research,
            revision_count=0,
        )