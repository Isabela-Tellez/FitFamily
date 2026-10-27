"""Recorrido análisis → redacción → revisión; nunca aprueba ni exporta."""
from dataclasses import dataclass
from src.analysis.provenance import (
    calculate_observed_metrics, calculate_price_average, calculate_break_even_metric,
)
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context


@dataclass
class ReviewedReport:
    draft: object
    calculated_metrics: list
    review: object
    route: str


def prepare_reviewed_report(brief, research, *, price_evidence_ids=None,
                            break_even_inputs=None, use_llm=False,
                            revision_count=0, max_revisions=2):
    metrics = calculate_observed_metrics(research)
    if price_evidence_ids is not None:
        metrics.append(calculate_price_average(research, price_evidence_ids))
    if break_even_inputs is not None:
        metrics.append(calculate_break_even_metric(research, break_even_inputs))
    draft = build_report(brief, research, use_llm=use_llm, calculated_metrics=metrics)
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    route = choose_review_route_for_context(
        review, draft, research, revision_count=revision_count,
        max_revisions=max_revisions, calculated_metrics=metrics,
    )
    return ReviewedReport(draft, metrics, review, route)


def export_reviewed_report(result, research, approval, run_id, output_dir, *,
                           csv_path=None, revision_count=0, max_revisions=2):
    """Puerta de entrega: contexto vigente y aprobación humana obligatoria."""
    from src.automation.delivery import export_approved_report
    route = choose_review_route_for_context(
        result.review, result.draft, research,
        revision_count=revision_count, max_revisions=max_revisions,
        calculated_metrics=result.calculated_metrics,
    )
    if route != "pending_review":
        raise ValueError("El informe tiene correcciones pendientes: " + route)
    return export_approved_report(
        result.draft, approval, run_id, output_dir, csv_path=csv_path,
    )
