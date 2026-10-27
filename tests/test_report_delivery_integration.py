"""Integración del redactor, la revisión básica y la entrega.

Usa datos ficticios y una aprobación simulada de prueba.
No ejecuta Groq ni representa una decisión humana real.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.automation.delivery import export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.markdown_renderer import render_report_markdown
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchBrief, ResearchResult


def test_research_draft_review_and_delivery(tmp_path):
    """Entrega el mismo borrador generado y revisado, sin modificarlo."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="Zona ficticia de prueba",
        questions=["¿Qué tarifas están documentadas?"],
    )

    # Fuente ficticia: no se consulta y no representa datos reales.
    evidence = Evidence(
        evidence_id="test_monthly_price",
        claim="La cuota ficticia de prueba es de 40 EUR al mes.",
        value=40,
        unit="EUR",
        frequency="monthly",
        source_url="https://example.com/tarifa-de-prueba",
        limitations="Dato ficticio utilizado solo en esta prueba.",
    )
    research = ResearchResult(
        evidences=[evidence],
        search_performed="Datos preparados para una prueba sin Internet.",
    )

    # Generamos una sola vez y conservamos su identidad y contenido.
    draft = build_report(brief, research)
    fingerprint = calculate_draft_fingerprint(draft)
    preview = render_report_markdown(draft)

    # Evitamos que el recorrido pase con un borrador sin afirmaciones.
    assert len(draft.claims) == 1
    assert draft.claims[0].evidence_ids == [evidence.evidence_id]
    assert evidence.claim in preview

    # La revisión real comprueba el borrador generado.
    review = run_basic_review(draft, research)

    assert review.issues == ()
    # Comprueba que la revisión corresponde a los datos actuales.
    route = choose_review_route_for_context(
        review,
        draft,
        research,
        revision_count=0,
    )
    assert route == "pending_review"
    assert review.draft_id == draft.draft_id
    assert review.draft_version == draft.version
    assert review.draft_fingerprint == fingerprint

    # Solo para esta prueba: simula el registro que crearía el
    # controlador después de recibir una decisión humana explícita.
    approval = ApprovalRecord(
        run_id="report-integration-test",
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=fingerprint,
        approved=True,
        actions=(
            "export_markdown",
            "export_pdf",
            "update_tracking_csv",
        ),
        decided_at=datetime.now(timezone.utc),
    )

    tracking_path = tmp_path / "tracking.csv"

    # Se usan el coordinador y los exportadores reales.
    result = export_approved_report(
        draft,
        approval,
        run_id=approval.run_id,
        output_dir=tmp_path / "reports",
        csv_path=tracking_path,
    )

    assert result.complete
    assert result.failed_actions == ()
    assert result.errors == ()

    # Los entregables pertenecen al borrador revisado.
    assert result.draft_id == review.draft_id
    assert result.draft_version == review.draft_version
    assert result.draft_fingerprint == review.draft_fingerprint

    markdown_path = Path(result.markdown_path)
    pdf_path = Path(result.pdf_path)

    assert evidence.claim in markdown_path.read_text(encoding="utf-8")
    assert pdf_path.read_bytes().startswith(b"%PDF-")
    assert Path(result.tracking_path) == tracking_path

    # El CSV identifica la misma entrega y sus dos formatos.
    with tracking_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))

    assert len(rows) == 1
    assert rows[0]["run_id"] == approval.run_id
    assert rows[0]["draft_id"] == draft.draft_id
    assert rows[0]["draft_fingerprint"] == fingerprint
    assert rows[0]["status"] == "complete"
    assert rows[0]["markdown_path"] == result.markdown_path
    assert rows[0]["pdf_path"] == result.pdf_path

    # Mostrar, revisar y exportar no deben alterar el borrador.
    assert calculate_draft_fingerprint(draft) == fingerprint