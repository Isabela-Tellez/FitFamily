"""Pruebas de calidad básica con evidencias ficticias."""

import pytest

from src.reporting.models import ReportClaim, ReportDraft
from src.review.validation import validate_evidence_quality
from src.schemas import Competitor, Evidence, ResearchResult


def make_draft(evidence_ids: list[str]) -> ReportDraft:
    """Construye un borrador ficticio con una afirmación factual."""
    return ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Hecho ficticio utilizado para probar el revisor.",
                kind="fact",
                evidence_ids=evidence_ids,
            )
        ],
    )


@pytest.mark.parametrize("reference", ["", "   "])
def test_detects_empty_reference(reference):
    draft = make_draft([reference])

    issues = validate_evidence_quality(draft, ResearchResult())

    assert len(issues) == 1
    assert issues[0]["code"] == "empty_evidence_reference"
    assert issues[0]["reference_id"] == "claim_1"


@pytest.mark.parametrize("source", [None, "", "   "])
def test_detects_missing_source(source):
    evidence = Evidence(
        evidence_id="test_1",
        claim="Dato ficticio.",
        source_url=source,
    )
    research = ResearchResult(evidences=[evidence])

    issues = validate_evidence_quality(make_draft(["test_1"]), research)

    assert len(issues) == 1
    assert issues[0]["code"] == "evidence_without_source"


@pytest.mark.parametrize(
    "evidence_id, evidence_claim, expected_code",
    [
        (
            "access_attempt_test",
            "Intento fallido de acceso.",
            "failed_access_as_evidence",
        ),
        (
            "source_test",
            "Fuente localizada: ejemplo [rejected] Acceso fallido.",
            "rejected_source_as_evidence",
        ),
    ],
)
def test_detects_failed_or_rejected_source(
    evidence_id, evidence_claim, expected_code
):
    evidence = Evidence(
        evidence_id=evidence_id,
        claim=evidence_claim,
        source_url="https://example.org",
    )
    research = ResearchResult(evidences=[evidence])

    issues = validate_evidence_quality(
        make_draft([evidence_id]), research
    )

    assert len(issues) == 1
    assert issues[0]["code"] == expected_code


def test_accepts_source_from_competitor():
    evidence = Evidence(
        evidence_id="test_1",
        claim="Dato ficticio con procedencia.",
        source_url="https://example.org",
    )
    research = ResearchResult(
        competitors=[
            Competitor(name="Negocio ficticio", evidences=[evidence])
        ]
    )

    assert validate_evidence_quality(
        make_draft(["test_1"]), research
    ) == []


def test_does_not_duplicate_issue_for_shared_evidence():
    evidence = Evidence(
        evidence_id="test_1",
        claim="Dato ficticio sin procedencia.",
    )
    research = ResearchResult(
        evidences=[evidence],
        competitors=[
            Competitor(name="Negocio ficticio", evidences=[evidence])
        ],
    )

    issues = validate_evidence_quality(make_draft(["test_1"]), research)

    assert len(issues) == 1
    assert issues[0]["code"] == "evidence_without_source"


def test_ignores_failed_access_not_cited_by_a_fact():
    evidence = Evidence(
        evidence_id="access_attempt_test",
        claim="Intento fallido conservado para auditoría.",
        source_url="https://example.org",
    )
    research = ResearchResult(evidences=[evidence])
    draft = ReportDraft(
        title="Borrador de prueba",
        study_area="El Cañaveral",
    )

    assert validate_evidence_quality(draft, research) == []