import math
from math import isfinite

def calculate_break_even_clients(
    fixed_costs: float,
    monthly_fee: float,
    variable_cost_per_client: float,
) -> int:
    """
    Calcula el número mínimo de clientes necesarios para cubrir los costes.

    Parámetros:
        fixed_costs: costes fijos mensuales en euros.
        monthly_fee: cuota mensual por cliente en euros.
        variable_cost_per_client: coste variable mensual por cliente en euros.

    Devuelve:
        Número mínimo de clientes necesarios para alcanzar el punto de equilibrio.

    Lanza:
        ValueError: si los valores son negativos o el margen por cliente no es positivo.
    """
    # Comprobamos que todos los importes sean números finitos.
    if not all(
        isfinite(value)
        for value in (
            fixed_costs,
            monthly_fee,
            variable_cost_per_client,
        )
    ):
        raise ValueError("All financial inputs must be finite numbers.")
    
    # Comprobamos que los importes sean válidos.
    if fixed_costs < 0:
        raise ValueError("Fixed costs cannot be negative.")

    if monthly_fee < 0:
        raise ValueError("Monthly fee cannot be negative.")

    if variable_cost_per_client < 0:
        raise ValueError("Variable cost per client cannot be negative.")

    # Calculamos cuánto aporta cada cliente para cubrir los costes fijos.
    contribution_margin = monthly_fee - variable_cost_per_client

    # Si el margen no es positivo, no existe un punto de equilibrio finito.
    if contribution_margin <= 0:
        raise ValueError(
            "Monthly fee must be greater than variable cost per client."
        )

    # Redondeamos hacia arriba porque necesitamos clientes enteros.
    return math.ceil(fixed_costs / contribution_margin)