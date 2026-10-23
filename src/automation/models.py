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