"""Herramienta para calcular y comparar escenarios económicos."""

from typing import Literal

from pydantic import BaseModel, Field

from src.analysis.calculation_models import EconomicScenario
from src.analysis.scenarios import evaluate_economic_scenario


class ScenarioInput(BaseModel):
    """Define los datos necesarios para evaluar un escenario económico."""

    scenario_type: Literal["conservative", "intermediate", "optimistic"]
    expected_clients: int = Field(ge=0)
    monthly_fee: float = Field(gt=0)
    fixed_costs: float = Field(ge=0)
    variable_cost_per_client: float = Field(ge=0)
    assumptions: list[str] = Field(default_factory=list)


def calculate_scenarios(data: ScenarioInput) -> list[dict]:
    """Calcula los principales indicadores de un escenario económico."""

    scenario = EconomicScenario(
        scenario_id=f"scenario_{data.scenario_type}",
        scenario_type=data.scenario_type,
        expected_clients=data.expected_clients,
        monthly_fee=data.monthly_fee,
        fixed_costs=data.fixed_costs,
        variable_cost_per_client=data.variable_cost_per_client,
        assumptions=data.assumptions,
    )

    calculations = evaluate_economic_scenario(scenario)

    return [
        calculation.model_dump(mode="json")
        for calculation in calculations
    ]