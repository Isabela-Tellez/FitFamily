"""Herramienta para realizar análisis numéricos controlados."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalysisRequest(BaseModel):
    """Define los datos necesarios para un análisis numérico."""

    operation: Literal[
        "describe",
        "mean",
        "growth_rate",
        "compare",
    ]
    values: list[float] = Field(min_length=1)
    comparison_values: list[float] | None = None

    @model_validator(mode="after")
    def validate_operation_inputs(self):
        """Comprueba que los datos sean adecuados para la operación."""

        if self.operation == "growth_rate" and len(self.values) < 2:
            raise ValueError(
                "Growth rate requires at least two values."
            )

        if self.operation == "compare":
            if not self.comparison_values:
                raise ValueError(
                    "Compare requires comparison_values."
                )

        if self.operation != "compare" and self.comparison_values is not None:
            raise ValueError(
                "comparison_values is only valid for compare."
            )

        return self


def run_python_analysis(request: AnalysisRequest) -> dict:
    """Ejecuta una operación estadística permitida."""

    values = request.values

    if request.operation == "mean":
        return {
            "operation": "mean",
            "mean": sum(values) / len(values),
            "count": len(values),
        }

    if request.operation == "describe":
        sorted_values = sorted(values)
        count = len(sorted_values)
        mean = sum(sorted_values) / count
        middle = count // 2

        if count % 2:
            median = sorted_values[middle]
        else:
            median = (
                sorted_values[middle - 1] + sorted_values[middle]
            ) / 2

        return {
            "operation": "describe",
            "count": count,
            "mean": mean,
            "median": median,
            "minimum": sorted_values[0],
            "maximum": sorted_values[-1],
            "range": sorted_values[-1] - sorted_values[0],
        }

    if request.operation == "growth_rate":
        initial_value = values[0]
        final_value = values[-1]

        if initial_value == 0:
            raise ValueError(
                "Growth rate cannot be calculated from an initial value of zero."
            )

        return {
            "operation": "growth_rate",
            "initial_value": initial_value,
            "final_value": final_value,
            "growth_rate_percent": (
                (final_value - initial_value) / abs(initial_value)
            ) * 100,
        }

    if request.operation == "compare":
        comparison_values = request.comparison_values
        assert comparison_values is not None

        mean_a = sum(values) / len(values)
        mean_b = sum(comparison_values) / len(comparison_values)

        return {
            "operation": "compare",
            "mean_a": mean_a,
            "mean_b": mean_b,
            "difference": mean_b - mean_a,
        }

    raise ValueError("Unsupported analysis operation.")