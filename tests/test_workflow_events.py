from unittest.mock import patch

from src.graph.state import create_initial_state
from src.graph.workflow import build_workflow


def test_instrumented_node_records_real_transitions(tmp_path):
    """Comprueba que un nodo registra su ejecución real."""

    from src.runtime.events import read_events

    state = create_initial_state(
        run_id="events-integration-001",
        brief={
            "business_type": "gimnasio",
            "location": "Madrid",
            "questions": [],
        },
    )

    with patch(
        "src.graph.workflow.settings"
    ) as mocked_settings:
        mocked_settings.events_db_path = (
            tmp_path / "events.sqlite"
        )

        graph = build_workflow()

        from src.graph.workflow import _instrument_node

        def fake_node(current_state):
            return {
                "status": "running",
                "current_stage": "analysis",
            }

        instrumented = _instrument_node(
            "research",
            fake_node,
        )

        result = instrumented(state)

        assert result["current_stage"] == "analysis"

        events = read_events(
            "events-integration-001",
            db_path=tmp_path / "events.sqlite",
        )

        assert [event["event_type"] for event in events] == [
            "stage_started",
            "stage_completed",
            "stage_transition",
        ]



def test_instrumented_node_records_failure(tmp_path):
    """Comprueba que los errores reales se registran."""

    import pytest

    from src.runtime.events import read_events
    from src.graph.workflow import _instrument_node

    db_path = tmp_path / "events.sqlite"

    with patch("src.graph.workflow.settings") as mocked_settings:
        mocked_settings.events_db_path = db_path

        def failing_node(state):
            raise RuntimeError("Error de prueba")

        instrumented = _instrument_node(
            "research",
            failing_node,
        )

        state = {
            "run_id": "events-failure-001",
        }

        with pytest.raises(
            RuntimeError,
            match="Error de prueba",
        ):
            instrumented(state)

    events = read_events(
        "events-failure-001",
        db_path=db_path,
    )

    assert [event["event_type"] for event in events] == [
        "stage_started",
        "stage_failed",
    ]
