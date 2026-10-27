"""Comprueba que las cifras forman parte del borrador y su huella."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.automation.exporter import (
    calculate_draft_fingerprint,
    validate_export_approval,
)
from src.automation.models import ApprovalRecord
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.models import ReportClaim, ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchResult


def make_case():
    """Prepara un informe ficticio con una cifra estructurada."""
    research = ResearchResult(
        evidences=[
            Evidence(
                evidence_id="demo_price",
                claim="La cuota mensual ficticia es de 45 euros.",
                value=45,
                unit="EUR",
                frequency="monthly",
                source_url="https://example.com/precios",
            )
        ]
    )

    draft = ReportDraft(
        title="Informe ficticio",
        study_area="Zona de prueba",
        claims=[
            ReportClaim(
                claim_id="price_claim",
                text="La cuota mensual ficticia es de 45 euros.",
                kind="fact",
                evidence_ids=["demo_price"],
                metric_id="demo.monthly_price",
                reported_value=45.0,
                reported_unit="EUR/month",
            )
        ],
    )

    return draft, research


def test_drafts_have_independent_metric_lists():
    """Añadir cifras a un informe no modifica otro."""
    first = ReportDraft(title="A", study_area="Prueba")
    second = ReportDraft(title="B", study_area="Prueba")
    example, _ = make_case()

    first.claims.append(example.claims[0])

    assert second.claims == []


def test_fingerprint_includes_claim_metrics_and_preserves_draft():
    """La huella admite las cifras y no modifica el informe."""
    draft, _ = make_case()
    original = deepcopy(draft)

    fingerprint = calculate_draft_fingerprint(draft)

    assert fingerprint
    assert fingerprint == calculate_draft_fingerprint(original)
    assert draft == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("reported_value", 50.0),
        ("reported_unit", "EUR/year"),
        ("metric_id", "another.metric"),
        ("claim_id", "another_claim"),
    ],
)
def test_metric_change_invalidates_review(field, value):
    """Cambiar cualquier vínculo o valor invalida la revisión."""
    draft, research = make_case()
    review = run_basic_review(draft, research)

    setattr(draft.claims[0], field, value)

    with pytest.raises(ValueError, match="contenido cambió"):
        choose_review_route_for_context(
            review,
            draft,
            research,
            revision_count=0,
        )


def test_metric_change_invalidates_export_approval():
    """Una cifra modificada no conserva la autorización anterior."""
    draft, _ = make_case()

    # Aprobación simulada exclusivamente para esta prueba.
    approval = ApprovalRecord(
        run_id="test-numeric-draft",
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved=True,
        actions=("export_markdown",),
        decided_at=datetime.now(timezone.utc),
    )

    draft.claims[0].reported_value = 50.0

    with pytest.raises(ValueError, match="contenido cambió"):
        validate_export_approval(
            draft,
            approval,
            approval.run_id,
            "export_markdown",
        )