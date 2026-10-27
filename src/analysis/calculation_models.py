from typing import Literal

from pydantic import BaseModel, Field


class CalculationInput(BaseModel):
    """Representa un valor utilizado como entrada de un cálculo."""

    name: str = Field(
        description="Nombre de la variable utilizada en el cálculo."
    )
    value: float | None = Field(
        default=None,
        description="Valor numérico de la entrada, o None si falta.",
    )
    unit: str = Field(
        description="Unidad de medida de la entrada."
    )
    input_type: Literal["evidence", "assumption"] = Field(
    description="Indica si el valor procede de una evidencia o es un supuesto."
    )

class CalculationValue(BaseModel):
    """Representa un valor numérico obtenido o utilizado en un cálculo."""

    value: float = Field(
        description="Valor numérico registrado."
    )
    unit: str = Field(
        description="Unidad de medida del valor."
    )

class CalculationResult(BaseModel):
    """Registra un cálculo económico y la información necesaria para explicarlo."""

    calculation_id: str = Field(
        description="Identificador único del cálculo."
    )
    calculation_type: str = Field(
        description="Tipo de cálculo realizado."
    )
    inputs: list[CalculationInput] = Field(
        default_factory=list,
        description="Entradas utilizadas, con sus valores y unidades.",
    )
    operation: str = Field(
        description="Fórmula u operación aplicada."
    )
    result: CalculationValue | None = Field(
        default=None,
        description="Resultado del cálculo, o None si no se pudo obtener.",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Identificadores de las evidencias que respaldan las entradas.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Limitaciones, datos ausentes o advertencias del cálculo.",
    )

class EconomicScenario(BaseModel):
    """Representa un escenario económico con sus hipótesis y resultados."""

    scenario_id: str = Field(
        description="Identificador único del escenario."
    )
    scenario_type: Literal[
        "conservative",
        "intermediate",
        "optimistic",
    ] = Field(
        description="Tipo de escenario económico."
    )
    expected_clients: int = Field(
        ge=0,
        description="Número de clientes previstos en el escenario."
    )
    monthly_fee: float = Field(
        gt=0,
        description="Cuota mensual por cliente en euros."
    )
    fixed_costs: float = Field(
        ge=0,
        description="Costes fijos mensuales en euros."
    )
    variable_cost_per_client: float = Field(
        ge=0,
        description="Coste variable mensual por cliente en euros."
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Hipótesis utilizadas en el escenario."
    )
