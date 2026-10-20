"""
Agente redactor de FitFamily.

Transforma el encargo y los resultados de investigación de Persona 1
en un borrador con la estructura ReportDraft.

Esta versión organiza los datos sin utilizar un LLM.
No calcula la viabilidad financiera ni inventa información ausente.
"""

from src.reporting.models import ReportDraft
from src.schemas import ResearchBrief, ResearchResult


class WriterAgent:
    """Prepara borradores de informes a partir de una investigación."""

    def create_draft(
        self,
        brief: ResearchBrief,
        research_result: ResearchResult,
    ) -> ReportDraft:
        """
        Crea un borrador de informe a partir de una investigación.

        Args:
            brief: Encargo con el negocio, la zona y las preguntas.
            research_result: Competidores, evidencias y preguntas
                pendientes recopilados por el investigador.

        Returns:
            Un ReportDraft con secciones, fuentes y limitaciones.
        """
        title = (
            f"Estudio de mercado: {brief.business_type} "
            f"en {brief.study_area}"
        )

        # Cada sección incluye su título y su contenido.
        sections = [
            self._build_scope_section(brief),
            self._build_competitors_section(research_result),
        ]

        # Reunimos las evidencias generales y las de cada competidor.
        evidences = list(research_result.evidences)
        for competitor in research_result.competitors:
            evidences.extend(competitor.evidences)

        sources: list[str] = []
        limitations: list[str] = []

        for evidence in evidences:
            # Los intentos fallidos no respaldan datos del informe.
            if evidence.evidence_id.startswith("access_attempt_"):
                message = "No se pudo acceder a una fuente"
                if evidence.source_url:
                    message += f": {evidence.source_url}"
                self._add_unique(limitations, message)
            elif evidence.source_url:
                self._add_unique(sources, evidence.source_url)

            if evidence.limitations:
                self._add_unique(limitations, evidence.limitations)

        # Conservamos los supuestos separados de los datos observados.
        if brief.assumed:
            self._add_unique(
                limitations,
                "El encargo está marcado como basado en supuestos.",
            )

        if brief.assumed_params:
            assumptions = "\n".join(
                f"- {name}: {value}"
                for name, value in brief.assumed_params.items()
            )
            sections.append(
                "Supuestos del encargo\n"
                "Los siguientes datos son supuestos, no observaciones:\n"
                + assumptions
            )

        if research_result.search_performed:
            sections.append(
                "Proceso de investigación\n"
                + research_result.search_performed
            )

        if research_result.unresolved_questions:
            pending = "\n".join(
                f"- {question}"
                for question in research_result.unresolved_questions
            )
            sections.append("Preguntas pendientes\n" + pending)

            for question in research_result.unresolved_questions:
                self._add_unique(
                    limitations,
                    f"Pregunta pendiente: {question}",
                )

        if not sources:
            self._add_unique(
                limitations,
                "No se han recibido enlaces de fuentes utilizables.",
            )

        self._add_unique(
            limitations,
            "Borrador generado sin LLM a partir de los datos recibidos. "
            "No constituye una conclusión de viabilidad financiera.",
        )

        return ReportDraft(
            title=title,
            study_area=brief.study_area,
            sections=sections,
            sources=sources,
            limitations=limitations,
        )

    def _build_scope_section(self, brief: ResearchBrief) -> str:
        """Describe el objetivo y el ámbito del estudio."""
        lines = [
            "Objetivo y alcance",
            f"Negocio estudiado: {brief.business_type}.",
            f"Ubicación: {brief.location}.",
            f"Zona de estudio: {brief.study_area}.",
        ]

        if brief.questions:
            lines.append("Preguntas del encargo:")
            lines.extend(f"- {question}" for question in brief.questions)

        return "\n".join(lines)

    def _build_competitors_section(
        self,
        research_result: ResearchResult,
    ) -> str:
        """Presenta los competidores y sus tarifas sin completar datos."""
        lines = ["Competidores y tarifas"]

        if not research_result.competitors:
            lines.append(
                "La investigación no ha aportado competidores. "
                "Esto no demuestra que no existan."
            )
            return "\n".join(lines)

        lines.append(
            "Resultados recopilados automáticamente; "
            "requieren comprobación de las fuentes."
        )

        frequency_labels = {
            "monthly": "mensual",
            "annual": "anual",
            "one-time": "pago único",
        }

        for index, competitor in enumerate(
            research_result.competitors,
            start=1,
        ):
            name = competitor.name or "Nombre no disponible"
            location = competitor.location or "No disponible"
            services = (
                ", ".join(competitor.services)
                if competitor.services
                else "No disponibles"
            )

            lines.extend([
                "",
                f"{index}. {name}",
                f"Ubicación: {location}",
                f"Servicios: {services}",
            ])

            if not competitor.tariffs:
                lines.append("Tarifas: no disponibles.")
            else:
                lines.append("Tarifas publicadas:")

                for tariff in competitor.tariffs:
                    value = tariff.get("value")
                    unit = tariff.get("unit") or "unidad no indicada"
                    frequency = tariff.get("frequency")
                    frequency_label = frequency_labels.get(
                        frequency,
                        frequency or "frecuencia no indicada",
                    )

                    if value is None:
                        lines.append("- Importe no disponible.")
                    else:
                        lines.append(
                            f"- {value} {unit}; {frequency_label}."
                        )

                    condition = tariff.get("condition")
                    if condition:
                        lines.append(f"  Condiciones: {condition}")

            # Las fuentes quedan junto al competidor y en la lista general.
            competitor_sources: list[str] = []
            for evidence in competitor.evidences:
                if (
                    evidence.source_url
                    and not evidence.evidence_id.startswith(
                        "access_attempt_"
                    )
                ):
                    self._add_unique(
                        competitor_sources,
                        evidence.source_url,
                    )

            if competitor_sources:
                lines.append("Fuentes:")
                lines.extend(
                    f"- {source}" for source in competitor_sources
                )
            else:
                lines.append("Fuentes: no disponibles.")

        return "\n".join(lines)

    @staticmethod
    def _add_unique(items: list[str], value: str) -> None:
        """Añade un texto sin duplicados ni espacios sobrantes."""
        clean_value = value.strip()
        if clean_value and clean_value not in items:
            items.append(clean_value)