"""Vista previa reutilizable: datos para la UI, sin aprobar ni escribir archivos."""

from dataclasses import dataclass

from src.automation.delivery import ACTION_ORDER
from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.markdown_renderer import render_report_markdown
from src.reporting.models import ReportDraft


@dataclass(frozen=True)
class ReportPreview:
    """Instantánea que la interfaz puede mostrar antes de pedir una decisión.

    delivery_actions son opciones para seleccionar, nunca autorizaciones.
    El controlador debe recibir una decisión humana y emitir ApprovalRecord.
    """

    markdown: str
    draft_id: str
    draft_version: int
    draft_fingerprint: str
    delivery_actions: tuple[str, ...]


def render_report_preview(draft: ReportDraft) -> ReportPreview:
    """Prepara el texto y la identidad del contenido mostrado, sin modificarlo.

    No ejecuta agentes, revisa cálculos, crea aprobaciones, exporta archivos
    ni importa Streamlit. La UI conserva el mismo borrador y esta huella;
    un cambio posterior exige mostrar y revisar el contenido nuevo.
    """
    fingerprint = calculate_draft_fingerprint(draft)
    markdown = render_report_markdown(draft)
    if calculate_draft_fingerprint(draft) != fingerprint:
        raise ValueError("El borrador cambió mientras se preparaba la vista previa.")
    return ReportPreview(
        markdown=markdown,
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=fingerprint,
        delivery_actions=ACTION_ORDER,
    )
