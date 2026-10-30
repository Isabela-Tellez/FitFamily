"""Pruebas de la herramienta de análisis numérico."""

import pytest
from pydantic import ValidationError

from src.tools.run_python_analysis import (
    AnalysisRequest,
    run_python_analysis,
)


class TestRunPythonAnalysis:
    """Comprueba las operaciones estadísticas disponibles."""

    def test_mean_calculates_average(self):
        request = AnalysisRequest(
            operation="mean",
            values=[10, 20, 30],
        )

        result = run_python_analysis(request)

        assert result["operation"] == "mean"
        assert result["mean"] == 20
        assert result["count"] == 3

    def test_describe_calculates_statistics(self):
        request = AnalysisRequest(
            operation="describe",
            values=[10, 20, 30, 40],
        )

        result = run_python_analysis(request)

        assert result["operation"] == "describe"
        assert result["count"] == 4
        assert result["mean"] == 25
        assert result["median"] == 25
        assert result["minimum"] == 10
        assert result["maximum"] == 40
        assert result["range"] == 30

    def test_describe_handles_odd_number_of_values(self):
        request = AnalysisRequest(
            operation="describe",
            values=[10, 30, 20],
        )

        result = run_python_analysis(request)

        assert result["median"] == 20

    def test_growth_rate_calculates_percentage(self):
        request = AnalysisRequest(
            operation="growth_rate",
            values=[100, 120],
        )

        result = run_python_analysis(request)

        assert result["operation"] == "growth_rate"
        assert result["initial_value"] == 100
        assert result["final_value"] == 120
        assert result["growth_rate_percent"] == pytest.approx(20)

    def test_growth_rate_supports_decrease(self):
        request = AnalysisRequest(
            operation="growth_rate",
            values=[100, 80],
        )

        result = run_python_analysis(request)

        assert result["growth_rate_percent"] == pytest.approx(-20)

    def test_growth_rate_rejects_initial_zero(self):
        request = AnalysisRequest(
            operation="growth_rate",
            values=[0, 100],
        )

        with pytest.raises(ValueError, match="initial value of zero"):
            run_python_analysis(request)

    def test_compare_calculates_difference_between_averages(self):
        request = AnalysisRequest(
            operation="compare",
            values=[10, 20],
            comparison_values=[30, 40],
        )

        result = run_python_analysis(request)

        assert result["operation"] == "compare"
        assert result["mean_a"] == 15
        assert result["mean_b"] == 35
        assert result["difference"] == 20

    def test_rejects_empty_values(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(
                operation="mean",
                values=[],
            )

    def test_growth_rate_requires_two_values(self):
        with pytest.raises(
            ValidationError,
            match="at least two values",
        ):
            AnalysisRequest(
                operation="growth_rate",
                values=[100],
            )

    def test_compare_requires_comparison_values(self):
        with pytest.raises(
            ValidationError,
            match="comparison_values",
        ):
            AnalysisRequest(
                operation="compare",
                values=[10, 20],
            )

    def test_compare_rejects_empty_comparison_values(self):
        with pytest.raises(
            ValidationError,
            match="comparison_values",
        ):
            AnalysisRequest(
                operation="compare",
                values=[10, 20],
                comparison_values=[],
            )

    def test_other_operations_reject_comparison_values(self):
        with pytest.raises(
            ValidationError,
            match="only valid for compare",
        ):
            AnalysisRequest(
                operation="mean",
                values=[10, 20],
                comparison_values=[30, 40],
            )

    def test_rejects_unsupported_operation(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(
                operation="median",
                values=[10, 20, 30],
            )