"""Pruebas de generación y exportación PDF sin llamadas al LLM."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from src.automation.exporter import (
    calculate_draft_fingerprint,
    export_pdf,
)
from src.automation.models import ApprovalRecord
from src.reporting.models import ReportDraft
from src.reporting.pdf_renderer import render_report_pdf


@pytest.fixture
def draft():
    """Borrador pequeño con caracteres habituales en español."""
    return ReportDraft(
        title="Investigación de FitFamily",
        study_area="El Cañaveral",
        sections=["Datos de prueba\nCuota ficticia: 45 € al mes."],
        sources=["https://example.com"],
        limitations=["Datos ficticios para pruebas."],
    )


def make_approval(draft, actions=("export_pdf",)):
    """Simula la aprobación que proporcionaría el controlador."""
    return ApprovalRecord(
        run_id="test-run",
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved=True,
        actions=actions,
        decided_at=datetime.now(timezone.utc),
    )


def test_pdf_is_repeatable_and_preserves_draft(draft):
    """La misma entrada produce los mismos bytes sin cambiar el borrador."""
    original = deepcopy(draft)

    first = render_report_pdf(draft, approved=True)
    second = render_report_pdf(draft, approved=True)

    assert first.startswith(b"%PDF-")
    assert first == second
    assert draft == original


def test_pdf_export_requires_approval(draft, tmp_path, monkeypatch):
    """Sin aprobación no debe generar el PDF ni crear su carpeta."""
    def unexpected_render(*args, **kwargs):
        pytest.fail("No debe generar un PDF sin aprobación.")

    monkeypatch.setattr(
        "src.reporting.pdf_renderer.render_report_pdf",
        unexpected_render,
    )
    destination = tmp_path / "not-created"

    with pytest.raises(ValueError, match="aprobación"):
        export_pdf(draft, None, "test-run", destination)

    assert not destination.exists()


def test_markdown_permission_does_not_allow_pdf(draft, tmp_path):
    """Cada formato necesita su propia acción autorizada."""
    approval = make_approval(draft, actions=("export_markdown",))
    destination = tmp_path / "not-created"

    with pytest.raises(ValueError, match="autorizada"):
        export_pdf(draft, approval, "test-run", destination)

    assert not destination.exists()


def test_modified_draft_cannot_be_exported(draft, tmp_path):
    """Una aprobación anterior deja de servir si cambia el contenido."""
    approval = make_approval(draft)
    draft.sections.append("Cambio posterior\nContenido nuevo.")
    destination = tmp_path / "not-created"

    with pytest.raises(ValueError, match="contenido cambió"):
        export_pdf(draft, approval, "test-run", destination)

    assert not destination.exists()


def test_pdf_export_can_be_repeated(draft, tmp_path, monkeypatch):
    """Repetir una exportación devuelve el mismo archivo aprobado."""
    calls = []

    def fake_render(received_draft, *, approved=False):
        calls.append((received_draft, approved))
        return b"%PDF-test-content"

    # Aquí aislamos la publicación del archivo del diseño del PDF.
    monkeypatch.setattr(
        "src.reporting.pdf_renderer.render_report_pdf",
        fake_render,
    )
    approval = make_approval(draft)

    first = export_pdf(draft, approval, "test-run", tmp_path)
    second = export_pdf(draft, approval, "test-run", tmp_path)

    assert first == second
    assert first.suffix == ".pdf"
    assert first.read_bytes() == b"%PDF-test-content"
    assert len(list(tmp_path.glob("*.pdf"))) == 1
    assert not list(tmp_path.glob(".report_*.tmp"))
    assert calls == [(draft, True), (draft, True)]


def test_pdf_export_never_overwrites_different_content(
    draft, tmp_path, monkeypatch
):
    """Un archivo distinto en el destino debe conservarse."""
    monkeypatch.setattr(
        "src.reporting.pdf_renderer.render_report_pdf",
        lambda *args, **kwargs: b"%PDF-test-content",
    )
    approval = make_approval(draft)
    target = export_pdf(draft, approval, "test-run", tmp_path)

    target.write_bytes(b"contenido diferente")

    with pytest.raises(ValueError, match="exportación diferente"):
        export_pdf(draft, approval, "test-run", tmp_path)

    assert target.read_bytes() == b"contenido diferente"
    assert not list(tmp_path.glob(".report_*.tmp"))

def test_pdf_includes_metric_reference_without_changing_draft(monkeypatch):
    """Incluye los campos numéricos en los párrafos del PDF."""
    from copy import deepcopy

    from reportlab.platypus import Paragraph, SimpleDocTemplate

    from src.reporting.models import ReportClaim, ReportDraft
    from src.reporting.pdf_renderer import render_report_pdf

    draft = ReportDraft(
        title="Informe ficticio",
        study_area="Zona de prueba",
        claims=[
            ReportClaim(
                claim_id="claim_break_even",
                text="Bajo estos supuestos se necesitan 25 clientes.",
                kind="inference",
                metric_id="scenario_intermediate.break_even_clients",
                reported_value=25.0,
                reported_unit="clients",
            )
        ],
    )
    original = deepcopy(draft)
    paragraphs = []

    # Observamos los párrafos sin sustituir la generación real.
    real_build = SimpleDocTemplate.build

    def capture_and_build(document, flowables, *args, **kwargs):
        paragraphs.extend(
            item.getPlainText()
            for item in flowables
            if isinstance(item, Paragraph)
        )
        return real_build(document, flowables, *args, **kwargs)

    monkeypatch.setattr(SimpleDocTemplate, "build", capture_and_build)

    content = render_report_pdf(draft)

    assert content.startswith(b"%PDF-")
    assert (
        "Métrica: scenario_intermediate.break_even_clients"
        in paragraphs
    )
    assert "Valor declarado: 25.0" in paragraphs
    assert "Unidad: clients" in paragraphs
    assert "Bajo estos supuestos se necesitan 25 clientes." in paragraphs
    assert draft == original