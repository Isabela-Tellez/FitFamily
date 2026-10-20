"""
Modelo de datos para los borradores de informes de FitFamily.

Este módulo define la estructura básica que tendrá un informe
antes de convertirse en un documento final.

"""

from dataclasses import dataclass, field


@dataclass
class ReportDraft:
    """
    Representa un borrador de informe generado por FitFamily.

    Esta clase almacena la información del informe,
    pero no se encarga de redactarlo ni de exportarlo.

    Atributos:
        title: Título del informe.
        study_area: Zona geográfica objeto del estudio.
        sections: Lista de secciones del informe.
        sources: Lista de fuentes de información utilizadas.
        limitations: Lista de limitaciones del análisis.
    """

    # Datos obligatorios: deben proporcionarse al crear el borrador.
    title: str
    study_area: str

    # Datos opcionales: comienzan como listas vacías.
    # default_factory=list crea una lista independiente
    # para cada instancia de ReportDraft.
    # Así evitamos que dos informes compartan accidentalmente
    # las mismas secciones, fuentes o limitaciones.

    sections: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)