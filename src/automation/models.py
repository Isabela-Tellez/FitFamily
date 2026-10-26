"""
Modelos para la exportación controlada de informes.

El controlador proporciona el registro de aprobación
después de recibir la decisión de la persona usuaria.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ApprovalRecord:
    """
    Decisión humana asociada a un borrador concreto.

    Atributos:
        run_id: Identificador de la ejecución.
        draft_id: Identificador del borrador revisado.
        draft_version: Versión del borrador revisado.
        draft_fingerprint: Huella del contenido revisado.
        approved: Indica si la persona autorizó la entrega.
        actions: Acciones autorizadas.
        decided_at: Fecha de la decisión, con zona horaria.

    Este objeto registra una decisión; crearlo no demuestra
    por sí mismo que haya existido aprobación humana.
    """

    run_id: str
    draft_id: str
    draft_version: int
    draft_fingerprint: str
    approved: bool
    actions: tuple[str, ...]
    decided_at: datetime

@dataclass(frozen=True)
class TrackingRecord:
    """
    Fila de seguimiento de una entrega aprobada.

    Registra el borrador y los archivos publicados.
    No representa una conclusión sobre la viabilidad del negocio.
    """

    # Identificamos la ejecución y el contenido aprobado.
    run_id: str
    draft_id: str
    draft_version: int
    draft_fingerprint: str

    # Guardamos la fecha de aprobación en formato ISO con zona horaria.
    # Usaremos la fecha del ApprovalRecord para mantenerla estable
    # cuando se repita una operación.
    approved_at: str

    # Identificamos el estudio sin copiar todo el informe al CSV.
    case: str
    study_area: str

    # Estado de la entrega: "partial" o "complete".
    # La función de seguimiento lo calculará según las acciones
    # autorizadas y los archivos que se hayan publicado.
    status: str

    # Una ruta vacía indica que ese formato todavía no se ha generado
    # o que no forma parte de las acciones autorizadas.
    markdown_path: str = ""
    pdf_path: str = ""