"""Workflow principal de investigación de FitFamily mediante LangGraph."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.researcher import run_research
from src.agents.strategic_writer import run_writing
from src.graph.state import ResearchState
from src.reporting.models import ReportDraft
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult


def research_node(state: ResearchState) -> dict[str, Any]:
    """Ejecuta la investigación y actualiza el estado compartido."""
    brief = ResearchBrief.model_validate(state["brief"])
    result = run_research(brief)

    return {
        "research_result": result.model_dump(mode="json"),
        "current_stage": "writing",
        "updated_at": _utc_now(),
    }


def writing_node(state: ResearchState) -> dict[str, Any]:
    """Genera un borrador utilizando la investigación disponible."""
    brief = ResearchBrief.model_validate(state["brief"])
    research = ResearchResult.model_validate(state["research_result"])

    draft = run_writing(brief, research)

    return {
        "report_draft": _draft_to_dict(draft),
        "report_version_id": f"{draft.draft_id}:{draft.version}",
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def review_node(state: ResearchState) -> dict[str, Any]:
    """Valida las referencias y la calidad básica del borrador."""
    research = ResearchResult.model_validate(state["research_result"])
    draft = ReportDraft(**state["report_draft"])
    review = run_basic_review(draft, research)

    return {
        "review_result": _review_to_dict(review),
        "status": "awaiting_approval" if not review.issues else "failed",
        "current_stage": "review",
        "updated_at": _utc_now(),
    }


def build_workflow(*, checkpointer: Any = None) -> Any:
    """Construye y compila el workflow de investigación."""
    builder = StateGraph(ResearchState)

    builder.add_node("research", research_node)
    builder.add_node("writing", writing_node)
    builder.add_node("review", review_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "writing")
    builder.add_edge("writing", "review")
    builder.add_edge("review", END)

    return builder.compile(checkpointer=checkpointer)


def _utc_now() -> str:
    """Devuelve la hora actual en UTC."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _draft_to_dict(draft: ReportDraft) -> dict[str, Any]:
    """Convierte el borrador en un diccionario serializable."""
    from dataclasses import asdict

    return asdict(draft)


def _review_to_dict(review: Any) -> dict[str, Any]:
    """Convierte el resultado de revisión en un diccionario serializable."""
    from dataclasses import asdict

    return asdict(review)
