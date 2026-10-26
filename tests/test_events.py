
"""Pruebas del registro y la consulta de eventos de FitFamily."""

import pytest

from src.runtime.events import emit_event, read_events


def test_emit_and_read_event(tmp_path):
    """Comprueba que un evento se guarda y se recupera correctamente."""
    db_path = tmp_path / "events.sqlite"

    event = emit_event(
        run_id="run-001",
        stage="research",
        event_type="started",
        message="Investigación iniciada",
        details={"source": "test"},
        db_path=db_path,
    )

    events = read_events("run-001", db_path=db_path)

    assert len(events) == 1
    assert events[0]["id"] == event["id"]
    assert events[0]["message"] == "Investigación iniciada"
    assert events[0]["details"] == {"source": "test"}


def test_events_are_isolated_by_run_id(tmp_path):
    """Comprueba que los eventos de distintas investigaciones no se mezclan."""
    db_path = tmp_path / "events.sqlite"

    emit_event("run-001", "research", "info", "Evento A", db_path=db_path)
    emit_event("run-002", "analysis", "info", "Evento B", db_path=db_path)

    events = read_events("run-001", db_path=db_path)

    assert len(events) == 1
    assert events[0]["message"] == "Evento A"


def test_read_events_supports_incremental_polling(tmp_path):
    """Comprueba que se pueden consultar solo los eventos nuevos."""
    db_path = tmp_path / "events.sqlite"

    first = emit_event(
        "run-001", "research", "info", "Primero", db_path=db_path
    )
    emit_event(
        "run-001", "research", "info", "Segundo", db_path=db_path
    )

    events = read_events(
        "run-001",
        after_id=first["id"],
        db_path=db_path,
    )

    assert len(events) == 1
    assert events[0]["message"] == "Segundo"


def test_emit_event_rejects_empty_run_id(tmp_path):
    """Impide registrar eventos sin identificar la investigación."""
    with pytest.raises(ValueError):
        emit_event(
            "",
            "research",
            "info",
            "Evento",
            db_path=tmp_path / "events.sqlite",
        )


def test_read_events_rejects_invalid_limit(tmp_path):
    """Comprueba que el límite de resultados debe ser positivo."""
    with pytest.raises(ValueError):
        read_events(
            "run-001",
            limit=0,
            db_path=tmp_path / "events.sqlite",
        )
