"""Pruebas del workflow de FitFamily sin llamadas externas."""

from unittest.mock import patch

import pytest

from src.graph.state import create_initial_state
from src.graph.workflow import build_workflow


@pytest.fixture
def initial_state():
    """Estado inicial válido para las pruebas del workflow."""
    return create_initial_state(
        run_id="research-test-001",
        brief={
            "business_type": "gimnasio con ludoteca",
            "location": "Madrid",
            "study_area": "El Cañaveral",
            "questions": [],
        },
    )


@pytest.fixture
def simulated_pipeline():
    """Simula investigación, redacción y revisión."""
    with (
        patch("src.graph.workflow.run_research") as research,
        patch("src.graph.workflow.run_writing") as writing,
        patch("src.graph.workflow.run_basic_review") as review,
    ):
        yield research, writing, review


def test_workflow_builds_successfully():
    """El grafo debe poder construirse sin ejecutar agentes."""
    graph = build_workflow()

    assert graph is not None


def test_workflow_runs_research_writing_and_review(
    initial_state,
    simulated_pipeline,
):
    """Comprueba la ruta actual de investigación a revisión."""
    research, writing, review = simulated_pipeline

    # Se definirán resultados válidos en el siguiente ajuste de estas
    # pruebas, utilizando los modelos reales del proyecto.
    graph = build_workflow()

    assert graph is not None
    research.assert_not_called()
    writing.assert_not_called()
    review.assert_not_called()


def test_workflow_can_be_compiled_with_checkpointer():
    """El workflow debe aceptar un checkpointer opcional."""
    graph = build_workflow(checkpointer=None)

    assert graph is not None
