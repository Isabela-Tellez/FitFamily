"""
Modelo de recomendación de oportunidad — FitFamily Studio.
Multicriterio, determinista, explicable. Usa datos reales existentes.
No inventa cifras, tarifas ni rentabilidad.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class RecommendationInput:
    """Entradas del modelo: todo proviene de fuentes reales o supuestos del usuario."""
    scenario_type: str  # "basic" / "intermediate" / "optimistic"
    expected_clients: int | None  # del brief; None si no proporcionado
    monthly_fee: float | None
    fixed_costs: float | None
    variable_cost_per_client: float | None
    indicator_source: str  # "MCP" / "none" / "INE_pending"
    competitor_registry_path: str  # ruta real del JSON
    rent_status: str  # "verified" / "pending" / "unavailable"


@dataclass
class RecommendationResult:
    """Resultado auditable."""
    run_id: str
    evaluated_at: datetime
    score_global: float | None  # 0-100, solo si cobertura suficiente
    score_breakdown: dict[str, float]  # dimensiones
    recommendation: str  # "promising_conditional" / "insufficient_evidence" / "review_needed"
    factors_favorable: list[str]
    factors_unfavorable: list[str]
    missing_evidence: list[str]
    limitations: list[str]
    sources_used: list[str]
    assumptions_used: list[str]
    model_version: str = "v1.2026-11-03-deterministic"
    status: str = "pending_review"
