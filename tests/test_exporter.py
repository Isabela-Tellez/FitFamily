"""Pruebas de la exportación controlada de informes."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.automation.exporter import (
    calculate_draft_fingerprint,
    export_markdown,
    validate_export_approval,
)
from src.automation.models import ApprovalRecord
from src.reporting.markdown_renderer import render_report_markdown
from src.reporting.models import ReportDraft


def test_same_draft_has_same_fingerprint():
    """Consultar la huella no modifica el borrador."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nEstudiar la competencia."],
    )
    original = deepcopy(draft)

    first = calculate_draft_fingerprint(draft)
    second = calculate_draft_fingerprint(draft)

    assert first == second
    assert draft == original


def test_modified_content_changes_fingerprint():
    """Un cambio de contenido se detecta aunque no cambie la versión."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Tarifas\nCuota mensual de 45 euros."],
    )
    previous_fingerprint = calculate_draft_fingerprint(draft)

    draft.sections = ["Tarifas\nCuota mensual de 50 euros."]

    assert draft.version == 1
    assert calculate_draft_fingerprint(draft) != previous_fingerprint


def test_copy_of_draft_has_same_fingerprint():
    """Una copia con los mismos datos conserva la huella."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    copied_draft = deepcopy(draft)

    assert (
        calculate_draft_fingerprint(draft)
        == calculate_draft_fingerprint(copied_draft)
    )

def make_approved_record(draft):
    """Crea una aprobación ficticia para las pruebas."""
    return ApprovalRecord(
        run_id="run_test",
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        approved=True,
        actions=("export_markdown",),
        decided_at=datetime.now(timezone.utc),
    )


def test_valid_approval_is_accepted():
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    approval = make_approved_record(draft)

    validate_export_approval(
        draft, approval, "run_test", "export_markdown"
    )


def test_missing_approval_is_rejected():
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )

    with pytest.raises(ValueError, match="Falta la aprobación"):
        validate_export_approval(
            draft, None, "run_test", "export_markdown"
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"approved": False}, "no está aprobada"),
        ({"run_id": "another_run"}, "otra ejecución"),
        ({"draft_id": "another_draft"}, "otro borrador"),
        ({"draft_version": 99}, "otra versión"),
        ({"actions": ("export_pdf",)}, "no está autorizada"),
        (
            {"decided_at": datetime(2026, 1, 1)},
            "zona horaria",
        ),
    ],
)
def test_incompatible_approval_is_rejected(changes, message):
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    approval = replace(make_approved_record(draft), **changes)

    with pytest.raises(ValueError, match=message):
        validate_export_approval(
            draft, approval, "run_test", "export_markdown"
        )


def test_changed_content_invalidates_approval():
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Tarifa publicada: 45 euros."],
    )
    approval = make_approved_record(draft)

    # Cambiamos el informe después de la aprobación ficticia.
    draft.sections = ["Tarifa publicada: 50 euros."]

    with pytest.raises(ValueError, match="contenido cambió"):
        validate_export_approval(
            draft, approval, "run_test", "export_markdown"
        )

def test_export_markdown_creates_approved_file(tmp_path):
    """El archivo conserva el Markdown del borrador aprobado."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nEstudiar la competencia."],
    )
    approval = make_approved_record(draft)

    path = export_markdown(
        draft, approval, "run_test", tmp_path
    )

    assert path.is_file()
    assert path.parent == tmp_path.resolve()
    assert path.read_text(encoding="utf-8") == (
        render_report_markdown(draft)
    )


def test_repeated_export_does_not_create_duplicates(tmp_path):
    """Repetir la misma exportación devuelve el mismo archivo."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    approval = make_approved_record(draft)

    first = export_markdown(
        draft, approval, "run_test", tmp_path
    )
    second = export_markdown(
        draft, approval, "run_test", tmp_path
    )

    assert first == second
    assert len(list(tmp_path.glob("*.md"))) == 1


def test_export_without_approval_creates_nothing(tmp_path):
    """Una aprobación ausente impide crear incluso la carpeta."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    output_dir = tmp_path / "reports"

    with pytest.raises(ValueError, match="Falta la aprobación"):
        export_markdown(
            draft, None, "run_test", output_dir
        )

    assert not output_dir.exists()


def test_existing_different_file_is_not_overwritten(tmp_path):
    """Un archivo alterado se conserva y se comunica el conflicto."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
    )
    approval = make_approved_record(draft)

    path = export_markdown(
        draft, approval, "run_test", tmp_path
    )
    path.write_text("Contenido diferente.", encoding="utf-8")

    with pytest.raises(ValueError, match="exportación diferente"):
        export_markdown(
            draft, approval, "run_test", tmp_path
        )

    assert path.read_text(encoding="utf-8") == "Contenido diferente."

def test_failed_publication_can_be_retried(tmp_path):
    """Un fallo no deja archivos parciales y permite reintentar."""
    from unittest.mock import patch

    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        sections=["Objetivo\nEstudiar la competencia."],
    )
    approval = make_approved_record(draft)

    # Simulamos un fallo al publicar el archivo ya escrito.
    with patch(
        "src.automation.exporter.os.link",
        side_effect=OSError("Fallo simulado"),
    ):
        with pytest.raises(OSError, match="Fallo simulado"):
            export_markdown(
                draft, approval, "run_test", tmp_path
            )

    # No debe quedar ni el informe final ni el temporal.
    assert list(tmp_path.iterdir()) == []

    # Al desaparecer el fallo, la misma operación funciona.
    path = export_markdown(
        draft, approval, "run_test", tmp_path
    )

    assert path.read_text(encoding="utf-8") == (
        render_report_markdown(draft)
    )
    assert len(list(tmp_path.iterdir())) == 1