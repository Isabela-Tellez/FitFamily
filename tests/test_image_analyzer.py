"""Pruebas unitarias del análisis visual de FitFamily."""

import base64
import json
from types import SimpleNamespace

import pytest

from src.multimodal.image_analyzer import (
    ImageObservation,
    analyze_image,
    append_image_observations_to_report,
)
from src.reporting.models import ReportDraft


def _fake_response(payload):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))]
    )


def _png(tmp_path):
    path = tmp_path / "price_chart.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-content")
    return path


def test_analyze_image_sends_image_and_returns_traceable_observation(tmp_path, monkeypatch):
    image_path = _png(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response({
            "observation": "La segunda barra representa la cuota más alta.",
            "limitations": ["No se distinguen las condiciones de matrícula."],
        })

    monkeypatch.setattr("src.multimodal.image_analyzer.litellm.completion", fake_completion)
    result = analyze_image(
        image_path,
        {"title": "Comparación de cuotas", "unit": "EUR/month", "sample_size": 3},
        image_id="price-chart-01",
        source_artifact_id="price_comparison",
        model="groq/test-vision-model",
    )

    assert isinstance(result, ImageObservation)
    assert result.image_id == "price-chart-01"
    assert result.source_artifact_id == "price_comparison"
    assert result.model_used == "groq/test-vision-model"
    assert "cuota más alta" in result.observation
    image_content = captured["messages"][0]["content"][1]
    assert image_content["type"] == "image_url"
    encoded = image_content["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(encoded) == image_path.read_bytes()


def test_analyze_image_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze_image(tmp_path / "missing.png", "Contexto", model="groq/test")


def test_analyze_image_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "chart.gif"
    path.write_bytes(b"image")
    with pytest.raises(ValueError, match="Formato no compatible"):
        analyze_image(path, "Contexto", model="groq/test")


def test_analyze_image_requires_model_and_api_key(tmp_path, monkeypatch):
    path = _png(tmp_path)

    monkeypatch.setattr(
        "src.multimodal.image_analyzer.load_dotenv",
        lambda *args, **kwargs: None,
    )

    monkeypatch.delenv("VISION_LLM_MODEL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="VISION_LLM_MODEL"):
        analyze_image(path, "Contexto")


def test_analyze_image_rejects_non_groq_model(tmp_path, monkeypatch):
    path = _png(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with pytest.raises(ValueError, match="proveedor Groq"):
        analyze_image(path, "Contexto", model="openai/test-vision")


def test_analyze_image_rejects_invalid_json(tmp_path, monkeypatch):
    path = _png(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        "src.multimodal.image_analyzer.litellm.completion",
        lambda **kwargs: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="respuesta sin JSON"))]
        ),
    )
    with pytest.raises(ValueError, match="JSON válido"):
        analyze_image(path, "Contexto", model="groq/test")


def test_analyze_image_wraps_provider_error(tmp_path, monkeypatch):
    path = _png(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def fail(**kwargs):
        raise OSError("network unavailable")

    monkeypatch.setattr("src.multimodal.image_analyzer.litellm.completion", fail)
    with pytest.raises(RuntimeError, match="Error al solicitar el análisis visual"):
        analyze_image(path, "Contexto", model="groq/test")


def test_append_observations_to_report_keeps_limitations_and_traceability():
    draft = ReportDraft(title="Informe", study_area="Madrid")
    observation = ImageObservation(
        image_id="price-chart-01",
        source_image_path="artifacts/price_comparison.png",
        source_artifact_id="price_comparison",
        model_used="groq/test-vision-model",
        observation="La segunda barra es la más alta.",
        limitations=["No se ven las condiciones de matrícula."],
        processed_file_path="artifacts/price_comparison.png",
    )

    result = append_image_observations_to_report(draft, [observation])

    assert result is draft
    assert any(section.startswith("Análisis visual\n") for section in draft.sections)
    assert "price-chart-01" in draft.sections[-1]
    assert any("condiciones de matrícula" in item for item in draft.limitations)


def test_append_empty_observations_does_not_change_report():
    draft = ReportDraft(title="Informe", study_area="Madrid")
    assert append_image_observations_to_report(draft, []) is draft
    assert draft.sections == []
