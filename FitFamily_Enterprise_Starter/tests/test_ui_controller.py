"""Regresiones de identidad, revisión y aprobación de la interfaz."""
from dataclasses import replace

import pytest

from src.automation.delivery import ACTION_ORDER
from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.models import ReportDraft
from src.review.models import ReviewIssue
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchResult
from src.ui.controller import create_approval_record, draft_from_state, review_from_state


@pytest.fixture
def review_context():
    research = ResearchResult(evidences=[Evidence(
        evidence_id="evidence-real-shape",
        claim="La fuente publica una tarifa mensual.",
        source_url="https://example.org/pricing",
        snippet="Tarifa publicada en la web consultada.",
    )])
    draft = ReportDraft(
        title="Estudio de mercado",
        study_area="El Cañaveral",
        sections=["Fuentes\nSe ha consultado una fuente."],
    )
    metrics = []
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    return research, draft, metrics, review


def test_approval_uses_real_draft_identity_and_fingerprint(review_context):
    research, draft, metrics, review = review_context
    approval = create_approval_record(
        run_id="run-real-001",
        draft=draft,
        research=research,
        metrics=metrics,
        review=review,
        actions=("export_markdown",),
    )
    assert approval.approved is True
    assert approval.run_id == "run-real-001"
    assert approval.draft_id == draft.draft_id
    assert approval.draft_version == draft.version
    assert approval.draft_fingerprint == calculate_draft_fingerprint(draft)
    assert approval.actions == ("export_markdown",)
    assert approval.decided_at.tzinfo is not None


def test_approval_rejects_changed_draft_after_review(review_context):
    research, draft, metrics, review = review_context
    draft.sections.append("Nueva sección\nContenido nuevo")
    with pytest.raises(ValueError, match="contenido cambió"):
        create_approval_record(
            run_id="run-real-002", draft=draft, research=research,
            metrics=metrics, review=review, actions=("export_markdown",),
        )


def test_approval_rejects_unknown_or_empty_actions(review_context):
    research, draft, metrics, review = review_context
    for actions in ((), ("export_fake",)):
        with pytest.raises(ValueError):
            create_approval_record(
                run_id="run-real-003", draft=draft, research=research,
                metrics=metrics, review=review, actions=actions,
            )


def test_approval_rejects_blocking_review_errors(review_context):
    research, draft, metrics, review = review_context
    blocked = replace(review, issues=(ReviewIssue(
        code="broken_reference", reference_id="claim-1",
        message="Referencia sin respaldo.", severity="error",
        correction_stage="research",
    ),))
    with pytest.raises(ValueError, match="errores bloqueantes"):
        create_approval_record(
            run_id="run-real-004", draft=draft, research=research,
            metrics=metrics, review=blocked, actions=("export_markdown",),
        )


def test_rejection_records_negative_decision_without_export_actions(review_context):
    research, draft, metrics, review = review_context
    decision = create_approval_record(
        run_id="run-real-005", draft=draft, research=research,
        metrics=metrics, review=review, actions=(), approved=False,
    )
    assert decision.approved is False
    assert decision.actions == ()
    assert decision.draft_fingerprint == calculate_draft_fingerprint(draft)


def test_state_reconstruction_restores_claims_and_issues(review_context):
    research, draft, metrics, review = review_context
    draft_dict = {
        "title": draft.title, "study_area": draft.study_area,
        "sections": draft.sections, "sources": draft.sources,
        "limitations": draft.limitations, "draft_id": draft.draft_id,
        "version": draft.version, "claims": [],
    }
    review_dict = {
        "draft_id": review.draft_id,
        "draft_version": review.draft_version,
        "draft_fingerprint": review.draft_fingerprint,
        "issues": [], "checks_performed": list(review.checks_performed),
        "research_fingerprint": review.research_fingerprint,
        "analysis_fingerprint": review.analysis_fingerprint,
    }
    assert draft_from_state(draft_dict) == draft
    assert review_from_state(review_dict) == review
