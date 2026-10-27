"""Pruebas del estado compartido de FitFamily."""

import pytest

from src.graph.state import create_initial_state


def test_initial_research_state_is_valid():
    """Comprueba los valores iniciales de una investigación real."""
    state = create_initial_state(
        run_id="research-2026-001",
        brief={"topic": "FitFamily"},
    )

    assert state["run_id"] == "research-2026-001"
    assert state["brief"] == {"topic": "FitFamily"}
    assert state["status"] == "running"
    assert state["current_stage"] == "research"

    assert state["research_result"] is None
    assert state["analysis_result"] is None
    assert state["report_draft"] is None
    assert state["review_result"] is None

    assert state["approval_decision"] is None
    assert state["approved_version_id"] is None
    assert state["events"] == []
    assert state["errors"] == []


@pytest.mark.parametrize("run_id", ["", " ", None, 123])
def test_initial_state_rejects_invalid_run_ids(run_id):
    """Rechaza identificadores de investigación inválidos."""
    with pytest.raises(ValueError):
        create_initial_state(
            run_id=run_id,
            brief={"topic": "FitFamily"},
        )


def test_initial_state_rejects_empty_brief():
    """Rechaza encargos vacíos."""
    with pytest.raises(ValueError):
        create_initial_state(
            run_id="research-2026-001",
            brief={},
        )
