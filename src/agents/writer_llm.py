"""
Configuración del modelo utilizado por el redactor de FitFamily.
"""

import os
from pathlib import Path

from crewai import LLM
from crewai.hooks import HookAborted, before_llm_call
from dotenv import load_dotenv
from src.agents.writer_budget import (
    WRITER_ROLE,
    WRITER_MAX_OUTPUT_TOKENS,
    WRITER_REQUEST_TOKEN_LIMIT,
    count_writer_tokens,
    reserve_writer_tokens,
)

@before_llm_call
def remove_groq_cache_breakpoints(context):
    """Retira una marca interna de CrewAI que Groq no admite."""
    model = getattr(context.llm, "model", "")

    if isinstance(model, str) and model.startswith("groq/"):
        for message in context.messages:
            message.pop("cache_breakpoint", None)

        # El presupuesto solo se aplica a nuestro redactor, no a otros agentes.
        if getattr(getattr(context, "agent", None), "role", None) == WRITER_ROLE:
            output = context.llm.max_tokens or WRITER_MAX_OUTPUT_TOKENS
            total = count_writer_tokens(context.messages, model) + output
            if total > WRITER_REQUEST_TOKEN_LIMIT:
                raise HookAborted(
                    reason="La petición real del redactor supera el presupuesto "
                    "de tokens, incluida la salida. No se ha enviado a Groq."
                )
            reserve_writer_tokens(total)

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
        max_tokens=WRITER_MAX_OUTPUT_TOKENS,
        timeout=60,
        response_format={"type": "json_object"},
    )
