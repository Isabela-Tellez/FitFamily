"""Formato compartido entre análisis, redacción y revisión."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


from src.analysis.calculation_models import CalculationResult, EconomicScenario


class CalculationContext(BaseModel):
    """Procedencia original y supuestos; incluidos en la huella del análisis."""
    model_config = ConfigDict(extra="forbid")
    scenario: EconomicScenario
    calculation_result: CalculationResult
    input_evidence_ids: dict[str, str] = Field(default_factory=dict)


class CalculatedMetric(BaseModel):
    """Un resultado producido por el código de análisis."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(min_length=1)

    # None significa que no hay datos suficientes para calcularlo.
    value: Decimal | None = Field(allow_inf_nan=False)

    unit: str = Field(min_length=1)
    calculation: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


    context: CalculationContext | None = None
