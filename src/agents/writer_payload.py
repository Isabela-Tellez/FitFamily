"""Preparación sin pérdida de datos y por lotes del contexto del redactor."""

import json

from src.schemas import ResearchBrief, ResearchResult


def collect_evidences(research: ResearchResult):
    """Una evidencia por identificador; rechaza versiones contradictorias."""
    records = {}
    for evidence in [
        *research.evidences,
        *(e for c in research.competitors for e in c.evidences),
    ]:
        previous = records.get(evidence.evidence_id)
        if previous is not None and previous != evidence:
            raise ValueError(
                f"Evidencia contradictoria: {evidence.evidence_id}. "
                "Hay que resolverla antes de redactar."
            )
        records[evidence.evidence_id] = evidence
    return records


def compact_writer_payload(brief: ResearchBrief, research: ResearchResult) -> str:
    """Conserva los campos originales y sustituye evidencias anidadas por IDs."""
    records = collect_evidences(research)
    data = research.model_dump(mode="json", exclude_none=True)
    data["evidences"] = [
        e.model_dump(mode="json", exclude_none=True) for e in records.values()
    ]
    for item, competitor in zip(data["competitors"], research.competitors):
        item.pop("evidences", None)
        item["evidence_ids"] = list(dict.fromkeys(
            e.evidence_id for e in competitor.evidences
        ))
    return json.dumps(
        {"brief": brief.model_dump(mode="json", exclude_none=True), "research": data},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def partition_writer_research(research: ResearchResult, fits) -> list[ResearchResult]:
    """Divide por competidor/evidencia, sin truncar campos ni tomar una muestra."""
    records = collect_evidences(research)
    if fits(research):
        return [research]

    metadata = research.model_dump(exclude={"competitors", "evidences"})
    attached = {
        e.evidence_id for c in research.competitors for e in c.evidences
    }
    units = [([c], c.evidences) for c in research.competitors]
    units.extend(([], [e]) for key, e in records.items() if key not in attached)
    batches = []
    current = ResearchResult(**metadata)
    if not fits(current):
        raise ValueError(
            "El encargo o las notas de investigación superan el presupuesto del "
            "redactor incluso sin evidencias. No se han recortado ni enviado datos."
        )

    for competitors, evidences in units:
        candidate = ResearchResult(
            **metadata,
            competitors=[*current.competitors, *competitors],
            evidences=[*current.evidences, *evidences],
        )
        if not fits(candidate):
            if current.competitors or current.evidences:
                batches.append(current)
            candidate = ResearchResult(
                **metadata, competitors=competitors, evidences=evidences,
            )
            if not fits(candidate):
                raise ValueError(
                    "Un registro individual supera el presupuesto del redactor. "
                    "No se ha truncado ni omitido; requiere preparar un resumen "
                    "trazable antes de llamar al modelo."
                )
        current = candidate
    if current.competitors or current.evidences:
        batches.append(current)
    return batches
