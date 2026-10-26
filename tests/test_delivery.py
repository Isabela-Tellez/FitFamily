"""Pruebas de coordinación de entregas aprobadas."""

import csv
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.automation import delivery
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.reporting.models import ReportDraft


@pytest.fixture
def approved_delivery():
    """Prepara un borrador autorizado para las tres acciones."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nProbar la entrega aprobada."],
    )
    approval = ApprovalRecord(
        run_id="delivery-test",
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved=True,
        actions=(
            "export_markdown",
            "export_pdf",
            "update_tracking_csv",
        ),
        decided_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
    )
    return draft, approval


def read_tracking(path):
    """Lee el seguimiento generado durante una prueba."""
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_delivery_without_approval_creates_nothing(
    approved_delivery, tmp_path
):
    """La coordinación rechaza la entrega antes de crear archivos."""
    draft, _ = approved_delivery
    output = tmp_path / "reports"

    with pytest.raises(ValueError, match="aprobación"):
        delivery.export_approved_report(
            draft,
            None,
            "delivery-test",
            output,
            csv_path=tmp_path / "tracking.csv",
        )

    assert not output.exists()
    assert not (tmp_path / "tracking.csv").exists()


def test_delivery_requires_csv_path_before_exporting(
    approved_delivery, tmp_path, monkeypatch
):
    """Una configuración incompleta no debe dejar entregas a medias."""
    draft, approval = approved_delivery
    markdown_export = Mock()
    monkeypatch.setattr(delivery, "export_markdown", markdown_export)

    with pytest.raises(ValueError, match="ruta del CSV"):
        delivery.export_approved_report(
            draft,
            approval,
            approval.run_id,
            tmp_path / "reports",
        )

    markdown_export.assert_not_called()
    assert not (tmp_path / "reports").exists()


def test_pdf_failure_can_be_retried_without_repeating_markdown(
    approved_delivery, tmp_path, monkeypatch
):
    """Conserva Markdown y completa la misma fila al recuperar el PDF."""
    draft, approval = approved_delivery
    output = tmp_path / "reports"
    tracking = tmp_path / "tracking.csv"

    # Conservamos los exportadores reales para el segundo intento.
    real_markdown = delivery.export_markdown
    real_pdf = delivery.export_pdf
    markdown_export = Mock(wraps=real_markdown)
    pdf_export = Mock(side_effect=OSError("PDF no disponible"))

    monkeypatch.setattr(delivery, "export_markdown", markdown_export)
    monkeypatch.setattr(delivery, "export_pdf", pdf_export)

    first = delivery.export_approved_report(
        draft,
        approval,
        approval.run_id,
        output,
        csv_path=tracking,
    )

    assert not first.complete
    assert first.failed_actions == ("export_pdf",)
    assert first.completed_actions == (
        "export_markdown",
        "update_tracking_csv",
    )
    assert first.errors == (("export_pdf", "PDF no disponible"),)
    assert read_tracking(tracking)[0]["status"] == "partial"

    # Recuperamos el PDF y reintentamos conservando el resultado anterior.
    pdf_export = Mock(wraps=real_pdf)
    monkeypatch.setattr(delivery, "export_pdf", pdf_export)

    second = delivery.export_approved_report(
        draft,
        approval,
        approval.run_id,
        output,
        csv_path=tracking,
        previous_result=first,
    )

    assert second.complete
    assert second.failed_actions == ()
    assert second.errors == ()
    assert second.markdown_path == first.markdown_path
    markdown_export.assert_called_once()
    pdf_export.assert_called_once()

    rows = read_tracking(tracking)
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"


def test_csv_failure_retries_tracking_without_repeating_reports(
    approved_delivery, tmp_path, monkeypatch
):
    """Tener los informes no equivale a completar también el CSV."""
    draft, approval = approved_delivery
    output = tmp_path / "reports"
    tracking = tmp_path / "tracking.csv"

    markdown_export = Mock(wraps=delivery.export_markdown)
    pdf_export = Mock(wraps=delivery.export_pdf)
    real_tracking = delivery.update_tracking_csv

    monkeypatch.setattr(delivery, "export_markdown", markdown_export)
    monkeypatch.setattr(delivery, "export_pdf", pdf_export)
    monkeypatch.setattr(
        delivery,
        "update_tracking_csv",
        Mock(side_effect=OSError("CSV no disponible")),
    )

    first = delivery.export_approved_report(
        draft,
        approval,
        approval.run_id,
        output,
        csv_path=tracking,
    )

    assert not first.complete
    assert first.failed_actions == ("update_tracking_csv",)
    assert first.markdown_path
    assert first.pdf_path
    assert not tracking.exists()

    # Una vez recuperado el CSV, solo falta registrar los informes.
    monkeypatch.setattr(delivery, "update_tracking_csv", real_tracking)

    second = delivery.export_approved_report(
        draft,
        approval,
        approval.run_id,
        output,
        csv_path=tracking,
        previous_result=first,
    )

    assert second.complete
    markdown_export.assert_called_once()
    pdf_export.assert_called_once()
    assert len(read_tracking(tracking)) == 1


def test_delivery_rejects_previous_result_from_another_run(
    approved_delivery, tmp_path, monkeypatch
):
    """No reutiliza archivos de una ejecución distinta."""
    from dataclasses import replace

    draft, approval = approved_delivery
    tracking = tmp_path / "tracking.csv"

    first = delivery.export_approved_report(
        draft,
        approval,
        approval.run_id,
        tmp_path / "reports",
        csv_path=tracking,
    )
    unrelated = replace(first, run_id="another-run")
    markdown_export = Mock()
    monkeypatch.setattr(delivery, "export_markdown", markdown_export)

    with pytest.raises(ValueError, match="resultado anterior"):
        delivery.export_approved_report(
            draft,
            approval,
            approval.run_id,
            tmp_path / "reports",
            csv_path=tracking,
            previous_result=unrelated,
        )

    markdown_export.assert_not_called()