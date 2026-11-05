
"""Pruebas del registro y la consulta de eventos de FitFamily."""

import pytest

from src.runtime.events import (
    emit_event,
    emit_event_once,
    read_events,
)


def test_emit_and_read_event(tmp_path):
    """Comprueba que un evento se guarda y recupera correctamente."""
    db_path = tmp_path / "events.sqlite"

    event = emit_event(
        run_id="run-001",
        stage="research",
        event_type="started",
        message="Investigación iniciada",
        details={"source": "test"},
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        db_path=db_path,
    )

    assert len(events) == 1
    assert events[0]["id"] == event["id"]
    assert events[0]["run_id"] == "run-001"
    assert events[0]["stage"] == "research"
    assert events[0]["event_type"] == "started"
    assert events[0]["message"] == "Investigación iniciada"
    assert events[0]["details"] == {"source": "test"}


def test_events_are_isolated_by_run_id(tmp_path):
    """Comprueba que distintas investigaciones no mezclan eventos."""
    db_path = tmp_path / "events.sqlite"

    emit_event(
        "run-001",
        "research",
        "info",
        "Evento A",
        db_path=db_path,
    )

    emit_event(
        "run-002",
        "analysis",
        "info",
        "Evento B",
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        db_path=db_path,
    )

    assert len(events) == 1
    assert events[0]["message"] == "Evento A"


def test_read_events_supports_incremental_polling(tmp_path):
    """Comprueba que se pueden consultar exclusivamente eventos nuevos."""
    db_path = tmp_path / "events.sqlite"

    first = emit_event(
        "run-001",
        "research",
        "info",
        "Primero",
        db_path=db_path,
    )

    emit_event(
        "run-001",
        "research",
        "info",
        "Segundo",
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        after_id=first["id"],
        db_path=db_path,
    )

    assert len(events) == 1
    assert events[0]["message"] == "Segundo"


def test_read_events_respects_limit(tmp_path):
    """Comprueba que limit restringe el número de resultados."""
    db_path = tmp_path / "events.sqlite"

    for index in range(5):
        emit_event(
            "run-001",
            "research",
            "info",
            f"Evento {index}",
            db_path=db_path,
        )

    events = read_events(
        "run-001",
        limit=2,
        db_path=db_path,
    )

    assert len(events) == 2
    assert events[0]["message"] == "Evento 0"
    assert events[1]["message"] == "Evento 1"


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


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", ""),
        ("stage", ""),
        ("event_type", ""),
        ("message", ""),
    ],
)
def test_emit_event_rejects_empty_fields(
    tmp_path,
    field,
    value,
):
    """Comprueba que no se admiten campos obligatorios vacíos."""
    arguments = {
        "run_id": "run-001",
        "stage": "research",
        "event_type": "info",
        "message": "Evento",
        "db_path": tmp_path / "events.sqlite",
    }

    arguments[field] = value

    with pytest.raises(ValueError):
        emit_event(**arguments)


def test_emit_event_rejects_invalid_details(tmp_path):
    """Comprueba que details debe ser un diccionario."""
    with pytest.raises(ValueError):
        emit_event(
            "run-001",
            "research",
            "info",
            "Evento",
            details=["invalid"],
            db_path=tmp_path / "events.sqlite",
        )


def test_read_events_rejects_invalid_after_id(tmp_path):
    """Comprueba que after_id debe ser un entero no negativo."""
    invalid_values = [-1, 1.5, "1", True]

    for value in invalid_values:
        with pytest.raises(ValueError):
            read_events(
                "run-001",
                after_id=value,
                db_path=tmp_path / "events.sqlite",
            )


def test_read_events_rejects_invalid_limit(tmp_path):
    """Comprueba que limit debe ser un entero positivo."""
    invalid_values = [0, -1, 1.5, "10", True]

    for value in invalid_values:
        with pytest.raises(ValueError):
            read_events(
                "run-001",
                limit=value,
                db_path=tmp_path / "events.sqlite",
            )


def test_emit_event_once_prevents_duplicates(tmp_path):
    """Comprueba que un evento equivalente no se duplica."""
    db_path = tmp_path / "events.sqlite"

    first = emit_event_once(
        "run-001",
        "research",
        "stage_started",
        "Inicio de investigación",
        details={"source": "test"},
        db_path=db_path,
    )

    second = emit_event_once(
        "run-001",
        "research",
        "stage_started",
        "Inicio de investigación",
        details={"source": "test"},
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        db_path=db_path,
    )

    assert first["id"] == second["id"]
    assert len(events) == 1


def test_emit_event_once_allows_different_details(tmp_path):
    """Comprueba que eventos con detalles diferentes no se fusionan."""
    db_path = tmp_path / "events.sqlite"

    emit_event_once(
        "run-001",
        "research",
        "info",
        "Evento",
        details={"attempt": 1},
        db_path=db_path,
    )

    emit_event_once(
        "run-001",
        "research",
        "info",
        "Evento",
        details={"attempt": 2},
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        db_path=db_path,
    )

    assert len(events) == 2


def test_emit_event_once_ignores_dictionary_key_order(tmp_path):
    """Comprueba que el orden de las claves no genera duplicados."""
    db_path = tmp_path / "events.sqlite"

    first = emit_event_once(
        "run-001",
        "research",
        "info",
        "Evento",
        details={"a": 1, "b": 2},
        db_path=db_path,
    )

    second = emit_event_once(
        "run-001",
        "research",
        "info",
        "Evento",
        details={"b": 2, "a": 1},
        db_path=db_path,
    )

    assert first["id"] == second["id"]


def test_events_persist_between_connections(tmp_path):
    """Comprueba que los eventos sobreviven al cierre de conexiones."""
    db_path = tmp_path / "events.sqlite"

    emit_event(
        "run-001",
        "research",
        "info",
        "Evento persistente",
        db_path=db_path,
    )

    events = read_events(
        "run-001",
        db_path=db_path,
    )

    assert len(events) == 1
    assert events[0]["message"] == "Evento persistente"


def test_read_events_returns_empty_list_for_unknown_run(tmp_path):
    """Comprueba que una investigación desconocida devuelve lista vacía."""
    events = read_events(
        "unknown-run",
        db_path=tmp_path / "events.sqlite",
    )

    assert events == []
