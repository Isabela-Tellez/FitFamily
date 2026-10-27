"""Pruebas del resultado conjunto de revisión."""

from copy import deepcopy

from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchResult


def make_draft(evidence_ids: list[str]) -> ReportDraft:
    """Crea un borrador ficticio para las pruebas."""
    return ReportDraft(
        title="Informe ficticio",
        study_area="El Cañaveral",
        sections=["Resultados\nDato ficticio."],
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Dato ficticio.",
                kind="fact",
                evidence_ids=evidence_ids,
            )
        ],
    )


def test_clean_basic_review_does_not_accept_full_report():
    """Pasar estas comprobaciones no aprueba el informe completo."""
    draft = make_draft(["evidence_1"])
    research = ResearchResult(
        evidences=[
            Evidence(
                evidence_id="evidence_1",
                claim="Dato ficticio.",
                source_url="https://example.org",
            )
        ]
    )

    result = run_basic_review(draft, research)

    assert result.status == "pending_review"
    assert result.issues == ()
    assert result.draft_id == draft.draft_id
    assert result.draft_version == draft.version


def test_missing_reference_requires_writing_correction():
    draft = make_draft(["missing_1"])

    result = run_basic_review(draft, ResearchResult())

    assert result.status == "needs_revision"
    issue = next(
        item for item in result.issues
        if item.code == "missing_evidence"
    )
    assert issue.reference_id == "missing_1"
    assert issue.severity == "error"
    assert issue.correction_stage == "writing"


def test_missing_source_requires_research_correction():
    draft = make_draft(["evidence_1"])
    research = ResearchResult(
        evidences=[
            Evidence(
                evidence_id="evidence_1",
                claim="Dato ficticio sin procedencia.",
            )
        ]
    )

    result = run_basic_review(draft, research)

    assert result.status == "needs_revision"
    issue = next(
        item for item in result.issues
        if item.code == "evidence_without_source"
    )
    assert issue.correction_stage == "research"


def test_review_preserves_inputs_and_identifies_reviewed_content():
    draft = make_draft([])
    research = ResearchResult()
    original_draft = deepcopy(draft)
    original_research = research.model_copy(deep=True)

    result = run_basic_review(draft, research)

    assert draft == original_draft
    assert research == original_research
    assert result.draft_fingerprint == calculate_draft_fingerprint(draft)
    assert result.checks_performed == (
        "claim_references",
        "evidence_quality",
        "claim_structure",
        "numeric_text",
    )

    # Aunque alguien olvide incrementar la versión, la huella
    # permite detectar que el contenido ya no es el revisado.
    draft.sections.append("Contenido añadido después de revisar.")

    assert result.draft_fingerprint != calculate_draft_fingerprint(draft)