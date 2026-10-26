"""Pruebas del seguimiento de entregas, sin llamadas externas."""

import csv
from datetime import datetime, timezone

import pytest

from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.automation.tracking import update_tracking_csv
from src.reporting.models import ReportDraft


@pytest.fixture
def delivery(tmp_path):
    """Prepara una entrega ficticia y su aprobación estable."""
    draft = ReportDraft(
        title="Estudio de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nComprobar el seguimiento."],
    )
    approval = ApprovalRecord(
        run_id="tracking-test",
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

    # Estos archivos simulan las rutas devueltas por los exportadores.
    # Aquí probamos el seguimiento, no el contenido de los informes.
    markdown = tmp_path / "report.md"
    markdown.write_text("# Informe de prueba", encoding="utf-8")
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-test")

    return draft, approval, markdown, pdf


def read_rows(path):
    """Lee las filas usando el mismo formato de texto del seguimiento."""
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_tracking_requires_approval(delivery, tmp_path):
    """Sin aprobación no debe crear ni la carpeta del CSV."""
    draft, _, markdown, _ = delivery
    target = tmp_path / "not-created" / "tracking.csv"

    with pytest.raises(ValueError, match="aprobación"):
        update_tracking_csv(
            draft,
            None,
            "tracking-test",
            target,
            markdown_path=markdown,
        )

    assert not target.parent.exists()


def test_tracking_requires_its_own_permission(delivery, tmp_path):
    """Autorizar informes no autoriza actualizar el seguimiento."""
    draft, approval, markdown, _ = delivery
    from dataclasses import replace

    approval = replace(approval, actions=("export_markdown",))
    target = tmp_path / "tracking.csv"

    with pytest.raises(ValueError, match="autorizada"):
        update_tracking_csv(
            draft,
            approval,
            approval.run_id,
            target,
            markdown_path=markdown,
        )

    assert not target.exists()


def test_tracking_completes_same_row_on_retry(delivery, tmp_path):
    """El segundo intento añade PDF sin perder Markdown ni duplicar."""
    draft, approval, markdown, pdf = delivery
    target = tmp_path / "tracking.csv"

    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        markdown_path=markdown,
    )
    rows = read_rows(target)
    assert len(rows) == 1
    assert rows[0]["status"] == "partial"

    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        pdf_path=pdf,
    )
    rows = read_rows(target)

    assert len(rows) == 1
    assert rows[0]["status"] == "complete"
    assert rows[0]["markdown_path"] == str(markdown.resolve())
    assert rows[0]["pdf_path"] == str(pdf.resolve())

    # Repetir la entrega completa conserva exactamente el archivo.
    previous = target.read_bytes()
    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        markdown_path=markdown,
        pdf_path=pdf,
    )
    assert target.read_bytes() == previous


def test_tracking_preserves_csv_after_write_failure(
    delivery, tmp_path, monkeypatch
):
    """Si falla la publicación, se conserva la entrega parcial."""
    draft, approval, markdown, pdf = delivery
    target = tmp_path / "tracking.csv"

    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        markdown_path=markdown,
    )
    previous = target.read_bytes()

    def fail_replace(*args, **kwargs):
        raise OSError("Fallo simulado de publicación")

    # El parche solo dura durante este intento.
    with monkeypatch.context() as patch:
        patch.setattr(
            "src.automation.tracking.os.replace",
            fail_replace,
        )
        with pytest.raises(OSError, match="Fallo simulado"):
            update_tracking_csv(
                draft,
                approval,
                approval.run_id,
                target,
                pdf_path=pdf,
            )

    assert target.read_bytes() == previous
    assert not target.with_name("tracking.csv.lock").exists()
    assert not list(tmp_path.glob(".tracking_*.tmp"))

    # Al recuperar la escritura, completamos la misma fila.
    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        pdf_path=pdf,
    )
    rows = read_rows(target)
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"


def test_tracking_does_not_remove_another_lock(delivery, tmp_path):
    """Otra actualización en curso impide escribir el CSV."""
    draft, approval, markdown, _ = delivery
    target = tmp_path / "tracking.csv"
    lock = tmp_path / "tracking.csv.lock"
    lock.write_text("otro proceso", encoding="utf-8")

    with pytest.raises(FileExistsError):
        update_tracking_csv(
            draft,
            approval,
            approval.run_id,
            target,
            markdown_path=markdown,
        )

    assert lock.read_text(encoding="utf-8") == "otro proceso"
    assert not target.exists()


def test_tracking_rejects_unrelated_csv(delivery, tmp_path):
    """No reutiliza un CSV de competidores ni pierde sus columnas."""
    draft, approval, markdown, _ = delivery
    target = tmp_path / "tracking.csv"
    target.write_text(
        "gym_name,monthly_price_eur\nEjemplo,45\n",
        encoding="utf-8",
    )
    previous = target.read_bytes()

    with pytest.raises(ValueError, match="columnas"):
        update_tracking_csv(
            draft,
            approval,
            approval.run_id,
            target,
            markdown_path=markdown,
        )

    assert target.read_bytes() == previous
    assert not target.with_name("tracking.csv.lock").exists()

def test_tracking_preserves_other_deliveries(delivery, tmp_path):
    """Una ejecución nueva añade una fila y conserva la anterior."""
    from dataclasses import replace

    draft, approval, markdown, _ = delivery
    target = tmp_path / "tracking.csv"

    update_tracking_csv(
        draft,
        approval,
        approval.run_id,
        target,
        markdown_path=markdown,
    )
    first_row = read_rows(target)[0]

    second_approval = replace(
        approval,
        run_id="second-run",
    )
    update_tracking_csv(
        draft,
        second_approval,
        second_approval.run_id,
        target,
        markdown_path=markdown,
    )

    rows = read_rows(target)
    assert len(rows) == 2
    assert rows[0] == first_row
    assert rows[1]["run_id"] == "second-run"


def test_tracking_rejects_modified_draft(delivery, tmp_path):
    """Modificar el borrador invalida su aprobación para el CSV."""
    draft, approval, markdown, _ = delivery
    target = tmp_path / "tracking.csv"

    draft.sections.append("Cambio posterior\nContenido no aprobado.")

    with pytest.raises(ValueError, match="contenido cambió"):
        update_tracking_csv(
            draft,
            approval,
            approval.run_id,
            target,
            markdown_path=markdown,
        )

    assert not target.exists()