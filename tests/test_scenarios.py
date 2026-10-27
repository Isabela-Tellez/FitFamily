import pytest

from src.analysis.economic_calculations import (
    calculate_break_even_clients,
    create_break_even_calculation,
    calculate_monthly_revenue,
    calculate_monthly_result,
    calculate_monthly_variable_costs,
)
from src.analysis.calculation_models import EconomicScenario
from src.analysis.economic_calculations import calculate_monthly_revenue
from src.analysis.scenarios import create_economic_scenario
from src.analysis.scenarios import evaluate_economic_scenario
from src.analysis.scenarios import compare_economic_scenarios


def test_calculate_break_even_clients_returns_expected_result():
    # Comprobamos el cálculo con supuestos económicos ficticios.
    result = calculate_break_even_clients(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
    )

    # Cada cliente aporta 30 euros y necesitamos 200 clientes.
    assert result == 200


def test_calculate_break_even_clients_rounds_up():
    # Comprobamos que se redondea hacia arriba si el resultado no es entero.
    result = calculate_break_even_clients(
        fixed_costs=6010,
        monthly_fee=40,
        variable_cost_per_client=10,
    )

    assert result == 201


def test_calculate_break_even_clients_returns_zero_without_fixed_costs():
    # Si no hay costes fijos, no necesitamos clientes para cubrirlos.
    result = calculate_break_even_clients(
        fixed_costs=0,
        monthly_fee=40,
        variable_cost_per_client=10,
    )

    assert result == 0


def test_calculate_break_even_clients_rejects_zero_margin():
    # Comprobamos que no se acepta una cuota igual al coste variable.
    with pytest.raises(ValueError, match="Monthly fee must be greater"):
        calculate_break_even_clients(
            fixed_costs=6000,
            monthly_fee=10,
            variable_cost_per_client=10,
        )


def test_calculate_break_even_clients_rejects_negative_fixed_costs():
    # Comprobamos que no se aceptan costes fijos negativos.
    with pytest.raises(ValueError, match="Fixed costs cannot be negative"):
        calculate_break_even_clients(
            fixed_costs=-100,
            monthly_fee=40,
            variable_cost_per_client=10,
        )


def test_calculate_break_even_clients_rejects_negative_monthly_fee():
    # Comprobamos que no se acepta una cuota mensual negativa.
    with pytest.raises(ValueError, match="Monthly fee cannot be negative"):
        calculate_break_even_clients(
            fixed_costs=6000,
            monthly_fee=-40,
            variable_cost_per_client=10,
        )


def test_calculate_break_even_clients_rejects_negative_variable_cost():
    # Comprobamos que no se aceptan costes variables negativos.
    with pytest.raises(
        ValueError,
        match="Variable cost per client cannot be negative",
    ):
        calculate_break_even_clients(
            fixed_costs=6000,
            monthly_fee=40,
            variable_cost_per_client=-10,
        )

def test_calculate_break_even_clients_rejects_infinite_fixed_costs():
    # Comprobamos que no se aceptan importes infinitos.
    with pytest.raises(ValueError, match="finite numbers"):
        calculate_break_even_clients(
            fixed_costs=float("inf"),
            monthly_fee=40,
            variable_cost_per_client=10,
        )

def test_create_break_even_calculation_records_traceability():
    # Creamos un cálculo con datos económicos conocidos.
    calculation = create_break_even_calculation(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
        evidence_ids=["evidence_example_001"],
    )

    # Comprobamos que el cálculo y sus entradas quedan registrados.
    assert calculation.calculation_type == "break_even"
    # Comprobamos que el identificador tiene el prefijo esperado.
    assert calculation.calculation_id.startswith("calc_break_even_")

    # Comprobamos que el identificador contiene un valor único.
    assert len(calculation.calculation_id) > len("calc_break_even_")
    assert len(calculation.inputs) == 3

    # Comprobamos que se conservan las unidades de las entradas.
    assert calculation.inputs[0].unit == "EUR/month"
    assert calculation.inputs[1].unit == "EUR/client/month"
    assert calculation.inputs[2].unit == "EUR/client/month"

    # Comprobamos el resultado, la operación y las evidencias.
    assert calculation.operation
    assert calculation.result is not None
    assert calculation.result.value == 200
    assert calculation.result.unit == "clients"
    assert calculation.evidence_ids == ["evidence_example_001"]
    assert all(
    item.input_type == "assumption"
    for item in calculation.inputs
    )

def test_create_break_even_calculation_generates_unique_ids():
    # Creamos dos cálculos con las mismas entradas.
    first = create_break_even_calculation(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
    )
    second = create_break_even_calculation(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
    )

    # Cada registro debe poder identificarse por separado.
    assert first.calculation_id != second.calculation_id

def test_create_break_even_calculation_records_limitations():
    # Registramos una limitación asociada a los valores utilizados.
    calculation = create_break_even_calculation(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
        limitations=["Financial inputs are assumptions, not verified market data."],
    )

    assert calculation.limitations == [
        "Financial inputs are assumptions, not verified market data."
    ]

def test_create_break_even_calculation_preserves_input_types():
    # Clasificamos cada entrada según su origen real.
    calculation = create_break_even_calculation(
        fixed_costs=6000,
        monthly_fee=40,
        variable_cost_per_client=10,
        evidence_ids=["evidence_example_001"],
        input_types={
            "fixed_costs": "assumption",
            "monthly_fee": "evidence",
            "variable_cost_per_client": "assumption",
        },
    )

    input_types = {
        item.name: item.input_type
        for item in calculation.inputs
    }

    assert input_types["fixed_costs"] == "assumption"
    assert input_types["monthly_fee"] == "evidence"
    assert input_types["variable_cost_per_client"] == "assumption"

def test_calculate_monthly_revenue_returns_expected_result():
    """Comprueba el cálculo de ingresos y su trazabilidad."""
    scenario = EconomicScenario(
        scenario_id="scenario_test",
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=40,
        fixed_costs=2500,
        variable_cost_per_client=5,
    )

    result = calculate_monthly_revenue(scenario)

    assert result.calculation_type == "monthly_revenue"
    assert result.result is not None
    assert result.result.value == 4000
    assert result.result.unit == "EUR/month"
    assert result.operation == "expected_clients * monthly_fee"
    assert len(result.inputs) == 2
    assert result.calculation_id.startswith("calc_monthly_revenue_")

def test_create_economic_scenario_returns_expected_values():
    """Comprueba que se crea un escenario con los valores indicados."""
    scenario = create_economic_scenario(
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=40,
        fixed_costs=2500,
        variable_cost_per_client=5,
        assumptions=["La cuota mensual prevista es de 40 EUR."],
    )

    assert scenario.scenario_type == "intermediate"
    assert scenario.expected_clients == 100
    assert scenario.monthly_fee == 40
    assert scenario.fixed_costs == 2500
    assert scenario.variable_cost_per_client == 5
    assert len(scenario.assumptions) == 1

def test_calculate_monthly_result_returns_expected_result():
    """Comprueba el resultado mensual y su trazabilidad."""
    result = calculate_monthly_result(
        monthly_revenue=4000,
        monthly_variable_costs=500,
        fixed_costs=2500,
    )

    assert result.calculation_type == "monthly_result"
    assert result.result is not None
    assert result.result.value == 1000
    assert result.result.unit == "EUR/month"
    assert len(result.inputs) == 3
    assert result.calculation_id.startswith("calc_monthly_result_")

def test_calculate_monthly_variable_costs_returns_expected_result():
    """Comprueba el cálculo de costes variables y su trazabilidad."""
    scenario = EconomicScenario(
        scenario_id="scenario_test",
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=40,
        fixed_costs=2500,
        variable_cost_per_client=5,
    )

    result = calculate_monthly_variable_costs(scenario)

    assert result.calculation_type == "monthly_variable_costs"
    assert result.result is not None
    assert result.result.value == 500
    assert result.result.unit == "EUR/month"
    assert len(result.inputs) == 2
    assert result.calculation_id.startswith("calc_monthly_variable_costs_")

def test_evaluate_economic_scenario_returns_expected_calculations():
    """Comprueba que se calculan y devuelven los cuatro resultados."""
    scenario = EconomicScenario(
        scenario_id="scenario_test",
        scenario_type="intermediate",
        expected_clients=100,
        monthly_fee=40,
        fixed_costs=2500,
        variable_cost_per_client=5,
    )

    results = evaluate_economic_scenario(scenario)

    # Comprobamos que se han generado los cuatro cálculos esperados.
    assert len(results) == 4
    assert [result.calculation_type for result in results] == [
        "monthly_revenue",
        "monthly_variable_costs",
        "monthly_result",
        "break_even",
    ]

    # Comprobamos los importes calculados.
    assert results[0].result.value == 4000
    assert results[1].result.value == 500
    assert results[2].result.value == 1000
    assert results[3].result.value == 72

def test_compare_economic_scenarios_returns_all_scenarios():
    scenarios = [
        create_economic_scenario(
            scenario_type="conservative",
            expected_clients=60,
            monthly_fee=40,
            fixed_costs=2500,
            variable_cost_per_client=5,
        ),
        create_economic_scenario(
            scenario_type="intermediate",
            expected_clients=100,
            monthly_fee=40,
            fixed_costs=2500,
            variable_cost_per_client=5,
        ),
        create_economic_scenario(
            scenario_type="optimistic",
            expected_clients=140,
            monthly_fee=40,
            fixed_costs=2500,
            variable_cost_per_client=5,
        ),
    ]

    comparison = compare_economic_scenarios(scenarios)

    assert len(comparison) == 3
    assert "scenario_conservative" in comparison
    assert "scenario_intermediate" in comparison
    assert "scenario_optimistic" in comparison

    for results in comparison.values():
        assert len(results) == 4