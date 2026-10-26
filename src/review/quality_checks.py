"""Ejecución de las comprobaciones básicas del revisor."""
import hashlib
import json
from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.models import ReportDraft
from src.review.models import ReviewIssue, ReviewResult
from src.review.validation import (
    validate_claim_references,
    validate_evidence_quality,
)
from src.schemas import ResearchResult

def calculate_research_fingerprint(
    research_result: ResearchResult,
) -> str:
    """
    Calcula una huella del contenido de la investigación.

    Incluye evidencias generales, competidores, sus evidencias
    y el resto de los campos de ResearchResult.
    """
    serialized = json.dumps(
        research_result.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def run_basic_review(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> ReviewResult:
    """
    Reúne las validaciones de referencias y calidad básica.

    No modifica el borrador, no llama a un LLM y no exporta archivos.
    """
    raw_issues = validate_claim_references(draft, research_result)
    raw_issues += validate_evidence_quality(draft, research_result)

    issues: list[ReviewIssue] = []

    for item in raw_issues:
        # Si existe una evidencia pero falta su procedencia,
        # investigación debe completar o aclarar ese registro.
        if item["code"] == "evidence_without_source":
            correction_stage = "research"
        else:
            # Las referencias incorrectas y las citas de registros
            # fallidos requieren corregir las afirmaciones del informe.
            correction_stage = "writing"

        issues.append(
            ReviewIssue(
                code=item["code"],
                reference_id=item["reference_id"],
                message=item["message"],
                severity="error",
                correction_stage=correction_stage,
            )
        )

    return ReviewResult(
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        issues=tuple(issues),
        checks_performed=(
            "claim_references",
            "evidence_quality",
        ),
        research_fingerprint=calculate_research_fingerprint(
            research_result
        ),
    )

def validate_review_matches_draft(
    review: ReviewResult,
    draft: ReportDraft,
) -> None:
    """
    Comprueba que la revisión corresponde al borrador actual.

    Si cambia el identificador, la versión o el contenido,
    es necesario realizar una nueva revisión.
    """
    if review.draft_id != draft.draft_id:
        raise ValueError("La revisión pertenece a otro borrador.")

    if review.draft_version != draft.version:
        raise ValueError("La revisión corresponde a otra versión.")

    current_fingerprint = calculate_draft_fingerprint(draft)

    if review.draft_fingerprint != current_fingerprint:
        raise ValueError(
            "El contenido cambió después de la revisión."
        )
    
def validate_review_matches_research(
    review: ReviewResult,
    research_result: ResearchResult,
) -> None:
    """
    Rechaza una revisión si no corresponde a la investigación actual.

    No modifica los datos ni realiza una nueva revisión.
    """
    if not review.research_fingerprint:
        raise ValueError(
            "La revisión no tiene huella de investigación. "
            "Es necesario revisar de nuevo."
        )

    current_fingerprint = calculate_research_fingerprint(
        research_result
    )

    if review.research_fingerprint != current_fingerprint:
        raise ValueError(
            "La investigación cambió después de la revisión."
        )
