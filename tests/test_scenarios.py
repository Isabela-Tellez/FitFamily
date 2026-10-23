import pytest

from src.analysis.scenarios import calculate_break_even_clients


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