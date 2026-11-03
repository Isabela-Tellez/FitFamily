"""Prueba opcional contra el proveedor visual real; requiere credenciales."""

import os
from pathlib import Path

import pytest

from src.multimodal.image_analyzer import analyze_image

IMAGE_PATH = os.getenv("FITFAMILY_VISION_TEST_IMAGE")
MODEL = os.getenv("VISION_LLM_MODEL")
API_KEY = os.getenv("GROQ_API_KEY")

pytestmark = pytest.mark.skipif(
    not (IMAGE_PATH and MODEL and API_KEY and Path(IMAGE_PATH).is_file()),
    reason=(
        "Configura FITFAMILY_VISION_TEST_IMAGE, VISION_LLM_MODEL y GROQ_API_KEY "
        "para ejecutar la prueba real del modelo visual."
    ),
)


def test_real_vision_model_analyzes_a_chart_image():
    result = analyze_image(
        IMAGE_PATH,
        {"title": "Gráfico de prueba", "unit": "EUR/month"},
        image_id="vision-integration-test",
    )
    assert result.observation.strip()
    assert result.model_used == MODEL
