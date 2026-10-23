"""
Configuración del modelo utilizado por el redactor de FitFamily.
"""

import os
from pathlib import Path

from crewai import LLM
from dotenv import load_dotenv


def build_writer_llm() -> LLM:
    """Construye el cliente del modelo sin realizar una llamada."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)

    model = os.getenv("WRITER_LLM_MODEL", "").strip()
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not model:
        raise ValueError("Falta configurar WRITER_LLM_MODEL.")

    if not model.startswith("groq/"):
        raise ValueError(
            "El redactor está configurado actualmente para Groq."
        )

    if not api_key or api_key == "pega_aqui_tu_clave":
        raise ValueError("Falta configurar GROQ_API_KEY.")

    return LLM(
        model=model,
        api_key=api_key,
        temperature=0,
        max_tokens=2048,
        timeout=60,
    )