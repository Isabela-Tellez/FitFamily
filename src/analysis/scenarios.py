from src.analysis.calculation_models import EconomicScenario, CalculationResult
from src.analysis.economic_calculations import (
    calculate_monthly_revenue,
    calculate_monthly_variable_costs,
    calculate_monthly_result,
    create_break_even_calculation,
)


def create_economic_scenario(
    scenario_type: str,
    expected_clients: int,
    monthly_fee: float,
    fixed_costs: float,
    variable_cost_per_client: float,
    assumptions: list[str] | None = None,
) -> EconomicScenario:
    """
    Crea un escenario económico a partir de sus parámetros.

    Parámetros:
        scenario_type: tipo de escenario económico.
        expected_clients: número de clientes previstos.
        monthly_fee: cuota mensual por cliente en euros.
        fixed_costs: costes fijos mensuales en euros.
        variable_cost_per_client: coste variable mensual por cliente.
        assumptions: lista de suposiciones del escenario.

    Devuelve:
        Un escenario económico validado.
    """
    # Creamos el escenario con los parámetros recibidos.
    return EconomicScenario(
        scenario_id=f"scenario_{scenario_type}",
        scenario_type=scenario_type,
        expected_clients=expected_clients,
        monthly_fee=monthly_fee,
        fixed_costs=fixed_costs,
        variable_cost_per_client=variable_cost_per_client,
        assumptions=assumptions or [],
    )


def evaluate_economic_scenario(
    scenario: EconomicScenario,
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> list[CalculationResult]:
    """
    Evalúa un escenario económico mediante varios cálculos relacionados.

    Parámetros:
        scenario: escenario económico que se va a evaluar.
        evidence_ids: identificadores de las evidencias disponibles.
        limitations: limitaciones generales del análisis.

    Devuelve:
        Lista de resultados de los cálculos económicos realizados.
    """
    # Calculamos los ingresos mensuales previstos.
    revenue_calculation = calculate_monthly_revenue(
        scenario=scenario,
        evidence_ids=evidence_ids,
        limitations=limitations,
    )

    # Calculamos los costes variables mensuales.
    variable_costs_calculation = calculate_monthly_variable_costs(
        scenario=scenario,
        evidence_ids=evidence_ids,
        limitations=limitations,
    )

    # Recuperamos los importes calculados para utilizarlos en el siguiente paso.
    monthly_revenue = revenue_calculation.result.value
    monthly_variable_costs = variable_costs_calculation.result.value

    # Calculamos el resultado mensual después de descontar los costes.
    monthly_result_calculation = calculate_monthly_result(
        monthly_revenue=monthly_revenue,
        monthly_variable_costs=monthly_variable_costs,
        fixed_costs=scenario.fixed_costs,
        evidence_ids=evidence_ids,
        limitations=limitations,
    )

    # Calculamos el número mínimo de clientes para cubrir los costes.
    break_even_calculation = create_break_even_calculation(
        fixed_costs=scenario.fixed_costs,
        monthly_fee=scenario.monthly_fee,
        variable_cost_per_client=scenario.variable_cost_per_client,
        evidence_ids=evidence_ids,
        limitations=limitations,
    )

    # Reunimos los cuatro resultados para facilitar su uso posterior.
    return [
        revenue_calculation,
        variable_costs_calculation,
        monthly_result_calculation,
        break_even_calculation,
    ]

def compare_economic_scenarios(
    scenarios: list[EconomicScenario],
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, list[CalculationResult]]:
    """
    Compara varios escenarios económicos evaluando sus cálculos.

    Parámetros:
        scenarios: lista de escenarios que se van a comparar.
        evidence_ids: identificadores de las evidencias disponibles.
        limitations: limitaciones generales del análisis.

    Devuelve:
        Diccionario con los resultados económicos de cada escenario.
    """
    # Evaluamos cada escenario y agrupamos sus resultados por identificador.
    comparison = {}

    for scenario in scenarios:
        comparison[scenario.scenario_id] = evaluate_economic_scenario(
            scenario=scenario,
            evidence_ids=evidence_ids,
            limitations=limitations,
        )

    return comparison