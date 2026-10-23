"""Ejecución de las comprobaciones básicas del revisor."""

from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.models import ReportDraft
from src.review.models import ReviewIssue, ReviewResult
from src.review.validation import (
    validate_claim_references,
    validate_evidence_quality,
)
from src.schemas import ResearchResult


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
    )