"""
Modelos para los borradores de informes de FitFamily.

El borrador conserva su contenido y las referencias que permiten
rastrear las afirmaciones hasta las evidencias utilizadas.
"""

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4
from math import isfinite


@dataclass
class ReportClaim:
    """
    Afirmación incluida en el informe.

    Atributos:
        claim_id: Identificador único dentro del borrador.
        text: Texto de la afirmación.
        kind: Distingue hechos, supuestos e inferencias.
        evidence_ids: Identificadores de las evidencias que la respaldan.
        metric_id: Identificador del resultado de análisis citado.
        reported_value: Valor numérico utilizado en el informe.
        reported_unit: Unidad del valor utilizado.

    Registrar una referencia no demuestra que respalde la afirmación.
    Esa comprobación corresponde al constructor y al revisor.
    """

    claim_id: str
    text: str
    kind: Literal["fact", "assumption", "inference"]
    evidence_ids: list[str] = field(default_factory=list)
     # Referencia al resultado calculado por el módulo de análisis.
    # None indica que esta afirmación no tiene una métrica vinculada.
    metric_id: str | None = None
    # Valor y unidad utilizados en el informe.
    # El revisor los comparará con el resultado del analista.
    reported_value: float | None = None
    reported_unit: str | None = None

    def __post_init__(self) -> None:
        """Comprueba que la referencia numérica esté completa."""
        metric_fields = (
            self.metric_id,
            self.reported_value,
            self.reported_unit,
        )

        # Las afirmaciones sin métrica siguen siendo válidas.
        if all(value is None for value in metric_fields):
            return

        # Si vinculamos una métrica, necesitamos los tres campos.
        if any(value is None for value in metric_fields):
            raise ValueError(
                "La referencia a una métrica requiere "
                "metric_id, reported_value y reported_unit."
            )

        if not isinstance(self.metric_id, str) or not self.metric_id.strip():
            raise ValueError("metric_id debe ser un texto no vacío.")

        if (
            not isinstance(self.reported_unit, str)
            or not self.reported_unit.strip()
        ):
            raise ValueError("reported_unit debe ser un texto no vacío.")

        # Rechazamos booleanos, texto y valores infinitos o NaN.
        if (
            isinstance(self.reported_value, bool)
            or not isinstance(self.reported_value, (int, float))
            or not isfinite(self.reported_value)
        ):
            raise ValueError("reported_value debe ser un número finito.")


@dataclass
class ReportDraft:
    """
    Borrador de informe pendiente de revisión y entrega.

    Atributos:
        title: Título del informe.
        study_area: Zona geográfica estudiada.
        sections: Secciones con su contenido.
        sources: Fuentes utilizadas.
        limitations: Limitaciones del estudio.
        draft_id: Identificador del borrador.
        version: Versión del contenido, comenzando en 1.
        claims: Afirmaciones y sus referencias.

    El identificador se conserva al revisar un mismo borrador.
    Si cambia su contenido, el proceso de revisión debe incrementar
    la versión. Esta clase no lo hace automáticamente.
    """

    title: str
    study_area: str

    # Conservamos los campos existentes para mantener la compatibilidad.
    sections: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    # Cada borrador nuevo recibe un identificador independiente.
    draft_id: str = field(default_factory=lambda: uuid4().hex)
    version: int = 1
    claims: list[ReportClaim] = field(default_factory=list)

