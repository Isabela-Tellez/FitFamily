"""Estado de sesión y utilidades compartidas de la interfaz Studio.

Centraliza claves de sesión, formato de valores, redacción de secretos y
ejecución de operaciones async. Ninguna pantalla define sus propias
convenciones de estado.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import streamlit as st

# Claves de sesión canónicas (una sola lista para toda la aplicación)
SESSION_KEYS = {
    "ff_run_id": None,
    "ff_state": None,
    "ff_mcp": None,
    "ff_mcp_error": None,
    "ff_page": "Inicio",
    "ff_pending_page": None,
    "ff_running": False,
}


def init() -> None:
    """Inicializa las claves de sesión sin sobrescribir valores existentes."""
    for key, default in SESSION_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_state() -> dict[str, Any] | None:
    """Devuelve el estado del workflow activo o None."""
    state = st.session_state.get("ff_state")
    return state if isinstance(state, dict) else None


def has_study() -> bool:
    return get_state() is not None


def format_value(value: object) -> str:
    """Formatea números en español; None se muestra como «No disponible»."""
    if value is None:
        return "No disponible"
    if isinstance(value, float):
        return (
            f"{value:,.2f}".rstrip("0").rstrip(".")
            .replace(",", "X").replace(".", ",").replace("X", ".")
        )
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return str(value)


def redact_secrets(text: object) -> str:
    """Elimina credenciales del entorno de cualquier mensaje mostrado."""
    value = str(text)
    for name in ("TAVILY_API_KEY", "GROQ_API_KEY", "LANGSMITH_API_KEY"):
        secret = os.getenv(name, "")
        if secret:
            value = value.replace(secret, "[credencial ocultada]")
    return value


def run_async(coroutine):
    """Ejecuta una corrutina async en el hilo principal de Streamlit."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("Ya existe un bucle async activo; no se abrió una segunda sesión MCP.")
