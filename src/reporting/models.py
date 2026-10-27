"""
Modelos para los borradores de informes de FitFamily.

El borrador conserva su contenido y las referencias que permiten
rastrear las afirmaciones hasta las evidencias utilizadas.
"""

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4
from src.analysis.contracts import ReportedMetric

@dataclass
class ReportClaim:
    """
    Afirmación incluida en el informe.

    Atributos:
        claim_id: Identificador único dentro del borrador.
        text: Texto de la afirmación.
        kind: Distingue hechos, supuestos e inferencias.
        evidence_ids: Identificadores de las evidencias que la respaldan.

    Registrar una referencia no demuestra que respalde la afirmación.
    Esa comprobación corresponde al constructor y al revisor.
    """

    claim_id: str
    text: str
    kind: Literal["fact", "assumption", "inference"]
    evidence_ids: list[str] = field(default_factory=list)


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

    # Cifras estructuradas que deben compararse con el análisis.
    reported_metrics: list[ReportedMetric] = field(default_factory=list)