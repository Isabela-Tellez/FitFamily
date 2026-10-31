"""Cierre de Persona 3 con cálculos reales y decisión simulada solo de prueba."""

import csv
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.analysis.calculation_adapter import metric_from_break_even, metric_context_notes
from src.analysis.economic_calculations import create_break_even_calculation
from src.analysis.scenarios import create_economic_scenario
from src.automation.delivery import export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult
from src.ui.report_preview import render_report_preview


@pytest.fixture
def reviewed_report():
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca", location="Madrid",
        study_area="Zona ficticia de prueba",
    )
    research = ResearchResult(notes="Datos sintéticos; no representan un estudio real.")
    scenario = create_economic_scenario(
        "intermediate", 100, 50, 1000, 10,
        assumptions=["Todos los parámetros económicos son hipotéticos de prueba."],
    )
    calculation = create_break_even_calculation(
        1000, 50, 10, limitations=["No demuestra demanda ni viabilidad real."],
    )
    metrics = [metric_from_break_even(scenario, calculation)]
    draft = build_report(brief, research, calculated_metrics=metrics)
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    assert review.issues == ()
    assert choose_review_route_for_context(
        review, draft, research, revision_count=0, calculated_metrics=metrics,
    ) == "pending_review"
    return draft, metrics, review


def simulated_approval(preview):
    """Solo para esta prueba; no representa una aprobación humana real."""
    return ApprovalRecord(
        run_id="synthetic-reporting-close", draft_id=preview.draft_id,
        draft_version=preview.draft_version,
        draft_fingerprint=preview.draft_fingerprint,
        approved=True, actions=preview.delivery_actions,
        decided_at=datetime(2026, 10, 31, tzinfo=timezone.utc),
    )


def test_preview_keeps_numeric_traceability_and_creates_no_files(
    reviewed_report, tmp_path, monkeypatch,
):
    draft, metrics, _ = reviewed_report
    before = deepcopy(draft)
    monkeypatch.chdir(tmp_path)
    preview = render_report_preview(draft)

    assert "25 clientes" in preview.markdown
    assert metrics[0].metric_id in preview.markdown
    assert "**Valor declarado:** 25.0" in preview.markdown
    assert "**Unidad:** clients" in preview.markdown
    assert "pendiente de revisión y aprobación" in preview.markdown
    assert all(note in preview.markdown for note in metric_context_notes(metrics[0]))
    assert preview.draft_fingerprint == calculate_draft_fingerprint(draft)
    assert preview.delivery_actions == ("export_markdown", "export_pdf", "update_tracking_csv")
    assert draft == before
    assert list(tmp_path.iterdir()) == []


def test_preview_actions_do_not_authorize_delivery(reviewed_report, tmp_path):
    draft, _, _ = reviewed_report
    preview = render_report_preview(draft)
    assert preview.delivery_actions
    with pytest.raises(ValueError, match="aprobación"):
        export_approved_report(
            draft, None, "not-approved", tmp_path / "reports",
            csv_path=tmp_path / "tracking.csv",
        )
    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / "tracking.csv").exists()


def test_numeric_preview_review_delivery_and_retry_keep_the_same_report(
    reviewed_report, tmp_path,
):
    draft, _, review = reviewed_report
    preview = render_report_preview(draft)
    approval = simulated_approval(preview)
    options = dict(
        run_id=approval.run_id, output_dir=tmp_path / "reports",
        csv_path=tmp_path / "tracking.csv",
    )
    result = export_approved_report(draft, approval, **options)
    repeated = export_approved_report(draft, approval, previous_result=result, **options)
    assert result.complete and repeated.complete
    assert result.markdown_path == repeated.markdown_path
    assert result.pdf_path == repeated.pdf_path
    assert result.draft_fingerprint == review.draft_fingerprint == preview.draft_fingerprint
    assert calculate_draft_fingerprint(draft) == preview.draft_fingerprint
    markdown = Path(result.markdown_path).read_text(encoding="utf-8")
    assert "25 clientes" in markdown
    assert "**Valor declarado:** 25.0" in markdown
    assert "aprobado para exportación" in markdown
    assert Path(result.pdf_path).read_bytes().startswith(b"%PDF-")
    assert len(list((tmp_path / "reports").glob("*.md"))) == 1
    assert len(list((tmp_path / "reports").glob("*.pdf"))) == 1
    with Path(result.tracking_path).open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1 and rows[0]["status"] == "complete"
    assert rows[0]["draft_fingerprint"] == preview.draft_fingerprint
    assert rows[0]["markdown_path"] == result.markdown_path
    assert rows[0]["pdf_path"] == result.pdf_path


@pytest.mark.parametrize("field,value", [
    ("reported_value", 26),
    ("text", "Texto modificado después de mostrar la vista previa."),
])
def test_change_after_preview_invalidates_old_delivery_approval(
    reviewed_report, tmp_path, field, value,
):
    draft, _, _ = reviewed_report
    preview = render_report_preview(draft)
    approval = simulated_approval(preview)
    numeric_claim = next(c for c in draft.claims if c.metric_id)
    setattr(numeric_claim, field, value)
    with pytest.raises(ValueError, match="contenido cambió"):
        export_approved_report(
            draft, approval, approval.run_id, tmp_path / "reports",
            csv_path=tmp_path / "tracking.csv",
        )
    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / "tracking.csv").exists()
