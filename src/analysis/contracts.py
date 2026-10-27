"""Formato compartido entre análisis, redacción y revisión."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CalculatedMetric(BaseModel):
    """Un resultado producido por el código de análisis."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(min_length=1)

    # None significa que no hay datos suficientes para calcularlo.
    value: Decimal | None = Field(allow_inf_nan=False)

    unit: str = Field(min_length=1)
    calculation: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)

