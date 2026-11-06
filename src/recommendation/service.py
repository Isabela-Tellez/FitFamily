"""
Servicio de recomendación — conecta datos reales y produce explicación.
No inventa cifras. Usa modelos de escenarios existentes.
"""
from src.recommendation.models import RecommendationInput, RecommendationResult
from src.recommendation.scoring import score_opportunity
import json
from pathlib import Path


def recommend(
    scenario_type: str = "intermediate",
    expected_clients: int | None = None,
    monthly_fee: float | None = None,
    fixed_costs: float | None = None,
    variable_cost_per_client: float | None = None,
    indicator_source: str = "MCP",
    competitor_registry_path: str = "data/processed/competitor_registry.json",
    rent_status: str = "pending",
    run_id: str = "fitfamily-recommendation-001",
) -> RecommendationResult:
    """
    Ejecuta lo que se puede demostrar con datos reales.
    Si faltan datos obligatorios, el resultado indica cobertura incompleta.
    """
    inp = RecommendationInput(
        scenario_type=scenario_type,
        expected_clients=expected_clients,
        monthly_fee=monthly_fee,
        fixed_costs=fixed_costs,
        variable_cost_per_client=variable_cost_per_client,
        indicator_source=indicator_source,
        competitor_registry_path=competitor_registry_path,
        rent_status=rent_status,
    )
    result = score_opportunity(inp)
    result.run_id = run_id
    return result
