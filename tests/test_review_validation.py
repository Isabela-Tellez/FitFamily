"""Pruebas con datos ficticios de la validación de referencias."""

from src.reporting.models import ReportClaim, ReportDraft
from src.review.validation import validate_claim_references
from src.schemas import Competitor, Evidence, ResearchResult


def test_accepts_reference_from_competitor():
    """Reconoce también evidencias guardadas dentro de un competidor."""
    evidence = Evidence(
        evidence_id="test_price_1",
        claim="Cuota mensual de prueba: 45 euros.",
    )
    research = ResearchResult(
        competitors=[
            Competitor(name="Gimnasio ficticio", evidences=[evidence])
        ]
    )
    draft = ReportDraft(
        title="Informe ficticio",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="La cuota mensual de prueba es de 45 euros.",
                kind="fact",
                evidence_ids=["test_price_1"],
            )
        ],
    )

    assert validate_claim_references(draft, research) == []


def test_detects_missing_reference_and_unsupported_fact():
    """Devuelve ambos problemas, aunque estén en el mismo borrador."""
    draft = ReportDraft(
        title="Informe ficticio",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Afirmación con una referencia inexistente.",
                kind="fact",
                evidence_ids=["missing_1"],
            ),
            ReportClaim(
                claim_id="claim_2",
                text="Afirmación presentada como hecho sin respaldo.",
                kind="fact",
            ),
        ],
    )

    issues = validate_claim_references(draft, ResearchResult())

    assert len(issues) == 2
    assert {issue["code"] for issue in issues} == {
        "missing_evidence",
        "fact_without_evidence",
    }


def test_detects_duplicate_claim_identifiers():
    """Dos afirmaciones diferentes no deben compartir identificador."""
    draft = ReportDraft(
        title="Informe ficticio",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="same_id",
                text="Primera hipótesis ficticia.",
                kind="assumption",
            ),
            ReportClaim(
                claim_id="same_id",
                text="Segunda hipótesis ficticia.",
                kind="assumption",
            ),
        ],
    )

    issues = validate_claim_references(draft, ResearchResult())

    assert len(issues) == 1
    assert issues[0]["code"] == "duplicate_claim_id"
    assert issues[0]["reference_id"] == "same_id"


def test_does_not_require_evidence_for_explicit_assumption():
    """Una hipótesis identificada como tal no se trata como un hecho."""
    draft = ReportDraft(
        title="Informe ficticio",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="assumption_1",
                text="Suponemos una cuota de 45 euros para el escenario.",
                kind="assumption",
            )
        ],
    )

    assert validate_claim_references(draft, ResearchResult()) == []